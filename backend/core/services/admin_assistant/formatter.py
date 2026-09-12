"""
Response Formatter for Admin Data Assistant
Seva Bandhu Platform

Formats structured execution results into clean, human-readable answers.
Supports LIST, COUNT, ENTITY_DETAILS, TECHNICIAN_SERVICES, ATTRIBUTE LOOKUPS,
and Indian currency representation.
"""

from decimal import Decimal
from typing import Any
from .metric_registry import get_metric


def format_currency(val: Any) -> str:
    """Format numeric/decimal value as Indian Rupee (₹)."""
    if val is None:
        return "₹0.00"
    try:
        dec = Decimal(str(val))
        return f"₹{dec:,.2f}"
    except Exception:
        return f"₹{val}"


def format_value_by_metric(metric_key: str, val: Any) -> str:
    """Format an individual metric value based on its registered unit."""
    m_def = get_metric(metric_key)
    unit = m_def.unit if m_def else 'text'

    if unit == 'currency':
        return format_currency(val)
    elif unit == 'rating':
        if isinstance(val, (int, float, Decimal)):
            return f"★ {round(float(val), 1)}"
        return f"★ {val}"
    elif unit == 'count':
        return f"{val:,}" if isinstance(val, int) else str(val)
    return str(val)


def _format_currency_simple(val):
    if val is None:
        return "0"
    try:
        dec = Decimal(str(val))
        if dec == dec.to_integral():
            return f"{int(dec)}"
        return f"{dec:,.2f}"
    except Exception:
        return str(val)


def _format_platform_overview(result: dict) -> str:
    paid_sales_str = _format_currency_simple(result['paid_sales'])
    tech_earnings_str = _format_currency_simple(result['tech_earnings'])
    platform_income_str = _format_currency_simple(result['platform_income'])

    lines = [
        "Seva Bandhu platform overview:",
        f"Technicians: {result['tech_count']}",
        f"Customers: {result['cust_count']}",
        f"Services: {result['serv_count']}",
        f"Bookings: {result['total_bookings']} ({result['completed_bookings']} completed)",
        f"Paid sales: Rs {paid_sales_str}",
        f"Technician earnings: Rs {tech_earnings_str}",
        f"Platform income: Rs {platform_income_str}",
        f"Offers: {result['offers_count']}",
        f"Customer complaints: {result['cust_complaints']}",
        f"Technician tickets: {result['tech_tickets']}",
        f"Ratings: {result['ratings_count']} (average {result['avg_rating']:.1f} stars)",
        f"Withdrawals: {result['withdrawals_count']}",
        f"Referrals: {result['referrals_count']}",
        f"Incentive awards: {result['incentives_count']}",
        "Source: Admin Analytics"
    ]
    return "\n".join(lines)


def format_query_response(result: dict) -> str:
    """
    Main formatting dispatcher.
    Returns human-readable answer string.
    """
    res_type = result.get('type')
    text = ""

    if res_type in ['out_of_scope', 'help', 'clarification', 'error']:
        text = result.get('message', '')

    elif res_type == 'platform_overview':
        text = _format_platform_overview(result)

    elif res_type == 'list':
        text = _format_list(result)

    elif res_type == 'count':
        text = _format_count(result)

    elif res_type == 'entity_details':
        text = _format_entity_details(result)

    elif res_type == 'technician_services':
        text = _format_technician_services(result)

    elif res_type == 'entity_metrics':
        text = _format_entity_metrics(result)

    elif res_type == 'system_metrics':
        text = _format_system_metrics(result)

    elif res_type == 'cross_relational':
        text = _format_cross_relational(result)

    elif res_type == 'ranking':
        text = _format_ranking(result)

    elif res_type == 'compare_periods':
        text = _format_compare_periods(result)

    elif res_type == 'compare_entities':
        text = _format_compare_entities(result)

    else:
        text = "Query executed successfully."

    # Ensure source attribution is included
    if "Source: Admin Analytics" not in text:
        text = f"{text}\nSource: Admin Analytics"

    return text


def _format_list(result: dict) -> str:
    target = result['target']
    total = result['total_count']
    records = result['records']

    if total == 0:
        return f"There are currently no {target} found in the database."

    if target == 'technicians':
        lines = ["Technicians:"]
        for t in records:
            lines.append(f"- {t['name']}")
        return "\n".join(lines)

    elif target == 'customers':
        lines = ["Customers:"]
        for c in records:
            lines.append(f"- {c['name']}")
        return "\n".join(lines)

    elif target == 'services':
        lines = ["Services:"]
        for s in records:
            lines.append(f"- {s['name']}")
        return "\n".join(lines)

    return f"Found {total} records."


def _format_count(result: dict) -> str:
    target = result['target']
    count = result['count']

    if target == 'technicians':
        active = result.get('active_count', count)
        return f"There are **{count} technicians** registered on the platform (**{active} currently active/available**)."

    elif target == 'customers':
        new_c = result.get('new_count')
        if new_c is not None:
            return f"There are **{count} total customers** (**{new_c} new signups** in this period)."
        return f"There are **{count} customers** registered on the platform."

    elif target == 'services':
        active = result.get('active_count', count)
        return f"There are **{count} services** in the catalog (**{active} active and open for booking**)."

    elif target == 'bookings':
        comp = result.get('completed_count', 0)
        pend = result.get('pending_count', 0)
        return f"There are **{count} total bookings** (**{comp} completed**, **{pend} active/pending**)."

    elif target == 'complaints':
        op = result.get('open_count', 0)
        res = result.get('resolved_count', 0)
        return f"There are **{count} total complaints** recorded (**{op} open**, **{res} resolved**)."

    return f"Total count: **{count}**."


def _format_entity_details(result: dict) -> str:
    etype = result['entity_type']

    if etype == 'technician':
        services_str = ", ".join(result['services']) if result['services'] else result['specialty']
        lines = [
            f"**{result['name']} (Technician Profile)**:",
            f"• **Specialty**: {result['specialty']}",
            f"• **Services Handled**: {services_str}",
            f"• **Phone Number**: `{result['phone']}`",
            f"• **Email Address**: `{result['email']}`",
            f"• **Availability Status**: {'Available' if result['is_available'] else 'Offline/Busy'}",
            f"• **Quality Rating**: ★ {result['rating']} ({result['warning_count']} warnings)",
            f"• **Completed Jobs**: {result['completed_jobs']} (out of {result['total_bookings']} bookings)",
            f"• **Total Earnings**: {format_currency(result['total_earnings'])}",
            f"• **Wallet Balance**: {format_currency(result['wallet_balance'])}",
            f"• **Disbursed Withdrawals**: {format_currency(result['withdrawals'])}",
            f"• **Member Since**: {result['joined']}"
        ]
        return "\n".join(lines)

    elif etype == 'customer':
        lines = [
            f"**{result['name']} (Customer Profile)**:",
            f"• **Phone Number**: `{result['phone']}`",
            f"• **Email Address**: `{result['email']}`",
            f"• **Total Spending**: {format_currency(result['total_spent'])}",
            f"• **Completed Bookings**: {result['completed_bookings']} (out of {result['total_bookings']} total)",
            f"• **Customer Wallet Balance**: {format_currency(result['wallet_balance'])}",
            f"• **Support Complaints Filed**: {result['complaints']}",
            f"• **Member Since**: {result['joined']}"
        ]
        return "\n".join(lines)

    elif etype == 'service':
        lines = [
            f"**{result['name']} (Service Catalog)**:",
            f"• **Catalog Price**: {format_currency(result['price'])}",
            f"• **Active Status**: {'Active (Open for bookings)' if result['is_enabled'] else 'Disabled'}",
            f"• **Quality Rating**: ★ {result['rating']} ({result['validated_complaints']} complaints)",
            f"• **Completed Bookings**: {result['completed_bookings']} (out of {result['total_bookings']} total)",
            f"• **Total Revenue Generated**: {format_currency(result['revenue'])}"
        ]
        return "\n".join(lines)

    return "Entity details retrieved."


def _format_technician_services(result: dict) -> str:
    tech = result['technician']
    services = result['services']

    if not services:
        return f"**{tech}** does not have any specific services assigned currently."

    lines = [f"**{tech}** provides the following services:"]
    for s in services:
        price_str = f" (Price: {format_currency(s['price'])})" if s['price'] is not None else ""
        lines.append(f"• **{s['name']}**{price_str}")
    return "\n".join(lines)


def _format_entity_metrics(result: dict) -> str:
    ent = result['entity']
    metrics = result['metrics']
    date_preset = result.get('date_range')

    if len(metrics) == 1:
        k, v = next(iter(metrics.items()))
        m_def = get_metric(k)
        disp = m_def.display_name if m_def else k.replace('_', ' ').title()
        formatted_val = format_value_by_metric(k, v)

        if k == 'technician_earnings':
            if date_preset == 'this_year':
                return f"**{ent['identifier']}**'s annual technician earnings (This Year) are **{formatted_val}**."
            elif date_preset == 'this_month':
                return f"**{ent['identifier']}**'s monthly technician earnings (This Month) are **{formatted_val}**."
            elif date_preset == 'today':
                return f"**{ent['identifier']}**'s technician earnings for today are **{formatted_val}**."
            return f"**{ent['identifier']}**'s technician earnings are **{formatted_val}**."

        elif k == 'customer_spending':
            if date_preset == 'this_year':
                return f"**{ent['identifier']}** has spent **{formatted_val}** this year across completed bookings."
            elif date_preset == 'this_month':
                return f"**{ent['identifier']}** has spent **{formatted_val}** this month across completed bookings."
            return f"**{ent['identifier']}** has spent **{formatted_val}** across completed bookings."

        elif k == 'technician_wallet_balance':
            return f"**{ent['identifier']}**'s wallet balance is **{formatted_val}**."
        elif k == 'customer_wallet_balance':
            return f"**{ent['identifier']}**'s customer wallet balance is **{formatted_val}**."
        elif k == 'technician_withdrawals':
            return f"**{ent['identifier']}** has withdrawn **{formatted_val}** in completed bank payouts."
        elif k == 'service_price':
            return f"The catalog price for **{ent['identifier']}** is **{formatted_val}**."
        elif k == 'rating':
            return f"The current quality rating for **{ent['identifier']}** is **{formatted_val}**."
        elif k == 'bookings':
            return f"**{ent['identifier']}** has **{formatted_val}** total bookings."
        elif k == 'completed_jobs':
            return f"**{ent['identifier']}** has completed **{formatted_val}** jobs."
        elif k == 'contact_email':
            return f"**{ent['identifier']}**'s email address is `{v}`."
        elif k == 'contact_phone':
            return f"**{ent['identifier']}**'s contact phone number is **{v}**."
        elif k == 'service_status':
            return f"**{ent['identifier']}** status: **{formatted_val}**."
        elif k == 'service_description':
            return f"**{ent['identifier']}**: {v}."
        elif k == 'complaints':
            return f"**{ent['identifier']}** has **{formatted_val}** recorded complaints/warnings."

        return f"**{ent['display_name']}** — {disp}: **{formatted_val}**"

    # Multi-metric bullet list
    lines = [f"**{ent['display_name']}**:"]
    for k, v in metrics.items():
        m_def = get_metric(k)
        disp = m_def.display_name if m_def else k.replace('_', ' ').title()
        formatted_val = format_value_by_metric(k, v)
        lines.append(f"• **{disp}**: {formatted_val}")

    return "\n".join(lines)


def _format_system_metrics(result: dict) -> str:
    metrics = result['metrics']
    date_label = result.get('date_range', 'Selected Timeframe').replace('_', ' ').title()

    lines = [f"**Platform Summary ({date_label})**:"]
    for k, v in metrics.items():
        m_def = get_metric(k)
        disp = m_def.display_name if m_def else k.replace('_', ' ').title()
        formatted_val = format_value_by_metric(k, v)
        lines.append(f"• **{disp}**: {formatted_val}")

    return "\n".join(lines)


def _format_cross_relational(result: dict) -> str:
    q_type = result.get('question_type')

    if q_type == 'customer_who_booked_technician_most':
        if not result.get('customer'):
            return f"No bookings found for technician **{result['technician']}**."
        return (
            f"The customer who booked technician **{result['technician']}** the most is "
            f"**{result['customer']}** with **{result['booking_count']} bookings**."
        )

    elif q_type == 'technician_who_served_customer_most':
        if not result.get('technician'):
            return f"No assigned bookings found for customer **{result['customer']}**."
        return (
            f"The technician who served **{result['customer']}** the most is "
            f"**{result['technician']}** with **{result['booking_count']} completed bookings**."
        )

    elif q_type == 'service_booked_most_by_customer':
        if not result.get('service'):
            return f"No bookings found for customer **{result['customer']}**."
        return (
            f"The service that **{result['customer']}** booked most often is "
            f"**{result['service']}** (**{result['booking_count']} bookings**)."
        )

    elif q_type == 'technician_most_sales_for_service':
        if not result.get('technician'):
            return f"No completed bookings found for service **{result['service']}**."
        return (
            f"The technician who generated the most sales from **{result['service']}** is "
            f"**{result['technician']}**, generating **{format_currency(result['total_sales'])}** "
            f"across {result['job_count']} completed jobs."
        )

    elif q_type == 'customer_most_spent_for_service':
        if not result.get('customer'):
            return f"No completed bookings found for service **{result['service']}**."
        return (
            f"The customer who spent the most on **{result['service']}** is "
            f"**{result['customer']}**, with total spending of **{format_currency(result['total_spent'])}** "
            f"across {result['booking_count']} completed bookings."
        )

    return "Cross-relational query resolved."


def _format_ranking(result: dict) -> str:
    target = result.get('target', 'results').title()
    metric_key = result.get('metric', '')
    ranks = result.get('ranks', [])

    if not ranks:
        return f"No {target.lower()} found matching the ranking criteria."

    m_def = get_metric(metric_key)
    metric_disp = m_def.display_name if m_def else metric_key.replace('_', ' ').title()

    lines = [f"**Top {target} by {metric_disp}**:"]
    for idx, r in enumerate(ranks, 1):
        if r.get('unit') == 'currency':
            val_str = format_currency(r['value'])
        elif r.get('unit') == 'joined':
            val_str = f"Joined on {r['value']}"
        else:
            val_str = f"{r['value']} {r.get('unit', '')}"
        lines.append(f"{idx}. **{r['name']}** — {val_str}")

    return "\n".join(lines)


def _format_compare_periods(result: dict) -> str:
    cur_p = result['current_period']
    cur_v = format_currency(result['current_value'])
    prev_p = result['previous_period']
    prev_v = format_currency(result['previous_value'])
    diff = result['difference']
    delta = result['delta']

    diff_str = f"+{format_currency(diff)}" if diff >= 0 else f"-{format_currency(abs(diff))}"

    verdict = ""
    if diff > 0:
        verdict = f"Sales were **higher** in {cur_p} than in {prev_p}."
    elif diff < 0:
        verdict = f"Sales were **lower** in {cur_p} than in {prev_p}."
    else:
        verdict = f"Sales were **identical** between {cur_p} and {prev_p}."

    lines = [
        f"**Sales Comparison ({cur_p} vs. {prev_p})**:",
        f"• **{cur_p}**: {cur_v}",
        f"• **{prev_p}**: {prev_v}",
        f"• **Difference**: {diff_str} ({delta['formatted']})",
        "",
        verdict
    ]
    return "\n".join(lines)


def _format_compare_entities(result: dict) -> str:
    ent1 = result['entity1']
    ent2 = result['entity2']
    metric_key = result['metric']
    winner = result.get('winner')

    m_def = get_metric(metric_key)
    disp = m_def.display_name if m_def else metric_key.replace('_', ' ').title()

    val1_str = format_value_by_metric(metric_key, ent1['value'])
    val2_str = format_value_by_metric(metric_key, ent2['value'])

    lines = [
        f"**{disp} Comparison**:",
        f"• **{ent1['name']}**: {val1_str}",
        f"• **{ent2['name']}**: {val2_str}",
    ]

    if winner:
        lines.append(f"\n**{winner}** is higher for {disp.lower()}.")
    else:
        lines.append(f"\nBoth have equal {disp.lower()}.")

    return "\n".join(lines)
