"""
Entity Resolver for Admin Data Assistant
Seva Bandhu Platform

Dynamically identifies and resolves Technicians, Customers, and Services from the database.
Handles disambiguation, apostrophe normalization, first-name lookups, spelling/phonetic variants (e.g. Pal <-> Paul),
and context clues.
Zero hardcoded entity names.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from core.models import Technician_signup, customer_signup, Service


@dataclass
class ResolvedEntity:
    entity_type: str  # 'technician', 'customer', 'service'
    entity_id: int
    identifier: str   # username or service name
    display_name: str
    raw_object: Any
    matched_token: str
    score: int = 100


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates simple Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def tokens_match_or_similar(t1: str, t2: str) -> bool:
    """Checks if two word tokens match exactly or are close spelling/transliteration variants."""
    t1, t2 = t1.lower(), t2.lower()
    if t1 == t2:
        return True

    # Known Indian transliteration variants
    variants = [
        ({'pal', 'paul'}, True),
        ({'chowdhury', 'choudhury', 'chaudhary'}, True),
        ({'mukherjee', 'mukhopadhyay'}, True),
        ({'banerjee', 'bandyopadhyay'}, True),
        ({'chatterjee', 'chattopadhyay'}, True),
    ]
    for pair_set, match_val in variants:
        if t1 in pair_set and t2 in pair_set:
            return True

    # Allow edit distance 1 for tokens of length >= 3
    if len(t1) >= 3 and len(t2) >= 3 and abs(len(t1) - len(t2)) <= 1:
        if levenshtein_distance(t1, t2) <= 1:
            return True

    return False


def normalize_token(s: str) -> str:
    """Normalize text for matching: lowercased, stripped punctuation, collapsed spaces."""
    if not s:
        return ''
    # Remove apostrophe-s and trailing punctuation (handles ASCII ' and Unicode ’ and s')
    s = re.sub(r"['’]s\b", '', s, flags=re.IGNORECASE)
    s = re.sub(r"s['’]\b", 's', s, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\s-]", ' ', s)
    return ' '.join(s.strip().lower().split())


def extract_query_words(query_text: str) -> List[str]:
    """Extracts normalized individual word tokens from query."""
    norm = normalize_token(query_text)
    return [w for w in norm.split() if w]


def find_services(query_text: str) -> List[ResolvedEntity]:
    """
    Finds service entities mentioned in the query.
    Matches against all services currently in the database.
    """
    norm_query = ' ' + normalize_token(query_text) + ' '
    services = Service.objects.all()
    matches = []

    for s in services:
        norm_name = normalize_token(s.name)
        pattern = r'(?:\b|\s)' + re.escape(norm_name) + r'(?:\b|\s)'
        if re.search(pattern, norm_query):
            matches.append(ResolvedEntity(
                entity_type='service',
                entity_id=s.id,
                identifier=s.name,
                display_name=s.name,
                raw_object=s,
                matched_token=s.name,
                score=100
            ))
            continue

        # Check token-level containment (e.g. "ac repair" matches "AC REPAIR")
        service_tokens = norm_name.split()
        if len(service_tokens) > 1 and all(re.search(r'\b' + re.escape(tk) + r'\b', norm_query) for tk in service_tokens):
            matches.append(ResolvedEntity(
                entity_type='service',
                entity_id=s.id,
                identifier=s.name,
                display_name=s.name,
                raw_object=s,
                matched_token=s.name,
                score=90
            ))

    matches.sort(key=lambda x: len(x.identifier), reverse=True)
    return matches


def match_user_candidate(
    query_text: str,
    query_words: List[str],
    user_id: int,
    username: str,
    email: str,
    contact: str,
    first_name: str,
    last_name: str,
    entity_type: str,
    raw_object: Any
) -> Optional[ResolvedEntity]:
    """
    Evaluates whether a given technician or customer matches the query words.
    Returns ResolvedEntity with match score if matched, else None.
    """
    lower_query = query_text.lower()

    # 1. Exact email match (Score 100)
    if email and email.lower() in lower_query:
        return ResolvedEntity(
            entity_type=entity_type,
            entity_id=user_id,
            identifier=username,
            display_name=f"{username} ({entity_type.title()})",
            raw_object=raw_object,
            matched_token=email,
            score=100
        )

    # 2. Exact username match in normalized query (Score 95)
    norm_user = normalize_token(username)
    norm_query = ' ' + normalize_token(query_text) + ' '
    if norm_user and len(norm_user) >= 2:
        if re.search(r'(?:\b|\s)' + re.escape(norm_user) + r'(?:\b|\s)', norm_query):
            return ResolvedEntity(
                entity_type=entity_type,
                entity_id=user_id,
                identifier=username,
                display_name=f"{username} ({entity_type.title()})",
                raw_object=raw_object,
                matched_token=username,
                score=95
            )

    # 3. Full name match (Score 95)
    full_name = f"{first_name} {last_name}".strip()
    norm_full = normalize_token(full_name)
    if norm_full and len(norm_full) >= 3:
        if re.search(r'(?:\b|\s)' + re.escape(norm_full) + r'(?:\b|\s)', norm_query):
            return ResolvedEntity(
                entity_type=entity_type,
                entity_id=user_id,
                identifier=username,
                display_name=f"{full_name} ({username})",
                raw_object=raw_object,
                matched_token=full_name,
                score=95
            )

    # 4. Multi-token match with spelling tolerance (e.g. "Sayan Paul" matching "SAYAN PAL") (Score 85)
    name_source = norm_full if norm_full else norm_user
    user_tokens = name_source.split()

    if len(user_tokens) >= 2:
        # Check if every token in user's name has a corresponding matching/similar word in query
        matched_count = 0
        matched_words = []
        for u_tok in user_tokens:
            for q_word in query_words:
                if tokens_match_or_similar(u_tok, q_word):
                    matched_count += 1
                    matched_words.append(q_word)
                    break

        if matched_count == len(user_tokens):
            return ResolvedEntity(
                entity_type=entity_type,
                entity_id=user_id,
                identifier=username,
                display_name=f"{username} ({entity_type.title()})",
                raw_object=raw_object,
                matched_token=" ".join(matched_words),
                score=85
            )

    # 5. Single first-name token match (e.g. "Sayan" or "Sayan's") (Score 70)
    # Only if token is >= 3 characters and not a common stopword
    stopwords = {'who', 'what', 'which', 'how', 'give', 'show', 'tell', 'all', 'any', 'the', 'this', 'that', 'with', 'from'}
    first_token = user_tokens[0] if user_tokens else ''
    if len(first_token) >= 3 and first_token not in stopwords:
        for q_word in query_words:
            if q_word not in stopwords and tokens_match_or_similar(first_token, q_word):
                return ResolvedEntity(
                    entity_type=entity_type,
                    entity_id=user_id,
                    identifier=username,
                    display_name=f"{username} ({entity_type.title()})",
                    raw_object=raw_object,
                    matched_token=q_word,
                    score=70
                )

    return None


def resolve_entities(
    query_text: str,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[List[ResolvedEntity], Optional[str]]:
    """
    Main entity resolution orchestrator.
    Dynamically searches Technicians, Customers, and Services in database.
    Returns: (list_of_resolved_entities, ambiguity_clarification_message_if_any)
    """
    lower_query = query_text.lower()
    query_words = extract_query_words(query_text)
    services = find_services(query_text)

    # Search Technicians
    tech_candidates = []
    for t in Technician_signup.objects.select_related('user').all():
        match = match_user_candidate(
            query_text=query_text,
            query_words=query_words,
            user_id=t.id,
            username=t.username,
            email=t.email,
            contact=t.contact,
            first_name=t.user.first_name,
            last_name=t.user.last_name,
            entity_type='technician',
            raw_object=t
        )
        if match:
            tech_candidates.append(match)

    # Search Customers
    cust_candidates = []
    for c in customer_signup.objects.select_related('user').all():
        match = match_user_candidate(
            query_text=query_text,
            query_words=query_words,
            user_id=c.id,
            username=c.username,
            email=c.email,
            contact=c.contact,
            first_name=c.user.first_name,
            last_name=c.user.last_name,
            entity_type='customer',
            raw_object=c
        )
        if match:
            cust_candidates.append(match)

    # Sort each group by match score descending (exact > multi-token > first-name)
    tech_candidates.sort(key=lambda x: x.score, reverse=True)
    cust_candidates.sort(key=lambda x: x.score, reverse=True)

    # Filter out lower-score candidates if we have high-score candidate(s)
    if tech_candidates and tech_candidates[0].score >= 85:
        tech_candidates = [t for t in tech_candidates if t.score >= 85]
    if cust_candidates and cust_candidates[0].score >= 85:
        cust_candidates = [c for c in cust_candidates if c.score >= 85]

    # Check for same-first-name ambiguity within technicians (e.g. "Soham" -> Soham Pal vs Soham Roy Chowdhury)
    if len(tech_candidates) > 1 and tech_candidates[0].score == 70 and tech_candidates[1].score == 70:
        names_str = " and ".join([f"'{t.identifier}'" for t in tech_candidates[:3]])
        clarification = f"I found multiple technicians matching '{tech_candidates[0].matched_token}' ({names_str}). Please specify the full name."
        return [], clarification

    # Check for same-first-name ambiguity within customers
    if len(cust_candidates) > 1 and cust_candidates[0].score == 70 and cust_candidates[1].score == 70:
        names_str = " and ".join([f"'{c.identifier}'" for c in cust_candidates[:3]])
        clarification = f"I found multiple customers matching '{cust_candidates[0].matched_token}' ({names_str}). Please specify the full name."
        return [], clarification

    # Check for Technician vs Customer collision with identical name
    if tech_candidates and cust_candidates:
        t_top = tech_candidates[0]
        c_top = cust_candidates[0]
        # Check if they matched the same token
        if tokens_match_or_similar(t_top.matched_token, c_top.matched_token):
            tech_clues = ['technician', 'tech', 'earned', 'earning', 'income', 'wallet', 'withdrawn', 'withdrawal', 'service', 'job', 'rating']
            cust_clues = ['customer', 'spent', 'spending', 'paid', 'order', 'booked']
            is_tech = any(clue in lower_query for clue in tech_clues)
            is_cust = any(clue in lower_query for clue in cust_clues)

            if is_tech and not is_cust:
                cust_candidates = []
            elif is_cust and not is_tech:
                tech_candidates = []
            else:
                clarification = (
                    f"I found both a technician '{t_top.identifier}' and a customer '{c_top.identifier}'. "
                    f"Did you mean the technician or the customer?"
                )
                return [], clarification

    resolved_list = []
    if tech_candidates:
        resolved_list.append(tech_candidates[0])
        # If there's a second distinct technician mentioned (e.g. for comparison)
        if len(tech_candidates) > 1 and tech_candidates[1].identifier != tech_candidates[0].identifier:
            resolved_list.append(tech_candidates[1])

    if cust_candidates:
        resolved_list.append(cust_candidates[0])
        if len(cust_candidates) > 1 and cust_candidates[1].identifier != cust_candidates[0].identifier:
            resolved_list.append(cust_candidates[1])

    for s in services:
        resolved_list.append(s)

    # Check context continuation (pronoun "he", "she", "this technician", etc.)
    if not resolved_list and context and context.get('last_entity'):
        last_ent = context['last_entity']
        pronoun_words = ['he', 'him', 'his', 'she', 'her', 'they', 'them', 'this technician', 'that technician', 'this customer', 'that customer', 'this service', 'that service']
        if any(re.search(r'\b' + re.escape(w) + r'\b', lower_query) for w in pronoun_words) or 'what about' in lower_query or lower_query.startswith('what service') or lower_query.startswith('which service'):
            if last_ent['entity_type'] == 'technician':
                t_obj = Technician_signup.objects.filter(username=last_ent['identifier']).first()
                if t_obj:
                    resolved_list.append(ResolvedEntity(
                        entity_type='technician',
                        entity_id=t_obj.id,
                        identifier=t_obj.username,
                        display_name=f"{t_obj.username} (Technician)",
                        raw_object=t_obj,
                        matched_token=last_ent['identifier'],
                        score=100
                    ))
            elif last_ent['entity_type'] == 'customer':
                c_obj = customer_signup.objects.filter(username=last_ent['identifier']).first()
                if c_obj:
                    resolved_list.append(ResolvedEntity(
                        entity_type='customer',
                        entity_id=c_obj.id,
                        identifier=c_obj.username,
                        display_name=f"{c_obj.username} (Customer)",
                        raw_object=c_obj,
                        matched_token=last_ent['identifier'],
                        score=100
                    ))
            elif last_ent['entity_type'] == 'service':
                s_obj = Service.objects.filter(name=last_ent['identifier']).first()
                if s_obj:
                    resolved_list.append(ResolvedEntity(
                        entity_type='service',
                        entity_id=s_obj.id,
                        identifier=s_obj.name,
                        display_name=s_obj.name,
                        raw_object=s_obj,
                        matched_token=last_ent['identifier'],
                        score=100
                    ))

    return resolved_list, None
