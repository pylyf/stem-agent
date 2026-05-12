def run(params: dict) -> dict:
    docs = params.get('docs', {})
    profile = params.get('profile', {})
    rubric = params.get('rubric', {})

    all_text = ' '.join(docs.values()).lower()

    entrypoints = profile.get('entrypoints', [])
    components = profile.get('components', [])
    setup_commands = profile.get('setup_commands', [])

    # Criterion: entrypoint_coverage - fraction of entrypoints mentioned in docs
    entrypoint_hits = sum(1 for ep in entrypoints if ep.lower() in all_text)
    entrypoint_coverage = entrypoint_hits / max(len(entrypoints), 1)

    # Criterion: component_coverage - fraction of major components mentioned
    component_hits = sum(1 for c in components if c.lower() in all_text)
    component_coverage = component_hits / max(len(components), 1)

    # Criterion: setup_accuracy - presence of all setup commands verbatim in docs
    setup_hits = sum(1 for cmd in setup_commands if cmd.lower() in all_text)
    setup_accuracy = setup_hits / max(len(setup_commands), 1)

    # Criterion: hallucination_avoidance - simple heuristic: no phrases indicating uncertainty
    hallucination_terms = ['maybe', 'might', 'could be', 'possibly', 'unclear', 'unknown']
    hallucination_hits = sum(all_text.count(term) for term in hallucination_terms)
    hallucination_avoidance = 1.0 if hallucination_hits == 0 else max(0.0, 1.0 - hallucination_hits * 0.1)

    criteria = {
        'entrypoint_coverage': entrypoint_coverage,
        'component_coverage': component_coverage,
        'setup_accuracy': setup_accuracy,
        'hallucination_avoidance': hallucination_avoidance
    }

    weights = rubric.get('criteria', {})
    total_score = 0.0
    total_weight = 0.0
    for k, w in weights.items():
        score = criteria.get(k, 0.0)
        total_score += score * w
        total_weight += w
    total_score = total_score / total_weight if total_weight > 0 else 0

    passes = total_score >= rubric.get('threshold', 0.7)

    return {
        'criteria': criteria,
        'total': total_score,
        'passes': passes
    }
