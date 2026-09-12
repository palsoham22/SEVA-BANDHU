"""
Query Executor for Admin Data Assistant
Seva Bandhu Platform

Executes validated StructuredQuerySpec objects against the database using Django ORM.
Supports LIST, COUNT, ENTITY_DETAILS, TECHNICIAN_SERVICES, ATTRIBUTE LOOKUP, and FINANCIAL METRICS.
Zero arbitrary code execution, zero raw SQL.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from core.models import (
    customer_signup,
    Technician_signup,
    Service,
    ServiceRequest,
    SupportTicket,
    TechnicianRating,
    TechnicianWarning,
    TechnicianWalletTransaction,
    TechnicianWithdrawal,
    TechnicianIncentive,
    WalletTransaction,
    ReferralLog,
)
from core.services.admin_income_analytics_service import (
    resolve_date_range,
    compute_delta,
    _to_decimal
)
from .parser import StructuredQuerySpec


def execute_query(spec: StructuredQuerySpec) -> dict:
    """
    Executes a StructuredQuerySpec and returns a structured result dictionary.
    """
    intent = spec.intent

    if intent == 'out_of_scope':
        return {
            'type': 'out_of_scope',
            'message': (
                "I am the Seva Bandhu Admin Data Assistant. I can only retrieve and analyze data "
                "from your Seva Bandhu platform (technicians, customers, services, bookings, "
                "sales, wallet balances, withdrawals, complaints, and ratings)."
            )
        }

    elif intent == 'help':
        return {
            'type': 'help',
            'message': (
                "Hello! I can answer questions about your Seva Bandhu platform data. Here are some examples of what you can ask:\n"
                "• **List Data**: *\"name all technicians\"*, *\"list all customers\"*, *\"give me all services\"*\n"
                "• **Counts**: *\"How many technicians are there?\"*, *\"How many bookings completed this month?\"*\n"
                "• **Profiles & Services**: *\"show Sayan Paul's details\"*, *\"what service does Sayan Paul provide?\"*\n"
                "• **Contacts**: *\"Sayan Paul's contact number\"*, *\"Rahul's email\"*\n"
                "• **Sales & Income**: *\"Give me today's sales, bookings and new customers\"*, *\"Compare this month's sales with last month's\"*\n"
                "• **Technicians**: *\"How much did Sayan Paul earn?\"*, *\"Sayan Paul's annual income\"*, *\"What is Sayan Paul's wallet balance?\"*\n"
                "• **Customers**: *\"How much did Rahul spend?\"*, *\"Who spent the most?\"*\n"
                "• **Services**: *\"Which service was booked the most?\"*, *\"Price of AC Repair\"*, *\"AC Repair rating\"*\n"
                "• **Cross-Relational**: *\"Which customer booked Sayan Paul the most?\"*, *\"Which technician generated the most sales from AC Repair?\"*"
            )
        }

    elif intent == 'clarification':
        return {
            'type': 'clarification',
            'message': spec.clarification_message
        }

    elif intent == 'list':
        return _execute_list(spec)

    elif intent == 'count':
        return _execute_count(spec)

    elif intent == 'entity_details':
        return _execute_entity_details(spec)

    elif intent == 'technician_services':
        return _execute_technician_services(spec)

    elif intent == 'compare_periods':
        return _execute_compare_periods(spec)

    elif intent == 'compare_entities':
        return _execute_compare_entities(spec)

    elif intent == 'cross_relational':
        return _execute_cross_relational(spec)

    elif intent == 'ranking':
        return _execute_ranking(spec)

    elif intent in ['lookup', 'multi_metric']:
        if spec.entity:
            return _execute_entity_metrics(spec)
        else:
            return _execute_system_metrics(spec)

    return {
        'type': 'error',
        'message': "Unable to execute query specification."
    }


def _execute_list(spec: StructuredQuerySpec) -> dict:
    """Executes enumeration/listing queries (e.g. 'name all technicians', 'list all services')."""
    target = spec.target_entity_type
    active_only = spec.filters.get('active_only', False)

    if target == 'technician':
        qs = Technician_signup.objects.select_related('user').all()
        if active_only:
            qs = qs.filter(is_available=True)

        total_count = qs.count()
        records = []
        for t in qs[:25]:
            records.append({
                'name': t.username,
                'specialty': t.service_category or 'General',
                'phone': t.contact or '—',
                'is_available': t.is_available,
                'rating': t.average_rating if t.average_rating is not None else 'Unrated'
            })
        return {
            'type': 'list',
            'target': 'technicians',
            'total_count': total_count,
            'records': records,
            'active_only': active_only
        }

    elif target == 'customer':
        qs = customer_signup.objects.select_related('user').all()
        total_count = qs.count()
        records = []
        for c in qs[:25]:
            records.append({
                'name': c.username,
                'email': c.email or c.user.email,
                'phone': c.contact or '—',
                'joined': c.user.date_joined.strftime('%d %b %Y')
            })
        return {
            'type': 'list',
            'target': 'customers',
            'total_count': total_count,
            'records': records
        }

    elif target == 'service':
        qs = Service.objects.all()
        if active_only:
            qs = qs.filter(is_enabled=True)

        total_count = qs.count()
        records = []
        for s in qs:
            records.append({
                'name': s.name,
                'price': _to_decimal(s.price),
                'is_enabled': s.is_enabled,
                'rating': s.performance_stats.get('rating')
            })
        return {
            'type': 'list',
            'target': 'services',
            'total_count': total_count,
            'records': records,
            'active_only': active_only
        }

    return {'type': 'error', 'message': f"Cannot list unknown target entity type '{target}'."}


def _execute_count(spec: StructuredQuerySpec) -> dict:
    """Executes count queries (e.g. 'how many technicians are there?')."""
    target = spec.target_entity_type
    start_dt, end_dt = spec.date_start, spec.date_end

    if target == 'technician':
        total = Technician_signup.objects.count()
        active = Technician_signup.objects.filter(is_available=True).count()
        return {
            'type': 'count',
            'target': 'technicians',
            'count': total,
            'active_count': active,
            'date_range': spec.date_preset
        }

    elif target == 'customer':
        total = customer_signup.objects.count()
        new_in_period = None
        if start_dt and end_dt:
            new_in_period = customer_signup.objects.filter(user__date_joined__range=(start_dt, end_dt)).count()
        return {
            'type': 'count',
            'target': 'customers',
            'count': total,
            'new_count': new_in_period,
            'date_range': spec.date_preset
        }

    elif target == 'service':
        total = Service.objects.count()
        active = Service.objects.filter(is_enabled=True).count()
        return {
            'type': 'count',
            'target': 'services',
            'count': total,
            'active_count': active
        }

    elif target == 'booking':
        sr_qs = ServiceRequest.objects.all()
        if start_dt and end_dt:
            sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
        total = sr_qs.count()
        completed = sr_qs.filter(status='Completed').count()
        pending = sr_qs.filter(status__in=['Pending', 'Assigned', 'In Progress']).count()
        return {
            'type': 'count',
            'target': 'bookings',
            'count': total,
            'completed_count': completed,
            'pending_count': pending,
            'date_range': spec.date_preset or 'all_time'
        }

    elif target == 'complaint':
        tk_qs = SupportTicket.objects.filter(ticket_type='Complaint')
        open_c = tk_qs.filter(status='Open').count()
        resolved_c = tk_qs.filter(status='Resolved').count()
        return {
            'type': 'count',
            'target': 'complaints',
            'count': tk_qs.count(),
            'open_count': open_c,
            'resolved_count': resolved_c
        }

    return {'type': 'error', 'message': 'Unknown count query.'}


def _execute_entity_details(spec: StructuredQuerySpec) -> dict:
    """Executes detailed profile lookup for a single technician, customer, or service."""
    entity = spec.entity

    if entity.entity_type == 'technician':
        tech = Technician_signup.objects.select_related('user').get(id=entity.entity_id)

        tx_qs = TechnicianWalletTransaction.objects.filter(technician=tech, transaction_type='CREDIT', service_request__isnull=False)
        inc_qs = TechnicianIncentive.objects.filter(technician=tech, status__in=['EARNED', 'CREDITED'])
        tot_earnings = _to_decimal(tx_qs.aggregate(Sum('amount'))['amount__sum']) + _to_decimal(inc_qs.aggregate(Sum('amount'))['amount__sum'])

        wd_qs = TechnicianWithdrawal.objects.filter(technician=tech, status='COMPLETED')
        tot_withdrawn = _to_decimal(wd_qs.aggregate(Sum('amount'))['amount__sum'])

        b_qs = ServiceRequest.objects.filter(technician_username=tech.username)
        total_b = b_qs.count()
        completed_b = b_qs.filter(status='Completed').count()

        # Services provided
        services_list = set()
        if tech.service_category:
            services_list.add(tech.service_category)
        for cat in b_qs.values_list('service_detail__service_category', flat=True).distinct():
            if cat:
                services_list.add(cat)

        return {
            'type': 'entity_details',
            'entity_type': 'technician',
            'name': tech.username,
            'phone': tech.contact or 'Not available',
            'email': tech.email or tech.user.email or 'Not available',
            'specialty': tech.service_category or 'General',
            'services': list(services_list),
            'wallet_balance': tech.wallet_balance,
            'total_earnings': tot_earnings,
            'withdrawals': tot_withdrawn,
            'rating': tech.average_rating if tech.average_rating is not None else 'Unrated',
            'rating_count': tech.rating_count,
            'warning_count': tech.warning_count,
            'total_bookings': total_b,
            'completed_jobs': completed_b,
            'is_available': tech.is_available,
            'joined': tech.user.date_joined.strftime('%d %b %Y')
        }

    elif entity.entity_type == 'customer':
        cust = customer_signup.objects.select_related('user').get(id=entity.entity_id)

        sr_qs = ServiceRequest.objects.filter(customer_username=cust.username)
        total_b = sr_qs.count()
        completed_b = sr_qs.filter(status='Completed').count()
        spent = _to_decimal(sr_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

        complaints_count = SupportTicket.objects.filter(customer=cust, ticket_type='Complaint').count()

        return {
            'type': 'entity_details',
            'entity_type': 'customer',
            'name': cust.username,
            'phone': cust.contact or 'Not available',
            'email': cust.email or cust.user.email or 'Not available',
            'wallet_balance': cust.wallet_balance,
            'total_spent': spent,
            'total_bookings': total_b,
            'completed_bookings': completed_b,
            'complaints': complaints_count,
            'joined': cust.user.date_joined.strftime('%d %b %Y')
        }

    elif entity.entity_type == 'service':
        serv = Service.objects.get(id=entity.entity_id)
        stats = serv.performance_stats
        sr_qs = ServiceRequest.objects.filter(service_detail__service_category=serv.name)
        total_b = sr_qs.count()
        completed_b = sr_qs.filter(status='Completed').count()
        rev = _to_decimal(sr_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

        return {
            'type': 'entity_details',
            'entity_type': 'service',
            'name': serv.name,
            'price': _to_decimal(serv.price),
            'is_enabled': serv.is_enabled,
            'rating': stats.get('rating') if stats.get('has_data') else 'New (No ratings)',
            'validated_complaints': stats.get('validated_complaint_count', 0),
            'total_bookings': total_b,
            'completed_bookings': completed_b,
            'revenue': rev
        }

    return {'type': 'error', 'message': 'Unknown entity details.'}


def _execute_technician_services(spec: StructuredQuerySpec) -> dict:
    """Executes query for which services a specific technician provides."""
    entity = spec.entity
    tech = Technician_signup.objects.get(id=entity.entity_id)

    services_set = set()
    if tech.service_category:
        services_set.add(tech.service_category)

    # Check booking history for any other categories
    assigned_categories = (
        ServiceRequest.objects.filter(technician_username=tech.username)
        .values_list('service_detail__service_category', flat=True)
        .distinct()
    )
    for cat in assigned_categories:
        if cat:
            services_set.add(cat)

    # Match against actual Service objects in database for pricing/rating
    service_details = []
    for s_name in sorted(services_set):
        s_obj = Service.objects.filter(name__iexact=s_name).first()
        service_details.append({
            'name': s_name,
            'price': _to_decimal(s_obj.price) if s_obj else None,
            'status': 'Active' if (s_obj and s_obj.is_enabled) else 'Available'
        })

    return {
        'type': 'technician_services',
        'technician': tech.username,
        'services': service_details
    }


def _execute_entity_metrics(spec: StructuredQuerySpec) -> dict:
    """Executes metrics for a specific resolved entity."""
    entity = spec.entity
    metrics = spec.metrics
    results = {}

    start_dt, end_dt = spec.date_start, spec.date_end

    if entity.entity_type == 'technician':
        tech = Technician_signup.objects.select_related('user').get(id=entity.entity_id)

        for m in metrics:
            if m == 'technician_earnings':
                tx_qs = TechnicianWalletTransaction.objects.filter(technician=tech, transaction_type='CREDIT', service_request__isnull=False)
                inc_qs = TechnicianIncentive.objects.filter(technician=tech, status__in=['EARNED', 'CREDITED'])
                if start_dt and end_dt:
                    tx_qs = tx_qs.filter(created_at__range=(start_dt, end_dt))
                    inc_qs = inc_qs.filter(created_at__range=(start_dt, end_dt))
                job_earnings = _to_decimal(tx_qs.aggregate(Sum('amount'))['amount__sum'])
                incentives = _to_decimal(inc_qs.aggregate(Sum('amount'))['amount__sum'])
                results['technician_earnings'] = job_earnings + incentives

            elif m == 'technician_job_earnings':
                tx_qs = TechnicianWalletTransaction.objects.filter(technician=tech, transaction_type='CREDIT', service_request__isnull=False)
                if start_dt and end_dt:
                    tx_qs = tx_qs.filter(created_at__range=(start_dt, end_dt))
                results['technician_job_earnings'] = _to_decimal(tx_qs.aggregate(Sum('amount'))['amount__sum'])

            elif m == 'technician_incentives':
                inc_qs = TechnicianIncentive.objects.filter(technician=tech, status__in=['EARNED', 'CREDITED'])
                if start_dt and end_dt:
                    inc_qs = inc_qs.filter(created_at__range=(start_dt, end_dt))
                results['technician_incentives'] = _to_decimal(inc_qs.aggregate(Sum('amount'))['amount__sum'])

            elif m == 'technician_wallet_balance':
                results['technician_wallet_balance'] = tech.wallet_balance

            elif m == 'technician_withdrawals':
                wd_qs = TechnicianWithdrawal.objects.filter(technician=tech, status='COMPLETED')
                if start_dt and end_dt:
                    wd_qs = wd_qs.filter(created_at__range=(start_dt, end_dt))
                results['technician_withdrawals'] = _to_decimal(wd_qs.aggregate(Sum('amount'))['amount__sum'])

            elif m == 'bookings':
                b_qs = ServiceRequest.objects.filter(technician_username=tech.username)
                if start_dt and end_dt:
                    b_qs = b_qs.filter(created_at__range=(start_dt, end_dt))
                results['bookings'] = b_qs.count()

            elif m == 'completed_jobs':
                b_qs = ServiceRequest.objects.filter(technician_username=tech.username, status='Completed')
                if start_dt and end_dt:
                    b_qs = b_qs.filter(created_at__range=(start_dt, end_dt))
                results['completed_jobs'] = b_qs.count()

            elif m == 'pending_bookings':
                results['pending_bookings'] = ServiceRequest.objects.filter(
                    technician_username=tech.username,
                    status__in=['Pending', 'Assigned', 'In Progress']
                ).count()

            elif m == 'rating':
                results['rating'] = tech.average_rating if tech.average_rating is not None else "Unrated"

            elif m == 'complaints':
                results['complaints'] = tech.warning_count

            elif m == 'contact_email':
                results['contact_email'] = tech.email or tech.user.email or "Not available"

            elif m == 'contact_phone':
                results['contact_phone'] = tech.contact or "Not available"

            elif m == 'joined_date':
                results['joined_date'] = tech.user.date_joined.strftime('%d %b %Y')

    elif entity.entity_type == 'customer':
        cust = customer_signup.objects.select_related('user').get(id=entity.entity_id)

        for m in metrics:
            if m == 'customer_spending':
                sr_qs = ServiceRequest.objects.filter(customer_username=cust.username, status='Completed')
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['customer_spending'] = _to_decimal(sr_qs.aggregate(Sum('amount'))['amount__sum'])

            elif m == 'customer_wallet_balance':
                results['customer_wallet_balance'] = cust.wallet_balance

            elif m == 'bookings':
                sr_qs = ServiceRequest.objects.filter(customer_username=cust.username)
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['bookings'] = sr_qs.count()

            elif m == 'completed_jobs':
                sr_qs = ServiceRequest.objects.filter(customer_username=cust.username, status='Completed')
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['completed_jobs'] = sr_qs.count()

            elif m == 'contact_email':
                results['contact_email'] = cust.email or cust.user.email or "Not available"

            elif m == 'contact_phone':
                results['contact_phone'] = cust.contact or "Not available"

            elif m == 'joined_date':
                results['joined_date'] = cust.user.date_joined.strftime('%d %b %Y')

            elif m == 'complaints':
                results['complaints'] = SupportTicket.objects.filter(customer=cust, ticket_type='Complaint').count()

    elif entity.entity_type == 'service':
        serv = Service.objects.get(id=entity.entity_id)

        for m in metrics:
            if m == 'service_price':
                results['service_price'] = Decimal(str(serv.price))

            elif m == 'service_status':
                results['service_status'] = "Active (Open for bookings)" if serv.is_enabled else "Disabled"

            elif m == 'service_description':
                results['service_description'] = f"{serv.name} service catalog entry (Price: ₹{serv.price})"

            elif m == 'bookings':
                sr_qs = ServiceRequest.objects.filter(service_detail__service_category=serv.name)
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['bookings'] = sr_qs.count()

            elif m == 'completed_jobs':
                sr_qs = ServiceRequest.objects.filter(service_detail__service_category=serv.name, status='Completed')
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['completed_jobs'] = sr_qs.count()

            elif m == 'gross_sales':
                sr_qs = ServiceRequest.objects.filter(service_detail__service_category=serv.name, status='Completed')
                if start_dt and end_dt:
                    sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))
                results['gross_sales'] = _to_decimal(sr_qs.aggregate(Sum('amount'))['amount__sum'])

            elif m == 'rating':
                stats = serv.performance_stats
                results['rating'] = stats['rating'] if stats['has_data'] else "New (No ratings)"

            elif m == 'complaints':
                stats = serv.performance_stats
                results['complaints'] = stats['validated_complaint_count']

    return {
        'type': 'entity_metrics',
        'entity': {
            'id': entity.entity_id,
            'type': entity.entity_type,
            'identifier': entity.identifier,
            'display_name': entity.display_name,
        },
        'metrics': results,
        'date_range': spec.date_preset
    }


def _execute_system_metrics(spec: StructuredQuerySpec) -> dict:
    """Executes platform-wide metrics (e.g. 'Today's sales, bookings and new customers')."""
    start_dt, end_dt = spec.date_start, spec.date_end
    results = {}

    sr_qs = ServiceRequest.objects.all()
    if start_dt and end_dt:
        sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))

    for m in spec.metrics:
        if m == 'gross_sales':
            results['gross_sales'] = _to_decimal(sr_qs.aggregate(Sum('amount'))['amount__sum'])

        elif m == 'realized_sales':
            results['realized_sales'] = _to_decimal(sr_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

        elif m == 'platform_income':
            comp_sales = _to_decimal(sr_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])
            tech_tx = TechnicianWalletTransaction.objects.filter(transaction_type='CREDIT', service_request__isnull=False)
            if start_dt and end_dt:
                tech_tx = tech_tx.filter(created_at__range=(start_dt, end_dt))
            payouts = _to_decimal(tech_tx.aggregate(Sum('amount'))['amount__sum'])
            results['platform_income'] = max(Decimal('0.00'), comp_sales - payouts)

        elif m == 'bookings':
            results['bookings'] = sr_qs.count()

        elif m == 'completed_jobs':
            results['completed_jobs'] = sr_qs.filter(status='Completed').count()

        elif m == 'pending_bookings':
            results['pending_bookings'] = sr_qs.filter(status__in=['Pending', 'Assigned', 'In Progress']).count()

        elif m == 'new_customers':
            c_qs = customer_signup.objects.all()
            if start_dt and end_dt:
                c_qs = c_qs.filter(user__date_joined__range=(start_dt, end_dt))
            results['new_customers'] = c_qs.count()

        elif m == 'new_technicians':
            t_qs = Technician_signup.objects.all()
            if start_dt and end_dt:
                t_qs = t_qs.filter(user__date_joined__range=(start_dt, end_dt))
            results['new_technicians'] = t_qs.count()

        elif m == 'complaints':
            tk_qs = SupportTicket.objects.filter(ticket_type='Complaint')
            if start_dt and end_dt:
                tk_qs = tk_qs.filter(created_at__range=(start_dt, end_dt))
            results['complaints'] = tk_qs.count()

    return {
        'type': 'system_metrics',
        'metrics': results,
        'date_range': spec.date_preset or 'this_month'
    }


def _execute_cross_relational(spec: StructuredQuerySpec) -> dict:
    """Executes multi-entity relationship questions."""
    entity = spec.entity
    rel_type = spec.cross_relation_type

    if rel_type == 'customer_who_booked_technician_most':
        top = (
            ServiceRequest.objects.filter(technician_username=entity.identifier)
            .values('customer_username')
            .annotate(booking_count=Count('id'))
            .order_by('-booking_count')
            .first()
        )
        if top:
            cust = customer_signup.objects.filter(username=top['customer_username']).first()
            return {
                'type': 'cross_relational',
                'question_type': rel_type,
                'technician': entity.identifier,
                'customer': top['customer_username'],
                'booking_count': top['booking_count'],
                'contact': cust.contact if cust else '—'
            }
        return {'type': 'cross_relational', 'question_type': rel_type, 'technician': entity.identifier, 'result': None}

    elif rel_type == 'technician_who_served_customer_most':
        top = (
            ServiceRequest.objects.filter(customer_username=entity.identifier, technician_username__isnull=False)
            .values('technician_username')
            .annotate(booking_count=Count('id'))
            .order_by('-booking_count')
            .first()
        )
        if top:
            tech = Technician_signup.objects.filter(username=top['technician_username']).first()
            return {
                'type': 'cross_relational',
                'question_type': rel_type,
                'customer': entity.identifier,
                'technician': top['technician_username'],
                'booking_count': top['booking_count'],
                'rating': tech.average_rating if tech else '—'
            }
        return {'type': 'cross_relational', 'question_type': rel_type, 'customer': entity.identifier, 'result': None}

    elif rel_type == 'service_booked_most_by_customer':
        top = (
            ServiceRequest.objects.filter(customer_username=entity.identifier)
            .values('service_detail__service_category')
            .annotate(booking_count=Count('id'))
            .order_by('-booking_count')
            .first()
        )
        if top:
            return {
                'type': 'cross_relational',
                'question_type': rel_type,
                'customer': entity.identifier,
                'service': top['service_detail__service_category'],
                'booking_count': top['booking_count']
            }
        return {'type': 'cross_relational', 'question_type': rel_type, 'customer': entity.identifier, 'result': None}

    elif rel_type == 'technician_most_sales_for_service':
        top = (
            ServiceRequest.objects.filter(
                service_detail__service_category=entity.identifier,
                status='Completed',
                technician_username__isnull=False
            )
            .values('technician_username')
            .annotate(total_sales=Sum('amount'), job_count=Count('id'))
            .order_by('-total_sales')
            .first()
        )
        if top:
            return {
                'type': 'cross_relational',
                'question_type': rel_type,
                'service': entity.identifier,
                'technician': top['technician_username'],
                'total_sales': _to_decimal(top['total_sales']),
                'job_count': top['job_count']
            }
        return {'type': 'cross_relational', 'question_type': rel_type, 'service': entity.identifier, 'result': None}

    elif rel_type == 'customer_most_spent_for_service':
        top = (
            ServiceRequest.objects.filter(
                service_detail__service_category=entity.identifier,
                status='Completed'
            )
            .values('customer_username')
            .annotate(total_spent=Sum('amount'), booking_count=Count('id'))
            .order_by('-total_spent')
            .first()
        )
        if top:
            return {
                'type': 'cross_relational',
                'question_type': rel_type,
                'service': entity.identifier,
                'customer': top['customer_username'],
                'total_spent': _to_decimal(top['total_spent']),
                'booking_count': top['booking_count']
            }
        return {'type': 'cross_relational', 'question_type': rel_type, 'service': entity.identifier, 'result': None}

    return {'type': 'error', 'message': 'Unknown cross-relational pattern'}


def _execute_ranking(spec: StructuredQuerySpec) -> dict:
    """Executes ranking and superlative queries."""
    target = spec.ranking_target
    direction = spec.ranking_direction
    limit = spec.ranking_limit or 5
    metric = spec.metrics[0] if spec.metrics else None

    if target == 'technician':
        if metric == 'completed_jobs':
            qs = (
                ServiceRequest.objects.filter(status='Completed', technician_username__isnull=False)
                .values('technician_username')
                .annotate(val=Count('id'))
            )
            order_field = '-val' if direction == 'desc' else 'val'
            raw_ranks = qs.order_by(order_field)[:limit]
            ranks = [{'name': r['technician_username'], 'value': r['val'], 'unit': 'jobs'} for r in raw_ranks]
            return {'type': 'ranking', 'target': 'technicians', 'metric': 'completed_jobs', 'ranks': ranks}

        elif metric == 'joined_date':
            t_qs = Technician_signup.objects.select_related('user').order_by('-user__date_joined' if direction == 'desc' else 'user__date_joined')[:limit]
            ranks = [{'name': t.username, 'value': t.user.date_joined.strftime('%d %b %Y'), 'unit': 'joined'} for t in t_qs]
            return {'type': 'ranking', 'target': 'technicians', 'metric': 'joined_date', 'ranks': ranks}

        else:
            # Default technician ranking: earnings
            techs = Technician_signup.objects.all()
            scored = []
            for t in techs:
                tx_qs = TechnicianWalletTransaction.objects.filter(technician=t, transaction_type='CREDIT', service_request__isnull=False)
                inc_qs = TechnicianIncentive.objects.filter(technician=t, status__in=['EARNED', 'CREDITED'])
                tot = _to_decimal(tx_qs.aggregate(Sum('amount'))['amount__sum']) + _to_decimal(inc_qs.aggregate(Sum('amount'))['amount__sum'])
                scored.append({'name': t.username, 'value': tot, 'unit': 'currency'})
            scored.sort(key=lambda x: x['value'], reverse=(direction == 'desc'))
            return {'type': 'ranking', 'target': 'technicians', 'metric': 'technician_earnings', 'ranks': scored[:limit]}

    elif target == 'customer':
        if metric == 'joined_date':
            c_qs = customer_signup.objects.select_related('user').order_by('-user__date_joined' if direction == 'desc' else 'user__date_joined')[:limit]
            ranks = [{'name': c.username, 'value': c.user.date_joined.strftime('%d %b %Y'), 'unit': 'joined'} for c in c_qs]
            return {'type': 'ranking', 'target': 'customers', 'metric': 'joined_date', 'ranks': ranks}
        else:
            # Customer spending ranking
            qs = (
                ServiceRequest.objects.filter(status='Completed')
                .values('customer_username')
                .annotate(val=Sum('amount'))
            )
            order_field = '-val' if direction == 'desc' else 'val'
            raw_ranks = qs.order_by(order_field)[:limit]
            ranks = [{'name': r['customer_username'], 'value': _to_decimal(r['val']), 'unit': 'currency'} for r in raw_ranks]
            return {'type': 'ranking', 'target': 'customers', 'metric': 'customer_spending', 'ranks': ranks}

    elif target == 'service':
        if metric == 'gross_sales':
            qs = (
                ServiceRequest.objects.filter(status='Completed')
                .values('service_detail__service_category')
                .annotate(val=Sum('amount'))
            )
            order_field = '-val' if direction == 'desc' else 'val'
            raw_ranks = qs.order_by(order_field)[:limit]
            ranks = [{'name': r['service_detail__service_category'], 'value': _to_decimal(r['val']), 'unit': 'currency'} for r in raw_ranks]
            return {'type': 'ranking', 'target': 'services', 'metric': 'gross_sales', 'ranks': ranks}
        else:
            # Service booking count ranking
            services = Service.objects.all()
            scored = []
            for s in services:
                cnt = ServiceRequest.objects.filter(service_detail__service_category=s.name).count()
                scored.append({'name': s.name, 'value': cnt, 'unit': 'bookings'})
            scored.sort(key=lambda x: x['value'], reverse=(direction == 'desc'))
            return {'type': 'ranking', 'target': 'services', 'metric': 'bookings', 'ranks': scored[:limit]}

    return {'type': 'error', 'message': 'Unknown ranking query'}


def _execute_compare_periods(spec: StructuredQuerySpec) -> dict:
    """Compares metrics between two timeframes (e.g. this month vs last month)."""
    cur_start, cur_end, _, cur_label = resolve_date_range('this_month')
    prev_start, prev_end, _, prev_label = resolve_date_range('previous_month')

    cur_sales = _to_decimal(ServiceRequest.objects.filter(created_at__range=(cur_start, cur_end)).aggregate(Sum('amount'))['amount__sum'])
    prev_sales = _to_decimal(ServiceRequest.objects.filter(created_at__range=(prev_start, prev_end)).aggregate(Sum('amount'))['amount__sum'])

    diff = cur_sales - prev_sales
    delta_info = compute_delta(cur_sales, prev_sales)

    return {
        'type': 'compare_periods',
        'metric': 'gross_sales',
        'current_period': cur_label,
        'current_value': cur_sales,
        'previous_period': prev_label,
        'previous_value': prev_sales,
        'difference': diff,
        'delta': delta_info
    }


def _execute_compare_entities(spec: StructuredQuerySpec) -> dict:
    """Compares metrics between two entities (e.g. Ramu vs tech_wash)."""
    ent1 = spec.entity
    ent2 = spec.secondary_entity
    metric = spec.metrics[0] if spec.metrics else 'bookings'

    res1 = _execute_entity_metrics(StructuredQuerySpec(intent='lookup', entity=ent1, metrics=[metric]))
    res2 = _execute_entity_metrics(StructuredQuerySpec(intent='lookup', entity=ent2, metrics=[metric]))

    val1 = res1.get('metrics', {}).get(metric, 0)
    val2 = res2.get('metrics', {}).get(metric, 0)

    winner = None
    if val1 > val2:
        winner = ent1.identifier
    elif val2 > val1:
        winner = ent2.identifier

    return {
        'type': 'compare_entities',
        'metric': metric,
        'entity1': {'name': ent1.identifier, 'value': val1},
        'entity2': {'name': ent2.identifier, 'value': val2},
        'winner': winner
    }
