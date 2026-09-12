"""
Metric Registry for Admin Data Assistant
Seva Bandhu Platform

Defines controlled business metrics, their allowed entity scopes,
semantic meanings, and data sources.

CRITICAL PRINCIPLE:
Customer Spending != Technician Earnings != Gross Sales != Realized Sales != Platform Income != Wallet Balance.
These concepts are never conflated.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MetricDefinition:
    key: str
    display_name: str
    category: str  # 'financial', 'operational', 'contact', 'quality'
    allowed_entity_types: List[str]  # ['technician', 'customer', 'service', 'platform']
    description: str
    unit: str  # 'currency', 'count', 'rating', 'text', 'percentage'


METRIC_REGISTRY = {
    # 1. Platform & Sales Metrics
    'gross_sales': MetricDefinition(
        key='gross_sales',
        display_name='Gross Sales (GMV)',
        category='financial',
        allowed_entity_types=['platform', 'service'],
        description='Total gross booking amount initiated across all bookings',
        unit='currency'
    ),
    'realized_sales': MetricDefinition(
        key='realized_sales',
        display_name='Realized Sales',
        category='financial',
        allowed_entity_types=['platform', 'service', 'technician'],
        description='Customer payments collected for successfully completed bookings',
        unit='currency'
    ),
    'platform_income': MetricDefinition(
        key='platform_income',
        display_name='Platform Gross Income',
        category='financial',
        allowed_entity_types=['platform'],
        description='Realized Sales minus Technician Job Payouts',
        unit='currency'
    ),

    # 2. Customer Specific Metrics
    'customer_spending': MetricDefinition(
        key='customer_spending',
        display_name='Customer Total Spending',
        category='financial',
        allowed_entity_types=['customer'],
        description='Total amount spent and paid by the customer for completed bookings',
        unit='currency'
    ),
    'customer_wallet_balance': MetricDefinition(
        key='customer_wallet_balance',
        display_name='Customer Wallet Balance',
        category='financial',
        allowed_entity_types=['customer'],
        description='Current balance in the customer wallet',
        unit='currency'
    ),

    # 3. Technician Specific Metrics
    'technician_earnings': MetricDefinition(
        key='technician_earnings',
        display_name='Technician Total Earnings',
        category='financial',
        allowed_entity_types=['technician'],
        description='Total wallet credits earned by technician from completed jobs and incentives',
        unit='currency'
    ),
    'technician_job_earnings': MetricDefinition(
        key='technician_job_earnings',
        display_name='Technician Job Payouts',
        category='financial',
        allowed_entity_types=['technician'],
        description='Wallet credits earned by technician strictly from completed service jobs',
        unit='currency'
    ),
    'technician_incentives': MetricDefinition(
        key='technician_incentives',
        display_name='Technician Incentive Bonuses',
        category='financial',
        allowed_entity_types=['technician'],
        description='Performance and milestone incentive rewards earned by technician',
        unit='currency'
    ),
    'technician_wallet_balance': MetricDefinition(
        key='technician_wallet_balance',
        display_name='Technician Wallet Balance',
        category='financial',
        allowed_entity_types=['technician'],
        description='Current available wallet balance of the technician',
        unit='currency'
    ),
    'technician_withdrawals': MetricDefinition(
        key='technician_withdrawals',
        display_name='Technician Withdrawals',
        category='financial',
        allowed_entity_types=['technician', 'platform'],
        description='Bank transfer payouts disbursed/requested for technician wallet balance',
        unit='currency'
    ),

    # 4. Service Specific Metrics
    'service_price': MetricDefinition(
        key='service_price',
        display_name='Service Catalog Price',
        category='operational',
        allowed_entity_types=['service'],
        description='Base catalog price for booking the service',
        unit='currency'
    ),
    'service_status': MetricDefinition(
        key='service_status',
        display_name='Service Active Status',
        category='operational',
        allowed_entity_types=['service'],
        description='Whether the service is currently enabled and open for bookings',
        unit='text'
    ),

    # 5. Operational & Volume Metrics
    'bookings': MetricDefinition(
        key='bookings',
        display_name='Total Bookings',
        category='operational',
        allowed_entity_types=['platform', 'service', 'technician', 'customer'],
        description='Total number of bookings matching the requested scope',
        unit='count'
    ),
    'completed_jobs': MetricDefinition(
        key='completed_jobs',
        display_name='Completed Bookings',
        category='operational',
        allowed_entity_types=['platform', 'service', 'technician', 'customer'],
        description='Number of successfully completed service requests',
        unit='count'
    ),
    'pending_bookings': MetricDefinition(
        key='pending_bookings',
        display_name='Pending Bookings',
        category='operational',
        allowed_entity_types=['platform', 'service', 'technician'],
        description='Bookings currently pending assignment or in progress',
        unit='count'
    ),

    # 6. Quality, Complaints & Ratings
    'rating': MetricDefinition(
        key='rating',
        display_name='Rating',
        category='quality',
        allowed_entity_types=['technician', 'service', 'platform'],
        description='Technician net rating or Bayesian smoothed service rating',
        unit='rating'
    ),
    'complaints': MetricDefinition(
        key='complaints',
        display_name='Complaints / Warnings',
        category='quality',
        allowed_entity_types=['technician', 'service', 'customer', 'platform'],
        description='Customer support complaints or disciplinary warnings',
        unit='count'
    ),

    # 7. User Growth & Demographics
    'new_customers': MetricDefinition(
        key='new_customers',
        display_name='New Customers',
        category='operational',
        allowed_entity_types=['platform'],
        description='Number of new customers who signed up in the period',
        unit='count'
    ),
    'new_technicians': MetricDefinition(
        key='new_technicians',
        display_name='New Technicians',
        category='operational',
        allowed_entity_types=['platform'],
        description='Number of new technicians who registered in the period',
        unit='count'
    ),

    # 8. Contact & Profile Info
    'contact_email': MetricDefinition(
        key='contact_email',
        display_name='Email Address',
        category='contact',
        allowed_entity_types=['technician', 'customer'],
        description='Contact email address',
        unit='text'
    ),
    'contact_phone': MetricDefinition(
        key='contact_phone',
        display_name='Phone Number',
        category='contact',
        allowed_entity_types=['technician', 'customer'],
        description='Contact phone number',
        unit='text'
    ),
    'joined_date': MetricDefinition(
        key='joined_date',
        display_name='Registration Date',
        category='contact',
        allowed_entity_types=['technician', 'customer'],
        description='When the user registered on the platform',
        unit='text'
    ),
}


def get_metric(key: str) -> Optional[MetricDefinition]:
    """Retrieve a metric definition by its key."""
    return METRIC_REGISTRY.get(key)

