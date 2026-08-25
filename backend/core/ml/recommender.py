import os
import joblib
import numpy as np
from core.models import ServiceRequest, Service

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model')

def get_recommendations(customer_username, max_results=3):
    """
    Returns a list of dicts: {"service": Service_obj, "recommendation_score": float, "reason": str}
    """
    all_services = list(Service.objects.filter(is_enabled=True))
    service_map = {s.name: s for s in all_services}
    
    knn_path = os.path.join(MODEL_DIR, 'knn_model.joblib')
    matrix_path = os.path.join(MODEL_DIR, 'interaction_matrix.joblib')
    
    has_model = os.path.exists(knn_path) and os.path.exists(matrix_path)
    
    if has_model:
        knn = joblib.load(knn_path)
        pivot = joblib.load(matrix_path)
        
        if customer_username in pivot.index:
            # We have history for this user, do CF
            user_idx = pivot.index.get_loc(customer_username)
            user_vector = pivot.iloc[user_idx].values.reshape(1, -1)
            
            # Find neighbors
            distances, indices = knn.kneighbors(user_vector, n_neighbors=min(5, len(pivot)))
            
            # Aggregate neighbors' preferences
            neighbor_vectors = pivot.iloc[indices[0]].values
            weights = 1.0 - distances[0] # cosine similarity
            
            # Avoid division by zero if weights sum to 0
            if weights.sum() > 0:
                weighted_sum = np.average(neighbor_vectors, axis=0, weights=weights)
            else:
                weighted_sum = np.zeros_like(user_vector[0])
            
            # Combine with user's own history (heavy weight to their own history)
            final_scores = (user_vector[0] * 0.7) + (weighted_sum * 0.3)
            
            # Create ranking
            ranking = []
            for i, col in enumerate(pivot.columns):
                ranking.append((col, final_scores[i], i))
            
            ranking.sort(key=lambda x: x[1], reverse=True)
            
            recs = []
            for service_name, score, idx in ranking:
                if len(recs) >= max_results: break
                if service_name in service_map and score > 0:
                    reason = "Based on your recent service history" if user_vector[0][idx] > 0 else "Customers with similar service histories also booked this"
                    recs.append({
                        "service": service_map[service_name],
                        "recommendation_score": round(score, 2),
                        "reason": reason
                    })
            
            # If not enough, pad
            if len(recs) < max_results:
                recs.extend(_get_fallback_recommendations(service_map, max_results - len(recs), exclude=[r['service'].name for r in recs]))
                
            return recs
            
        elif os.path.exists(matrix_path):
            # User not in model (Cold start, but model exists)
            # Maybe fallback to general popularity using the interaction matrix
            pivot = joblib.load(matrix_path)
            popular = pivot.sum(axis=0).sort_values(ascending=False)
            recs = []
            for service_name, score in popular.items():
                if len(recs) >= max_results: break
                if service_name in service_map:
                    recs.append({
                        "service": service_map[service_name],
                        "recommendation_score": round(score, 2),
                        "reason": "Popular service in your area"
                    })
            
            if len(recs) < max_results:
                recs.extend(_get_fallback_recommendations(service_map, max_results - len(recs), exclude=[r['service'].name for r in recs]))
            return recs

    # Complete Fallback / Cold Start
    return _get_fallback_recommendations(service_map, max_results)


def _get_fallback_recommendations(service_map, limit, exclude=None):
    if exclude is None: exclude = []
    
    # Find most popular services globally via DB
    from django.db.models import Count
    popular = ServiceRequest.objects.values('service_detail__service_category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    recs = []
    for p in popular:
        if len(recs) >= limit: break
        cat = p['service_detail__service_category']
        if cat in service_map and cat not in exclude:
            recs.append({
                "service": service_map[cat],
                "recommendation_score": 0.50, # default score
                "reason": "Popular service in your area"
            })
            
    # If still not enough, just pick first enabled ones
    for name, s in service_map.items():
        if len(recs) >= limit: break
        if name not in exclude and not any(r['service'].name == name for r in recs):
            recs.append({
                "service": s,
                "recommendation_score": 0.30,
                "reason": "Trending service"
            })
            
    return recs
