"""
Natural Language Parser for Admin Data Assistant
Seva Bandhu Platform

Converts admin English queries into a controlled StructuredQuerySpec.
Supports:
- LIST queries ("name all technicians", "list customers", "give me all services")
- COUNT queries ("how many technicians are there?", "total customers")
- ENTITY DETAILS ("show Sayan Paul's details", "tell me about Sayan Paul")
- TECHNICIAN SERVICES ("what services does Sayan Paul provide?")
- ATTRIBUTE LOOKUPS ("phone number", "email", "rating", "wallet balance", "withdrawals")
- FINANCIAL QUERIES ("annual income", "monthly earnings", "spending")
- CROSS-RELATIONAL & RANKINGS & COMPARISONS
Deterministic, safe, zero-eval, zero-LLM.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import datetime

from .entity_resolver import resolve_entities, ResolvedEntity
from .date_resolver import extract_date_range
from .metric_registry import METRIC_REGISTRY


@dataclass
class StructuredQuerySpec:
    intent: str  # 'list', 'count', 'entity_details', 'technician_services', 'lookup', 'multi_metric', 'cross_relational', 'ranking', 'compare_periods', 'compare_entities', 'out_of_scope', 'help', 'clarification'
    target_entity_type: Optional[str] = None  # 'technician', 'customer', 'service', 'booking', 'complaint'
    entity: Optional[ResolvedEntity] = None
    secondary_entity: Optional[ResolvedEntity] = None
    metrics: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    date_preset: Optional[str] = None
    date_start: Optional[datetime.datetime] = None
    date_end: Optional[datetime.datetime] = None
    compare_preset: Optional[str] = None
    ranking_target: Optional[str] = None  # 'technician', 'customer', 'service'
    ranking_direction: str = 'desc'  # 'desc', 'asc'
    ranking_limit: int = 5
    cross_relation_type: Optional[str] = None
    clarification_message: Optional[str] = None
    raw_query: str = ''


# Out of scope indicators (general knowledge, external search, destructive commands)
OUT_OF_SCOPE_REGEX = re.compile(
    r'\b(president|weather|forecast|poem|joke|who\s+invented|capital\s+of|delete|drop\s+table|update\s+balance|hack|python\s+code|chatgpt|openai|google\s+search|meaning\s+of\s+life)\b',
    re.IGNORECASE
)

GREETING_REGEX = re.compile(
    r'^(hi|hello|hey|greetings|help|who\s+are\s+you|what\s+can\s+you\s+do)[\s!\.\?]*$',
    re.IGNORECASE
)


def detect_metrics_in_text(text: str, entity_type: Optional[str] = None) -> List[str]:
    """
    Identifies relevant metrics from keywords and entity context.
    Strictly keeps customer spending separate from technician earnings and platform sales.
    """
    lower = text.lower()
    metrics = []

    # 1. Contact / Profile info
    if re.search(r'\b(contact\s+number|phone\s+number|mobile\s+number|phone|mobile|call|contact)\b', lower) and 'ticket' not in lower and 'booking' not in lower:
        metrics.append('contact_phone')
    if re.search(r'\b(email\s+address|email|mail)\b', lower):
        metrics.append('contact_email')
    if re.search(r'\b(joined|registered|sign\s*up|signed\s*up)\b', lower):
        metrics.append('joined_date')

    # 2. Service Catalog Price / Status / Description
    if re.search(r'\b(price|cost|charge|charges|fee|pricing|rate)\b', lower):
        metrics.append('service_price')
    if re.search(r'\b(status|enabled|active|open)\b', lower):
        metrics.append('service_status')
    if re.search(r'\b(description|about|details)\b', lower) and entity_type == 'service':
        metrics.append('service_description')

    # 3. Customer Spending vs Technician Earnings vs Sales
    # Rule: If query explicitly asks "spend / spent / paid" -> customer_spending
    if re.search(r'\b(spend|spent|spending|paid)\b', lower):
        metrics.append('customer_spending')

    # Rule: If query explicitly asks "earn / earned / earnings / income / salary / wages / annual income / monthly income"
    if re.search(r'\b(earn|earned|earnings|income|salary|wages|made|take\s*home)\b', lower):
        if entity_type == 'customer':
            metrics.append('customer_spending')
        else:
            metrics.append('technician_earnings')

    # Rule: "sales" / "gmv" / "revenue"
    if re.search(r'\b(sales|gross\s+sales|gmv|revenue|turnover)\b', lower):
        metrics.append('gross_sales')

    # Rule: "platform income" / "net profit" / "company margin"
    if re.search(r'\b(platform\s+income|platform\s+revenue|platform\s+margin|net\s+profit|gross\s+profit)\b', lower):
        metrics.append('platform_income')

    # 4. Wallets & Withdrawals
    if re.search(r'\b(wallet|wallet\s+balance|balance)\b', lower):
        if entity_type == 'customer':
            metrics.append('customer_wallet_balance')
        else:
            metrics.append('technician_wallet_balance')

    if re.search(r'\b(withdraw|withdrawn|withdrawal|withdrawals|payout|payouts)\b', lower):
        metrics.append('technician_withdrawals')

    # 5. Bookings & Jobs
    if re.search(r'\b(complete|completed)\b', lower) and re.search(r'\b(job|jobs|work|booking|bookings)\b', lower):
        metrics.append('completed_jobs')
    elif re.search(r'\b(completed\s+jobs|jobs\s+completed|completed\s+bookings|work\s+done|jobs\s+done)\b', lower):
        metrics.append('completed_jobs')
    elif re.search(r'\b(booking|bookings|jobs|requests|orders)\b', lower):
        metrics.append('bookings')

    # 6. Quality & Discipline
    if re.search(r'\b(rating|ratings|stars|review|reviews|score)\b', lower):
        metrics.append('rating')
    if re.search(r'\b(complaint|complaints|warning|warnings|penalty|penalties|issue|issues)\b', lower):
        metrics.append('complaints')

    # 7. Platform Growth
    if re.search(r'\b(new\s+customer|new\s+customers)\b', lower):
        metrics.append('new_customers')
    if re.search(r'\b(new\s+technician|new\s+technicians)\b', lower):
        metrics.append('new_technicians')

    # Deduplicate while preserving order
    deduped = []
    for m in metrics:
        if m not in deduped:
            deduped.append(m)
    return deduped


def parse_admin_query(
    query_text: str,
    context: Optional[Dict[str, Any]] = None
) -> StructuredQuerySpec:
    """
    Main parser entry point. Maps query text into StructuredQuerySpec.
    """
    raw_query = query_text.strip()
    lower_query = raw_query.lower()

    # 1. Check Out of Scope
    if OUT_OF_SCOPE_REGEX.search(lower_query):
        return StructuredQuerySpec(
            intent='out_of_scope',
            raw_query=raw_query
        )

    # 2. Check Greetings or Help
    if GREETING_REGEX.match(lower_query):
        return StructuredQuerySpec(
            intent='help',
            raw_query=raw_query
        )

    # 3. LIST / ENUMERATION QUERIES (Highest Priority before single-entity checks)
    # e.g. "name all technicians", "list all technicians", "show all technicians", "who are the technicians?", "list customers", "give me all services"
    list_patterns = [
        # Technicians
        (r'\b(name\s+all\s+technicians|list\s+all\s+technicians|show\s+all\s+technicians|who\s+are\s+the\s+technicians|show\s+me\s+every\s+technician|give\s+me\s+the\s+technicians|list\s+technicians|all\s+technicians|show\s+technician\s+names|get\s+technicians|technicians\s+list)\b', 'technician'),
        # Customers
        (r'\b(name\s+all\s+customers|list\s+all\s+customers|show\s+all\s+customers|who\s+are\s+the\s+customers|show\s+me\s+every\s+customer|give\s+me\s+the\s+customers|list\s+customers|all\s+customers|show\s+customer\s+names|get\s+customers|customers\s+list)\b', 'customer'),
        # Services
        (r'\b(name\s+all\s+services|list\s+all\s+services|show\s+all\s+services|what\s+services\s+do\s+we\s+have|what\s+services\s+do\s+we\s+offer|show\s+service\s+catalog|give\s+me\s+all\s+services|list\s+services|all\s+services|services\s+list|catalog)\b', 'service'),
    ]
    for pattern, target in list_patterns:
        if re.search(pattern, lower_query):
            filters = {}
            if 'active' in lower_query or 'available' in lower_query:
                filters['active_only'] = True
            return StructuredQuerySpec(
                intent='list',
                target_entity_type=target,
                filters=filters,
                raw_query=raw_query
            )

    # 4. COUNT QUERIES
    # e.g. "how many technicians are there?", "how many customers do we have?", "how many services are available?"
    count_patterns = [
        (r'\b(how\s+many\s+technicians|number\s+of\s+technicians|total\s+technicians|count\s+of\s+technicians)\b', 'technician'),
        (r'\b(how\s+many\s+customers|number\s+of\s+customers|total\s+customers|count\s+of\s+customers)\b', 'customer'),
        (r'\b(how\s+many\s+services|number\s+of\s+services|total\s+services|count\s+of\s+services)\b', 'service'),
        (r'\b(how\s+many\s+bookings|total\s+bookings|number\s+of\s+bookings|count\s+of\s+bookings)\b', 'booking'),
        (r'\b(how\s+many\s+complaints|unresolved\s+complaints|open\s+complaints|total\s+complaints)\b', 'complaint'),
    ]
    for pattern, target in count_patterns:
        if re.search(pattern, lower_query):
            date_start, date_end, date_preset, _, _ = extract_date_range(raw_query)
            return StructuredQuerySpec(
                intent='count',
                target_entity_type=target,
                date_preset=date_preset,
                date_start=date_start,
                date_end=date_end,
                raw_query=raw_query
            )

    # 5. Extract Dates
    date_start, date_end, date_preset, date_label, remaining_text = extract_date_range(raw_query)

    # Timeframe modifiers for income/earnings
    if re.search(r'\b(annual\s+income|yearly\s+income|income\s+this\s+year|earnings\s+this\s+year|this\s+year\'s\s+earnings|in\s+2026)\b', lower_query):
        date_preset = 'this_year'
        date_start, date_end, *_ = extract_date_range('this year')
    elif re.search(r'\b(monthly\s+income|income\s+this\s+month|earnings\s+this\s+month|this\s+month\'s\s+earnings)\b', lower_query):
        date_preset = 'this_month'
        date_start, date_end, *_ = extract_date_range('this month')
    elif re.search(r'\b(weekly\s+income|income\s+this\s+week|earnings\s+this\s+week)\b', lower_query):
        date_preset = 'this_week'
        date_start, date_end, *_ = extract_date_range('this week')

    # 6. Resolve Entities
    entities, clarification = resolve_entities(raw_query, context)
    if clarification:
        return StructuredQuerySpec(
            intent='clarification',
            clarification_message=clarification,
            raw_query=raw_query
        )

    primary_entity = entities[0] if len(entities) >= 1 else None
    secondary_entity = entities[1] if len(entities) >= 2 else None

    # 7. Check Period Comparison Patterns
    compare_periods_match = re.search(
        r'\b(compare\s+(?:this|the|current)\s+month.*?last\s+month|was\s+sales\s+higher\s+(?:this|last)\s+month|sales\s+this\s+month\s+vs\s+last\s+month)\b',
        lower_query
    )
    if compare_periods_match or ('compare' in lower_query and ('last month' in lower_query or 'yesterday' in lower_query)):
        return StructuredQuerySpec(
            intent='compare_periods',
            date_preset='this_month',
            compare_preset='previous_month',
            metrics=['gross_sales'],
            raw_query=raw_query
        )

    # 8. Check Entity Comparison Patterns
    if ('compare' in lower_query or 'earned more' in lower_query or 'higher' in lower_query) and primary_entity and secondary_entity:
        metrics = detect_metrics_in_text(raw_query, primary_entity.entity_type)
        return StructuredQuerySpec(
            intent='compare_entities',
            entity=primary_entity,
            secondary_entity=secondary_entity,
            metrics=metrics or ['technician_earnings' if primary_entity.entity_type == 'technician' else 'bookings'],
            raw_query=raw_query
        )

    # 9. Check Cross-Relational Patterns
    if re.search(r'\b(which\s+customer\s+booked.*?most|who\s+booked.*?most)\b', lower_query) and primary_entity and primary_entity.entity_type == 'technician':
        return StructuredQuerySpec(
            intent='cross_relational',
            entity=primary_entity,
            cross_relation_type='customer_who_booked_technician_most',
            raw_query=raw_query
        )

    if re.search(r'\b(which\s+technician\s+served.*?most|who\s+served.*?most)\b', lower_query) and primary_entity and primary_entity.entity_type == 'customer':
        return StructuredQuerySpec(
            intent='cross_relational',
            entity=primary_entity,
            cross_relation_type='technician_who_served_customer_most',
            raw_query=raw_query
        )

    if re.search(r'\b(which\s+service\s+did.*?book.*?most|service.*?booked.*?most\s+often)\b', lower_query) and primary_entity and primary_entity.entity_type == 'customer':
        return StructuredQuerySpec(
            intent='cross_relational',
            entity=primary_entity,
            cross_relation_type='service_booked_most_by_customer',
            raw_query=raw_query
        )

    if re.search(r'\b(technician.*?most\s+sales|who\s+generated.*?most\s+sales)\b', lower_query) and primary_entity and primary_entity.entity_type == 'service':
        return StructuredQuerySpec(
            intent='cross_relational',
            entity=primary_entity,
            cross_relation_type='technician_most_sales_for_service',
            raw_query=raw_query
        )

    if re.search(r'\b(who\s+spent\s+the\s+most|which\s+customer\s+spent.*?most)\b', lower_query) and primary_entity and primary_entity.entity_type == 'service':
        return StructuredQuerySpec(
            intent='cross_relational',
            entity=primary_entity,
            cross_relation_type='customer_most_spent_for_service',
            raw_query=raw_query
        )

    # 10. TECHNICIAN SERVICES RELATIONSHIP QUERY
    # e.g. "what service does Sayan Paul provide?", "what services does Sayan Paul provide?", "which services does this technician provide?"
    if re.search(r'\b(what\s+service|what\s+services|which\s+service|which\s+services)\b', lower_query) and re.search(r'\b(provide|handle|work\s+on|assigned\s+to|do)\b', lower_query):
        if primary_entity and primary_entity.entity_type == 'technician':
            return StructuredQuerySpec(
                intent='technician_services',
                entity=primary_entity,
                raw_query=raw_query
            )

    # 11. ENTITY DETAIL REQUEST ("show Sayan Paul's details", "tell me about Sayan Paul")
    if re.search(r'\b(details?|profile|information|about|who\s+is)\b', lower_query) and primary_entity:
        # If no specific financial metric keyword was requested, treat as full entity details
        if not re.search(r'\b(spend|spent|earn|earnings|income|sales|balance|withdrawn)\b', lower_query):
            return StructuredQuerySpec(
                intent='entity_details',
                entity=primary_entity,
                raw_query=raw_query
            )

    # 12. Check Rankings / Superlatives
    if re.search(r'\b(who\s+earned\s+the\s+most|highest\s+earning\s+technician|top\s+earning|most\s+income)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='technician',
            metrics=['technician_earnings'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(completed\s+the\s+most\s+jobs|most\s+jobs\s+done|most\s+work|who\s+did\s+the\s+most\s+work|top\s+technician)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='technician',
            metrics=['completed_jobs'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(service.*?booked\s+the\s+most|most\s+booked\s+service|top\s+service|popular\s+service)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='service',
            metrics=['bookings'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(service.*?most\s+sales|service.*?most\s+revenue|top\s+grossing\s+service)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='service',
            metrics=['gross_sales'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(least\s+booked\s+service|lowest\s+booked\s+service)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='service',
            metrics=['bookings'],
            ranking_direction='asc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(who\s+spent\s+the\s+most|top\s+spending\s+customer|top\s+spender)\b', lower_query):
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target='customer',
            metrics=['customer_spending'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    if re.search(r'\b(who\s+joined|joined\s+most\s+recently|recently\s+joined|latest\s+signups?)\b', lower_query):
        target = 'technician' if 'technician' in lower_query else 'customer'
        return StructuredQuerySpec(
            intent='ranking',
            ranking_target=target,
            metrics=['joined_date'],
            ranking_direction='desc',
            ranking_limit=5,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    # 13. Entity Lookup (Single or Multi-Metric / Attribute)
    if primary_entity:
        metrics = detect_metrics_in_text(raw_query, primary_entity.entity_type)
        if not metrics:
            # Default sensible metrics for entity type if none explicitly detected
            if primary_entity.entity_type == 'technician':
                metrics = ['technician_earnings', 'completed_jobs', 'rating']
            elif primary_entity.entity_type == 'customer':
                metrics = ['customer_spending', 'bookings']
            elif primary_entity.entity_type == 'service':
                metrics = ['service_price', 'bookings', 'gross_sales']

        intent = 'multi_metric' if len(metrics) > 1 else 'lookup'
        return StructuredQuerySpec(
            intent=intent,
            entity=primary_entity,
            metrics=metrics,
            date_preset=date_preset,
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    # 14. System-Wide Aggregations (e.g. "Today's sales, bookings and new customers")
    system_metrics = detect_metrics_in_text(raw_query, entity_type='platform')
    if system_metrics:
        intent = 'multi_metric' if len(system_metrics) > 1 else 'lookup'
        return StructuredQuerySpec(
            intent=intent,
            metrics=system_metrics,
            date_preset=date_preset or 'this_month',
            date_start=date_start,
            date_end=date_end,
            raw_query=raw_query
        )

    # Fallback / Unrecognized within platform scope
    return StructuredQuerySpec(
        intent='clarification',
        clarification_message=(
            "I couldn't identify a specific technician, customer, service, or metric in your question. "
            "You can ask about sales, bookings, technician earnings, customer spending, service stats, "
            "or list entities by asking 'name all technicians' or 'list all services'."
        ),
        raw_query=raw_query
    )
