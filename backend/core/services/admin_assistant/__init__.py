"""
Admin Data Assistant Package
Seva Bandhu Platform

Main entry point for processing admin natural language queries.
"""

from typing import Optional, Dict, Any

from .parser import parse_admin_query
from .executor import execute_query
from .formatter import format_query_response


def process_admin_query(
    query_text: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parses, validates, executes, and formats an admin query.
    Returns:
    {
        'status': 'ok' | 'clarification' | 'unsupported' | 'help' | 'error',
        'answer': str,
        'intent': str,
        'context': dict,
        'data': dict
    }
    """
    if not query_text or not query_text.strip():
        return {
            'status': 'error',
            'answer': "Please enter a question to ask the data assistant.",
            'intent': 'empty',
            'context': context or {},
            'data': {}
        }

    try:
        # 1. Parse into StructuredQuerySpec
        spec = parse_admin_query(query_text, context)

        # 2. Execute ORM aggregations
        raw_result = execute_query(spec)

        # 3. Format human-readable response
        answer = format_query_response(raw_result)

        # 4. Update conversation context for follow-up questions
        updated_context = dict(context or {})
        if spec.entity:
            updated_context['last_entity'] = {
                'id': spec.entity.entity_id,
                'entity_type': spec.entity.entity_type,
                'identifier': spec.entity.identifier,
                'display_name': spec.entity.display_name,
            }
        if spec.metrics:
            updated_context['last_metric'] = spec.metrics[0]

        # Determine status
        status = 'ok'
        if spec.intent == 'clarification':
            status = 'clarification'
        elif spec.intent == 'out_of_scope':
            status = 'unsupported'
        elif spec.intent == 'help':
            status = 'help'

        return {
            'status': status,
            'answer': answer,
            'intent': spec.intent,
            'context': updated_context,
            'data': raw_result
        }

    except Exception as e:
        return {
            'status': 'error',
            'answer': "An unexpected error occurred while processing your query. Please rephrase or specify the entity name clearly.",
            'intent': 'error',
            'context': context or {},
            'data': {'error': str(e)}
        }

