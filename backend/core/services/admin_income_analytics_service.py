"""
Admin Income & Business Analytics Service
Seva Bandhu Platform

Provides comprehensive data aggregation and financial analytics across:
- Gross Sales (GMV) & Realized Platform Income
- Booking lifecycle & conversion metrics
- Service performance & Bayesian smoothed quality ratings
- Technician productivity, earnings, scorecards, and ratings
- Customer acquisition, retention, and repeat booking rates
- Marketing offers, redemptions, and referral bonuses
- Technician/Customer wallet ledger & withdrawal liabilities
- Quality assurance, ratings distribution (1★-5★), warnings, and support complaints
"""

import datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate

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
    TechnicianSupportTicket,
    WalletTransaction,
    ReferralLog,
    Offer,
    CustomerOffer,
)


def _to_decimal(val) -> Decimal:
    """Safely convert None or numeric to Decimal."""
    if val is None:
        return Decimal('0.00')
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal('0.00')


def resolve_date_range(preset='this_month', start_str=None, end_str=None):
    """
    Resolves date range boundaries and human-readable labels.
    Returns: (start_dt, end_dt, resolved_preset, label)
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    preset = (preset or 'this_month').lower().strip()

    if preset == 'today':
        return today_start, today_end, 'today', 'Today'

    elif preset == 'yesterday':
        yesterday_start = today_start - datetime.timedelta(days=1)
        yesterday_end = today_end - datetime.timedelta(days=1)
        return yesterday_start, yesterday_end, 'yesterday', 'Yesterday'

    elif preset == 'last_7_days':
        start = today_start - datetime.timedelta(days=6)
        return start, today_end, 'last_7_days', 'Last 7 Days'

    elif preset == 'last_30_days':
        start = today_start - datetime.timedelta(days=29)
        return start, today_end, 'last_30_days', 'Last 30 Days'

    elif preset == 'this_month':
        start = today_start.replace(day=1)
        return start, today_end, 'this_month', 'This Month'

    elif preset == 'previous_month':
        # First day of this month minus 1 day -> in previous month
        first_of_this_month = today_start.replace(day=1)
        last_day_prev_month = first_of_this_month - datetime.timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_prev_month = last_day_prev_month.replace(hour=23, minute=59, second=59, microsecond=999999)
        return first_day_prev_month, end_prev_month, 'previous_month', 'Previous Month'

    elif preset == 'this_year':
        start = today_start.replace(month=1, day=1)
        return start, today_end, 'this_year', 'This Year'

    elif preset == 'all_time':
        # Epoch to future
        start = timezone.make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0))
        return start, today_end, 'all_time', 'All Time'

    elif preset == 'custom' and start_str and end_str:
        try:
            s_date = datetime.datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
            e_date = datetime.datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
            if s_date > e_date:
                s_date, e_date = e_date, s_date
            start = timezone.make_aware(datetime.datetime.combine(s_date, datetime.time.min))
            end = timezone.make_aware(datetime.datetime.combine(e_date, datetime.time.max))
            return start, end, 'custom', f"{s_date.strftime('%d %b %Y')} – {e_date.strftime('%d %b %Y')}"
        except Exception:
            # Fallback to this_month if format invalid
            start = today_start.replace(day=1)
            return start, today_end, 'this_month', 'This Month'

    # Default fallback
    start = today_start.replace(day=1)
    return start, today_end, 'this_month', 'This Month'


def get_comparison_range(start_dt, end_dt, preset_key):
    """
    Computes prior matching window for calculating delta percentages.
    Returns: (prev_start_dt, prev_end_dt) or (None, None)
    """
    if preset_key == 'all_time' or not start_dt or not end_dt:
        return None, None

    if preset_key == 'today':
        prev_end = start_dt - datetime.timedelta(microseconds=1)
        prev_start = prev_end.replace(hour=0, minute=0, second=0, microsecond=0)
        return prev_start, prev_end

    if preset_key == 'yesterday':
        prev_end = start_dt - datetime.timedelta(microseconds=1)
        prev_start = prev_end.replace(hour=0, minute=0, second=0, microsecond=0)
        return prev_start, prev_end

    duration = end_dt - start_dt
    prev_end = start_dt - datetime.timedelta(microseconds=1)
    prev_start = prev_end - duration
    return prev_start, prev_end


def compute_delta(current_val, prev_val):
    """
    Returns delta dictionary: value, direction ('up', 'down', 'neutral'), and formatted string.
    """
    cur = float(current_val or 0.0)
    prev = float(prev_val or 0.0)

    if prev == 0.0:
        if cur > 0.0:
            return {'value': 100.0, 'direction': 'up', 'formatted': '+100%'}
        elif cur == 0.0:
            return {'value': 0.0, 'direction': 'neutral', 'formatted': '0.0%'}
        else:
            return {'value': -100.0, 'direction': 'down', 'formatted': '-100%'}

    pct = round(((cur - prev) / prev) * 100.0, 1)
    if pct > 0:
        return {'value': pct, 'direction': 'up', 'formatted': f"+{pct}%"}
    elif pct < 0:
        return {'value': abs(pct), 'direction': 'down', 'formatted': f"{pct}%"}
    else:
        return {'value': 0.0, 'direction': 'neutral', 'formatted': '0.0%'}


def get_kpi_summary(start_dt, end_dt, prev_start_dt=None, prev_end_dt=None):
    """
    Aggregates top-level KPI metrics across sales, revenue, bookings, and users.
    Includes comparison delta against prior period.
    """
    # Current period booking filters
    sr_qs = ServiceRequest.objects.all()
    if start_dt and end_dt:
        sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))

    total_bookings = sr_qs.count()
    gross_sales = _to_decimal(sr_qs.aggregate(Sum('amount'))['amount__sum'])

    completed_qs = sr_qs.filter(status='Completed')
    completed_bookings = completed_qs.count()
    realized_sales = _to_decimal(completed_qs.aggregate(Sum('amount'))['amount__sum'])

    active_bookings = sr_qs.filter(status__in=['Pending', 'Assigned', 'In Progress']).count()

    # Technician job earnings in period
    tech_tx_qs = TechnicianWalletTransaction.objects.filter(
        transaction_type='CREDIT',
        service_request__isnull=False
    )
    if start_dt and end_dt:
        tech_tx_qs = tech_tx_qs.filter(created_at__range=(start_dt, end_dt))
    tech_payouts = _to_decimal(tech_tx_qs.aggregate(Sum('amount'))['amount__sum'])

    # Platform Gross Income = Realized Sales - Technician Payouts
    platform_income = realized_sales - tech_payouts
    if platform_income < Decimal('0.00'):
        platform_income = Decimal('0.00')

    completion_rate = round((completed_bookings / total_bookings * 100.0), 1) if total_bookings > 0 else 0.0

    # User counts
    total_technicians = Technician_signup.objects.count()
    active_technicians = Technician_signup.objects.filter(is_available=True).count()
    total_customers = customer_signup.objects.count()

    cust_new_qs = customer_signup.objects.all()
    if start_dt and end_dt:
        cust_new_qs = cust_new_qs.filter(user__date_joined__range=(start_dt, end_dt))
    new_customers = cust_new_qs.count()

    # Complaints in period
    ticket_qs = SupportTicket.objects.filter(ticket_type='Complaint')
    if start_dt and end_dt:
        ticket_qs = ticket_qs.filter(created_at__range=(start_dt, end_dt))
    complaints_count = ticket_qs.count()

    # Previous period for deltas
    deltas = {}
    if prev_start_dt and prev_end_dt:
        prev_sr_qs = ServiceRequest.objects.filter(created_at__range=(prev_start_dt, prev_end_dt))
        prev_total_bookings = prev_sr_qs.count()
        prev_gross_sales = _to_decimal(prev_sr_qs.aggregate(Sum('amount'))['amount__sum'])

        prev_comp_qs = prev_sr_qs.filter(status='Completed')
        prev_comp_bookings = prev_comp_qs.count()
        prev_realized_sales = _to_decimal(prev_comp_qs.aggregate(Sum('amount'))['amount__sum'])

        prev_tech_tx = TechnicianWalletTransaction.objects.filter(
            transaction_type='CREDIT',
            service_request__isnull=False,
            created_at__range=(prev_start_dt, prev_end_dt)
        )
        prev_tech_payouts = _to_decimal(prev_tech_tx.aggregate(Sum('amount'))['amount__sum'])
        prev_platform_income = max(Decimal('0.00'), prev_realized_sales - prev_tech_payouts)

        deltas = {
            'gross_sales': compute_delta(gross_sales, prev_gross_sales),
            'realized_sales': compute_delta(realized_sales, prev_realized_sales),
            'platform_income': compute_delta(platform_income, prev_platform_income),
            'total_bookings': compute_delta(total_bookings, prev_total_bookings),
            'completed_bookings': compute_delta(completed_bookings, prev_comp_bookings),
        }
    else:
        neutral = {'value': 0.0, 'direction': 'neutral', 'formatted': 'N/A'}
        deltas = {
            'gross_sales': neutral,
            'realized_sales': neutral,
            'platform_income': neutral,
            'total_bookings': neutral,
            'completed_bookings': neutral,
        }

    return {
        'gross_sales': gross_sales,
        'realized_sales': realized_sales,
        'platform_income': platform_income,
        'technician_payouts': tech_payouts,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'active_bookings': active_bookings,
        'completion_rate': completion_rate,
        'total_technicians': total_technicians,
        'active_technicians': active_technicians,
        'total_customers': total_customers,
        'new_customers': new_customers,
        'complaints_count': complaints_count,
        'deltas': deltas,
    }


def get_sales_and_revenue_trends(start_dt, end_dt):
    """
    Returns time-series daily aggregation for Chart.js (Sales, Realized, Bookings).
    """
    sr_qs = ServiceRequest.objects.all()
    if start_dt and end_dt:
        sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))

    # Daily aggregation via TruncDate
    daily_stats = (
        sr_qs.annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            total_sales=Sum('amount'),
            total_count=Count('id'),
            completed_sales=Sum('amount', filter=Q(status='Completed')),
            completed_count=Count('id', filter=Q(status='Completed')),
        )
        .order_by('date')
    )

    stats_by_date = {}
    for entry in daily_stats:
        d = entry['date']
        if d:
            stats_by_date[d] = {
                'sales': float(entry['total_sales'] or 0.0),
                'realized': float(entry['completed_sales'] or 0.0),
                'bookings': entry['total_count'],
                'completed': entry['completed_count'],
            }

    # Generate complete day-by-day continuous sequence
    labels = []
    sales_series = []
    realized_series = []
    bookings_series = []

    if start_dt and end_dt:
        cur_date = start_dt.date()
        target_end_date = end_dt.date()
        # Cap range to 60 days to prevent chart overload
        if (target_end_date - cur_date).days > 90:
            cur_date = target_end_date - datetime.timedelta(days=89)

        while cur_date <= target_end_date:
            label = cur_date.strftime('%d %b')
            labels.append(label)
            st = stats_by_date.get(cur_date, {'sales': 0.0, 'realized': 0.0, 'bookings': 0})
            sales_series.append(st['sales'])
            realized_series.append(st['realized'])
            bookings_series.append(st['bookings'])
            cur_date += datetime.timedelta(days=1)
    else:
        for d, st in sorted(stats_by_date.items()):
            labels.append(d.strftime('%d %b'))
            sales_series.append(st['sales'])
            realized_series.append(st['realized'])
            bookings_series.append(st['bookings'])

    return {
        'labels': labels,
        'sales_series': sales_series,
        'realized_series': realized_series,
        'bookings_series': bookings_series,
    }


def get_service_analytics(start_dt, end_dt):
    """
    Aggregates metrics and quality ratings per service category.
    Incorporates Bayesian smoothed quality formula from Service.performance_stats.
    """
    sr_qs = ServiceRequest.objects.all()
    if start_dt and end_dt:
        sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))

    services = Service.objects.all()
    results = []

    total_platform_revenue = _to_decimal(sr_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

    for s in services:
        cat_bookings = sr_qs.filter(service_detail__service_category=s.name)
        total_b = cat_bookings.count()
        comp_b = cat_bookings.filter(status='Completed').count()
        rev = _to_decimal(cat_bookings.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

        # Bayesian rating calculation from qualifying completed bookings
        qualifying_booking_ids = [str(x) for x in cat_bookings.filter(status='Completed').values_list('id', flat=True)]
        validated_complaints = 0
        if qualifying_booking_ids:
            validated_complaints = SupportTicket.objects.filter(
                ticket_type='Complaint',
                status='Resolved',
                service_request_id__in=qualifying_booking_ids
            ).exclude(action_taken__icontains='Rejected').count()

        if comp_b > 0:
            C = 5.0
            M = 15.0
            smoothed_complaint_rate = validated_complaints / (comp_b + C)
            raw_rating = 5.0 - (smoothed_complaint_rate * M)
            rating = round(max(1.0, min(5.0, raw_rating)), 1)
            comp_rate = round((comp_b / total_b * 100.0), 1)
        else:
            rating = None
            comp_rate = 0.0

        revenue_share = round((float(rev) / float(total_platform_revenue) * 100.0), 1) if total_platform_revenue > 0 else 0.0
        avg_order_val = round((rev / comp_b), 2) if comp_b > 0 else Decimal('0.00')

        results.append({
            'id': s.id,
            'name': s.name,
            'catalog_price': s.price,
            'is_enabled': s.is_enabled,
            'total_bookings': total_b,
            'completed_bookings': comp_b,
            'completion_rate': comp_rate,
            'revenue': rev,
            'revenue_share': revenue_share,
            'avg_order_val': avg_order_val,
            'rating': rating,
            'validated_complaints': validated_complaints,
        })

    # Sort descending by revenue, then completed bookings
    results.sort(key=lambda x: (x['revenue'], x['completed_bookings']), reverse=True)

    top_service = results[0] if results and results[0]['total_bookings'] > 0 else None
    least_booked = min(results, key=lambda x: x['total_bookings']) if results else None

    return {
        'services': results,
        'top_service': top_service,
        'least_booked': least_booked,
    }


def get_technician_performance(start_dt, end_dt):
    """
    Scorecard for every technician with earnings, completion rate, ratings, and withdrawals.
    """
    techs = Technician_signup.objects.select_related('user').all()
    results = []

    for t in techs:
        # Bookings assigned
        tech_bookings = ServiceRequest.objects.filter(technician_username=t.username)
        if start_dt and end_dt:
            tech_bookings = tech_bookings.filter(created_at__range=(start_dt, end_dt))

        total_jobs = tech_bookings.count()
        completed_jobs = tech_bookings.filter(status='Completed').count()
        completion_rate = round((completed_jobs / total_jobs * 100.0), 1) if total_jobs > 0 else 0.0

        # Earnings from jobs in period
        tx_qs = TechnicianWalletTransaction.objects.filter(
            technician=t,
            transaction_type='CREDIT',
            service_request__isnull=False
        )
        if start_dt and end_dt:
            tx_qs = tx_qs.filter(created_at__range=(start_dt, end_dt))
        job_earnings = _to_decimal(tx_qs.aggregate(Sum('amount'))['amount__sum'])

        # Incentives in period
        inc_qs = TechnicianIncentive.objects.filter(technician=t, status__in=['EARNED', 'CREDITED'])
        if start_dt and end_dt:
            inc_qs = inc_qs.filter(created_at__range=(start_dt, end_dt))
        incentive_earnings = _to_decimal(inc_qs.aggregate(Sum('amount'))['amount__sum'])

        # Withdrawals completed in period
        wd_qs = TechnicianWithdrawal.objects.filter(technician=t, status='COMPLETED')
        if start_dt and end_dt:
            wd_qs = wd_qs.filter(created_at__range=(start_dt, end_dt))
        withdrawn_amount = _to_decimal(wd_qs.aggregate(Sum('amount'))['amount__sum'])

        # Rating metrics (all time for accuracy)
        avg_rating = t.average_rating
        rating_count = t.rating_count
        warning_count = t.warning_count

        results.append({
            'id': t.id,
            'username': t.username,
            'category': t.service_category or 'General',
            'is_available': t.is_available,
            'wallet_balance': t.wallet_balance,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'completion_rate': completion_rate,
            'job_earnings': job_earnings,
            'incentive_earnings': incentive_earnings,
            'total_earnings': job_earnings + incentive_earnings,
            'withdrawn_amount': withdrawn_amount,
            'average_rating': avg_rating,
            'rating_count': rating_count,
            'warning_count': warning_count,
        })

    # Sort descending by completed jobs then earnings
    results.sort(key=lambda x: (x['completed_jobs'], x['total_earnings']), reverse=True)
    return results


def get_customer_and_booking_breakdown(start_dt, end_dt):
    """
    Booking status breakdown, customer growth, and repeat booking analysis.
    """
    sr_qs = ServiceRequest.objects.all()
    if start_dt and end_dt:
        sr_qs = sr_qs.filter(created_at__range=(start_dt, end_dt))

    status_counts = {
        'Pending': sr_qs.filter(status='Pending').count(),
        'Assigned': sr_qs.filter(status='Assigned').count(),
        'InProgress': sr_qs.filter(status='In Progress').count(),
        'Completed': sr_qs.filter(status='Completed').count(),
    }

    # Customer repeat rate calculation
    user_booking_counts = (
        ServiceRequest.objects.values('customer_username')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    total_customers_who_booked = user_booking_counts.count()
    repeat_customers = user_booking_counts.filter(c__gte=2).count()
    repeat_rate = round((repeat_customers / total_customers_who_booked * 100.0), 1) if total_customers_who_booked > 0 else 0.0

    # Top spending customers in period
    top_spenders_raw = (
        sr_qs.filter(status='Completed')
        .values('customer_username')
        .annotate(total_spent=Sum('amount'), bookings_count=Count('id'))
        .order_by('-total_spent')[:5]
    )
    top_spenders = []
    for sp in top_spenders_raw:
        cust_profile = customer_signup.objects.filter(username=sp['customer_username']).first()
        top_spenders.append({
            'username': sp['customer_username'],
            'email': cust_profile.email if cust_profile else '—',
            'contact': cust_profile.contact if cust_profile else '—',
            'bookings_count': sp['bookings_count'],
            'total_spent': _to_decimal(sp['total_spent']),
            'wallet_balance': cust_profile.wallet_balance if cust_profile else Decimal('0.00'),
        })

    return {
        'status_counts': status_counts,
        'total_customers_who_booked': total_customers_who_booked,
        'repeat_customers': repeat_customers,
        'repeat_rate': repeat_rate,
        'top_spenders': top_spenders,
    }


def get_offers_and_referrals_analytics(start_dt, end_dt):
    """
    Marketing analytics: promotional offers usage and referral reward costs.
    """
    # Offers
    active_offers = Offer.objects.filter(active=True).count()
    total_offers = Offer.objects.count()

    co_qs = CustomerOffer.objects.all()
    if start_dt and end_dt:
        co_qs = co_qs.filter(assigned_at__range=(start_dt, end_dt))
    offers_assigned = co_qs.count()
    offers_redeemed = co_qs.filter(redeemed=True).count()
    redemption_rate = round((offers_redeemed / offers_assigned * 100.0), 1) if offers_assigned > 0 else 0.0

    # Bookings with offer applied
    offer_bookings_qs = ServiceRequest.objects.filter(applied_offer__isnull=False)
    if start_dt and end_dt:
        offer_bookings_qs = offer_bookings_qs.filter(created_at__range=(start_dt, end_dt))
    offer_bookings_count = offer_bookings_qs.count()
    offer_revenue = _to_decimal(offer_bookings_qs.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

    # Breakdown per offer
    offers_table = []
    for off in Offer.objects.all():
        assigned = CustomerOffer.objects.filter(offer=off).count()
        redeemed = CustomerOffer.objects.filter(offer=off, redeemed=True).count()
        r_rate = round((redeemed / assigned * 100.0), 1) if assigned > 0 else 0.0
        bookings = ServiceRequest.objects.filter(applied_offer=off)
        if start_dt and end_dt:
            bookings = bookings.filter(created_at__range=(start_dt, end_dt))
        b_count = bookings.count()
        rev = _to_decimal(bookings.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'])

        offers_table.append({
            'title': off.title,
            'code': off.code,
            'discount_type': off.get_discount_type_display(),
            'discount_value': off.discount_value,
            'active': off.active,
            'assigned': assigned,
            'redeemed': redeemed,
            'redemption_rate': r_rate,
            'bookings_count': b_count,
            'revenue': rev,
        })

    # Referrals
    ref_qs = ReferralLog.objects.all()
    if start_dt and end_dt:
        ref_qs = ref_qs.filter(created_at__range=(start_dt, end_dt))
    referral_count = ref_qs.count()
    referral_rewards_paid = _to_decimal(ref_qs.aggregate(Sum('reward_amount'))['reward_amount__sum'])

    recent_referrals = ref_qs.select_related('referrer', 'referee').order_by('-created_at')[:10]

    return {
        'active_offers': active_offers,
        'total_offers': total_offers,
        'offers_assigned': offers_assigned,
        'offers_redeemed': offers_redeemed,
        'redemption_rate': redemption_rate,
        'offer_bookings_count': offer_bookings_count,
        'offer_revenue': offer_revenue,
        'offers_table': offers_table,
        'referral_count': referral_count,
        'referral_rewards_paid': referral_rewards_paid,
        'recent_referrals': recent_referrals,
    }


def get_wallet_and_withdrawal_analytics(start_dt, end_dt):
    """
    Platform wallet liability audit and technician withdrawal queue.
    """
    total_technician_wallet_liability = _to_decimal(
        Technician_signup.objects.aggregate(Sum('wallet_balance'))['wallet_balance__sum']
    )
    total_customer_wallet_liability = _to_decimal(
        customer_signup.objects.aggregate(Sum('wallet_balance'))['wallet_balance__sum']
    )

    wd_qs = TechnicianWithdrawal.objects.all()
    if start_dt and end_dt:
        wd_qs = wd_qs.filter(created_at__range=(start_dt, end_dt))

    withdrawals_completed = _to_decimal(wd_qs.filter(status='COMPLETED').aggregate(Sum('amount'))['amount__sum'])
    withdrawals_pending = _to_decimal(wd_qs.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'])
    pending_requests_count = wd_qs.filter(status='PENDING').count()

    # Customer refunds issued in period
    refunds_qs = WalletTransaction.objects.filter(
        transaction_type='CREDIT',
        description__icontains='Refund'
    )
    if start_dt and end_dt:
        refunds_qs = refunds_qs.filter(created_at__range=(start_dt, end_dt))
    refunds_issued = _to_decimal(refunds_qs.aggregate(Sum('amount'))['amount__sum'])

    # Pending & Recent withdrawal requests for admin action
    withdrawal_requests = (
        TechnicianWithdrawal.objects.select_related('technician')
        .order_by('-created_at')[:15]
    )

    return {
        'technician_wallet_liability': total_technician_wallet_liability,
        'customer_wallet_liability': total_customer_wallet_liability,
        'total_platform_liability': total_technician_wallet_liability + total_customer_wallet_liability,
        'withdrawals_completed': withdrawals_completed,
        'withdrawals_pending': withdrawals_pending,
        'pending_requests_count': pending_requests_count,
        'refunds_issued': refunds_issued,
        'withdrawal_requests': withdrawal_requests,
    }


def get_quality_and_complaints_analytics(start_dt, end_dt):
    """
    Quality monitoring: 1★-5★ rating distributions, customer tickets, technician warnings.
    """
    ratings_qs = TechnicianRating.objects.all()
    if start_dt and end_dt:
        ratings_qs = ratings_qs.filter(created_at__range=(start_dt, end_dt))

    total_ratings = ratings_qs.count()
    avg_stars = ratings_qs.aggregate(Avg('rating'))['rating__avg']
    avg_stars_formatted = round(avg_stars, 1) if avg_stars else 5.0

    # Rating star distribution (1 to 5)
    star_distribution = {
        5: ratings_qs.filter(rating=5).count(),
        4: ratings_qs.filter(rating=4).count(),
        3: ratings_qs.filter(rating=3).count(),
        2: ratings_qs.filter(rating=2).count(),
        1: ratings_qs.filter(rating=1).count(),
    }

    # Support complaints
    ticket_qs = SupportTicket.objects.filter(ticket_type='Complaint')
    if start_dt and end_dt:
        ticket_qs = ticket_qs.filter(created_at__range=(start_dt, end_dt))
    open_complaints = ticket_qs.filter(status='Open').count()
    resolved_complaints = ticket_qs.filter(status='Resolved').count()

    # Technician warnings
    warn_qs = TechnicianWarning.objects.all()
    if start_dt and end_dt:
        warn_qs = warn_qs.filter(created_at__range=(start_dt, end_dt))
    total_warnings = warn_qs.count()
    total_penalties = _to_decimal(warn_qs.aggregate(Sum('penalty_points'))['penalty_points__sum'])

    # Technician support tickets
    tech_ticket_qs = TechnicianSupportTicket.objects.all()
    if start_dt and end_dt:
        tech_ticket_qs = tech_ticket_qs.filter(created_at__range=(start_dt, end_dt))
    open_tech_tickets = tech_ticket_qs.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    resolved_tech_tickets = tech_ticket_qs.filter(status__in=['RESOLVED', 'CLOSED']).count()

    return {
        'total_ratings': total_ratings,
        'avg_stars': avg_stars_formatted,
        'star_distribution': star_distribution,
        'open_complaints': open_complaints,
        'resolved_complaints': resolved_complaints,
        'total_warnings': total_warnings,
        'total_penalties': total_penalties,
        'open_tech_tickets': open_tech_tickets,
        'resolved_tech_tickets': resolved_tech_tickets,
    }


def get_financial_ledger_breakdown(kpi_summary, wallet_analytics, offers_referrals):
    """
    Constructs an audit-ready financial statement table comparing Money In vs Money Out.
    """
    gross_sales = kpi_summary['gross_sales']
    realized_sales = kpi_summary['realized_sales']
    tech_payouts = kpi_summary['technician_payouts']
    gross_margin = kpi_summary['platform_income']

    referral_costs = offers_referrals['referral_rewards_paid']
    refunds = wallet_analytics['refunds_issued']
    withdrawals_paid = wallet_analytics['withdrawals_completed']

    # Net platform cash retained after all platform subsidies
    net_retained_income = gross_margin - referral_costs - refunds
    if net_retained_income < Decimal('0.00'):
        net_retained_income = Decimal('0.00')

    ledger_rows = [
        {
            'category': 'Revenue & Inflows',
            'item': 'Gross Bookings Value (GMV)',
            'amount': gross_sales,
            'type': 'inflow',
            'note': 'Total value of customer bookings created in selected range',
        },
        {
            'category': 'Revenue & Inflows',
            'item': 'Realized Completed Sales',
            'amount': realized_sales,
            'type': 'inflow',
            'note': 'Customer payments collected for successfully completed bookings',
        },
        {
            'category': 'Direct Operating Outflows',
            'item': 'Technician Job Payouts',
            'amount': tech_payouts,
            'type': 'outflow',
            'note': 'Wallet credits earned by technicians for completed jobs',
        },
        {
            'category': 'Platform Gross Profit',
            'item': 'Platform Gross Income',
            'amount': gross_margin,
            'type': 'net_positive',
            'note': 'Realized Sales minus Technician Job Payouts',
        },
        {
            'category': 'Marketing & Subsidies',
            'item': 'Referral Rewards Paid',
            'amount': referral_costs,
            'type': 'outflow',
            'note': 'Referral bonuses distributed to customer wallets',
        },
        {
            'category': 'Customer Adjustments',
            'item': 'Customer Refunds Issued',
            'amount': refunds,
            'type': 'outflow',
            'note': 'Customer wallet credits for ticket refunds',
        },
        {
            'category': 'Net Profit Summary',
            'item': 'Net Platform Retained Income',
            'amount': net_retained_income,
            'type': 'net_positive',
            'note': 'Gross Profit minus Referral Rewards and Refunds',
        },
        {
            'category': 'Cash Flow / Payouts',
            'item': 'Technician Cash Withdrawals Paid',
            'amount': withdrawals_paid,
            'type': 'cash_flow',
            'note': 'Actual bank/UPI disbursements processed for technician wallet balances',
        },
    ]

    return {
        'rows': ledger_rows,
        'net_retained_income': net_retained_income,
    }


def get_full_income_analytics_context(request):
    """
    Main orchestration entry point: parses GET query params, runs queries,
    and constructs the complete template context.
    """
    preset = request.GET.get('preset', 'this_month')
    start_date_param = request.GET.get('start_date', '')
    end_date_param = request.GET.get('end_date', '')

    start_dt, end_dt, resolved_preset, date_label = resolve_date_range(preset, start_date_param, end_date_param)
    prev_start_dt, prev_end_dt = get_comparison_range(start_dt, end_dt, resolved_preset)

    kpi = get_kpi_summary(start_dt, end_dt, prev_start_dt, prev_end_dt)
    trend_data = get_sales_and_revenue_trends(start_dt, end_dt)
    service_data = get_service_analytics(start_dt, end_dt)
    technicians = get_technician_performance(start_dt, end_dt)
    customer_data = get_customer_and_booking_breakdown(start_dt, end_dt)
    offers_referrals = get_offers_and_referrals_analytics(start_dt, end_dt)
    wallet_data = get_wallet_and_withdrawal_analytics(start_dt, end_dt)
    quality_data = get_quality_and_complaints_analytics(start_dt, end_dt)
    ledger_data = get_financial_ledger_breakdown(kpi, wallet_data, offers_referrals)

    return {
        # Filter State
        'preset': resolved_preset,
        'date_label': date_label,
        'start_date_str': start_dt.strftime('%Y-%m-%d') if start_dt else '',
        'end_date_str': end_dt.strftime('%Y-%m-%d') if end_dt else '',

        # Key Metrics & Cards
        'kpi': kpi,

        # Chart.js Serialized Data
        'chart_trends': trend_data,
        'chart_categories': [s['name'] for s in service_data['services']],
        'chart_cat_revenue': [float(s['revenue']) for s in service_data['services']],
        'chart_cat_bookings': [s['total_bookings'] for s in service_data['services']],

        # Sections
        'service_analytics': service_data,
        'technicians': technicians,
        'customer_analytics': customer_data,
        'offers_referrals': offers_referrals,
        'wallet_analytics': wallet_data,
        'quality_analytics': quality_data,
        'financial_ledger': ledger_data,
    }

