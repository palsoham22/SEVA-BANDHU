import os
import sys
import django

# Setup django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

import pandas as pd
import joblib
from django.utils import timezone
from core.models import ServiceRequest, Service
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize
import numpy as np

def train_model():
    print("Fetching ServiceRequest history...")
    requests = ServiceRequest.objects.all().select_related('service_detail')
    
    if not requests.exists():
        print("No requests found. Skipping training.")
        return
        
    # Build dataframe
    data = []
    now = timezone.now()
    
    for req in requests:
        customer = req.customer_username
        service = req.service_detail.service_category
        days_ago = (now - req.created_at).days
        
        # recency weight: starts at 1.0, decays over time
        recency = 1.0 / (1.0 + (days_ago / 30.0))  # half weight after 30 days
        
        # status weight
        status = req.status
        if status == 'Completed':
            status_weight = 1.0
        elif status in ['Assigned', 'Accepted', 'In Progress']:
            status_weight = 0.8
        elif status == 'Pending':
            status_weight = 0.5
        elif status == 'Cancelled':
            status_weight = -0.5
        else:
            status_weight = 0.0
            
        interaction_weight = recency * status_weight
        
        data.append({
            'customer': customer,
            'service': service,
            'interaction_weight': interaction_weight,
            'count': 1
        })
        
    df = pd.DataFrame(data)
    
    # Aggregate scores: sum of weights for repeated usage frequency
    agg_df = df.groupby(['customer', 'service']).agg({
        'count': 'sum',
        'interaction_weight': 'sum' 
    }).reset_index()
    
    agg_df['interaction_score'] = agg_df['interaction_weight'].clip(lower=0)
    
    # Create pivot table
    pivot = agg_df.pivot(index='customer', columns='service', values='interaction_score').fillna(0)
    
    # Save the matrices and models
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model')
    os.makedirs(model_dir, exist_ok=True)
    
    if len(pivot) < 3:
        print("Not enough diverse users to train Collaborative Filtering. Saving interaction data only.")
        joblib.dump(pivot, os.path.join(model_dir, 'interaction_matrix.joblib'))
        return
        
    # Fit NearestNeighbors
    matrix = pivot.values
    # Normalize for cosine similarity
    matrix_norm = normalize(matrix, norm='l2', axis=1)
    
    knn = NearestNeighbors(metric='cosine', algorithm='brute')
    knn.fit(matrix_norm)
    
    # Save
    joblib.dump(knn, os.path.join(model_dir, 'knn_model.joblib'))
    joblib.dump(pivot, os.path.join(model_dir, 'interaction_matrix.joblib'))
    print("Training complete and models saved.")

if __name__ == '__main__':
    train_model()
