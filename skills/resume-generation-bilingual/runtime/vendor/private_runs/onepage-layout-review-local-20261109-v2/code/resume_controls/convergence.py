"""Measured, bounded content-only convergence. No transport, keys or paid entry.

stage(key, request) matches OfflineWorkflow.stage. Supply an authorized adapter
only outside this offline candidate. Semantic verdicts always come from a fresh
whole-candidate source review, never from pagination or citation location.
"""
from copy import deepcopy
from pathlib import Path
from . import document as d
from .common import digest, save, text_hash
from .capacity import feedback
from .requests import build
from .patches import apply_patch, save_application
from .reviews import audit_review, acceptance
from .schemas import VERSION
from .layout_review import evaluate as evaluate_layout


POLICY = ('Use measured pages, overflow and physical text lines, not word limits. '
          'First remove explicitly optional low-relevance whole entries, then '
          'redundant wording. Preserve core education. A claim and its denominator, '
          'sample, actor, owner, not-launched status, uncertainty and other limits '
          'are indivisible: keep together or remove the entire claim. Do not infer '
          'facts or use keyword substitution. Do not change fonts, margins, spacing '
          'or templates. Return only existing stable-ID patch operations.')
TAIL_POLICY = ('For each measured multi-line bullet the final physical line must use '
               'more than half its available body width; two-thirds to four-fifths is '
               'a preference, not a fact-generation target. Short single-line bullets '
               'are exempt. Rewrite only with source-supported wording. Do not add '
               'facts, pad text, delete qualifiers, insert unapproved breaks, shrink '
               'fonts or change margins/line spacing to satisfy width.')


def mechanical(m):
    return (type(m.get('pages')) is int and m['pages'] > 0
            and len(m.get('pages_detail', [])) == m['pages']
            and m.get('word_pdf_mapping', {}).get('word_pdf_body_match_in_order') is True
            and m.get('fonts_validated') is True
            and m.get('actual_clipping_detected') is False
            and m.get('nonpunctuation_body_overflow') is False
            and m.get('date_month_orphan') is False
            and m.get('balanced_markdown_remaining') is False)


def geometry(m):
    """Exact fixed layout comparison, not permission to choose a smaller baseline."""
    return {'geometry_pt': m.get('geometry_pt'),
            'font_sizes': m.get('explicit_run_font_sizes_pt')}


def validate_plan(doc, source, plan):
    if plan is None:
        return
    if plan.get('candidate_version') != d.version(doc) or plan.get('source_sha256') != text_hash(source):
        raise ValueError('selection_or_atomic_group_plan_stale')
    ns = d.units(doc)
    for item in plan.get('optional_entries', []):
        if (item.get('optional') is not True or item.get('id') not in ns
                or ns[item['id']]['kind'] != 'entry'
                or type(item.get('priority')) is not int or not 1 <= item['priority'] <= 5
                or not item.get('reason') or not item.get('source_refs')):
            raise ValueError('explicit_source_bound_optional_entry_required')
    for group in plan.get('atomic_groups', []):
        if not group.get('id') or not group.get('anchors'):
            raise ValueError('atomic_group_empty')
        for a in group['anchors']:
            if a.get('node_id') not in ns or not a.get('quote') or a['quote'] not in ns[a['node_id']]['text']:
                raise ValueError('atomic_anchor_not_literal_in_current_candidate')


def boundary_findings(before, after, groups):
    """Conservative literal guards, not language understanding or replacements.

    If a reviewed anchor is paraphrased, stop for a newly reviewed boundary plan.
    Matching scattered keywords never certifies a paraphrase. Whole group removal
    is allowed; final review still evaluates material omissions.
    """
    old, new = d.units(before), d.units(after)
    findings = []
    for g in groups:
        anchors = [a for a in g['anchors'] if a['node_id'] in old]
        if not anchors:
            continue
        if all(a['node_id'] not in new for a in anchors):
            continue
        broken = [a for a in anchors if a['node_id'] not in new
                  or a['quote'] not in new[a['node_id']]['text']
                  or old[a['node_id']]['parent'] != new[a['node_id']]['parent']]
        if broken:
            findings.append({'group_id': g['id'], 'code': 'claim_boundary_change_needs_review',
                             'anchors_changed_or_missing': broken,
                             'action': 'Keep the complete group, delete it entirely, or obtain a new source-reviewed boundary plan.'})
    return findings


def optional_patch(doc, plan):
    """No automatic relevance inference. Reviewer/user supplies ranked options."""
    if not plan:
        return None
    ns = d.units(doc)
    options = sorted(plan.get('optional_entries', []), key=lambda x: (x['priority'], x['id']))
    for item in options:
        if item['id'] not in ns:
            continue
        target = item['id']
        parent = ns[target]['parent']
        if len([n for n in doc['nodes'] if n['parent'] == parent and n['kind'] == 'entry']) == 1:
            target = parent  # Empty sections must be explicitly deleted by the existing contract.
        if d.descendants(doc, target) & set(doc['protected_ids']):
            continue
        return {'schema_version': VERSION, 'base_version': d.version(doc), 'operations': [
            {'op': 'delete', 'target_id': target, 'original_hash': text_hash(ns[target]['text']),
             'reason': item['reason'], 'source_refs': deepcopy(item['source_refs'])}]}
    return None


def converge(doc, *, source, jd, skill, directory, renderer, patch_stage=None,
             review_stage=None, plan=None, max_rounds=2, clarification=None, known_issues=()):
    """Render -> patch -> render (at most twice) -> independent whole-source review.

    Calls are per-case. Failure produces an actionable local result, no batch STOP.
    An existing directory is not replayed: an uncertain adapter action is never resent.
    """
    if type(max_rounds) is not int or not 0 <= max_rounds <= 2:
        raise ValueError('maximum_two_content_revision_rounds')
    d.validate(doc)
    validate_plan(doc, source, plan)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    original = deepcopy(doc)
    current = deepcopy(doc)
    # Protect complete education entries even if the caller did not annotate them.
    current['protected_ids'] = sorted(set(current['protected_ids']) |
        {n['id'] for n in current['nodes'] if n['kind'] == 'entry' and n['purpose'] == 'education'})
    # Protection is metadata, so bind a caller plan to this effective version too.
    save(root / 'input.json', original)
    save(root / 'effective-input.json', current)
    save(root / 'policy.json', {'max_rounds': max_rounds, 'policy': POLICY, 'plan': plan,
                              'source_sha256': text_hash(source), 'jd_sha256': text_hash(jd)})
    history, changed, review, m = [], set(), None, {}
    initial_geometry, initial_layout, initial_style = None, None, None
    pending_items, quality = [], None
    reason, next_action = 'revision_limit_reached', 'Choose fewer complete optional claims or request a new source-reviewed concise version; a two-page draft is not deliverable as one page.'
    calls = {'patch': 0, 'review': 0}
    try:
        for round_no in range(max_rounds + 1):
            step = root / f'round-{round_no:02d}'
            step.mkdir()
            save(step / 'candidate.json', current)
            rendered = renderer(deepcopy(current), step / 'render')
            save(step / 'render-result.json', rendered)
            if rendered.get('candidate_version') != d.version(current):
                raise ValueError('render_candidate_version_mismatch')
            m = rendered['measurement']
            if not mechanical(m):
                reason, next_action = 'render_integrity_blocked', 'Inspect full-text mapping, clipping, fonts and date wrapping before editing content.'
                break
            # An explicitly approved presentation can be chosen before round 0.
            # Its version is independent of the non-negotiable typography lock.
            layout = rendered.get('typography_fingerprint', rendered.get('fixed_layout_sha256'))
            style = rendered.get('style_fingerprint', rendered.get('fixed_layout_sha256'))
            pending_items = rendered.get('pending_items', [])
            if not layout or not m.get('geometry_pt') or not m.get('explicit_run_font_sizes_pt'):
                raise ValueError('fixed_layout_evidence_required')
            if initial_geometry is None:
                initial_geometry, initial_layout, initial_style = geometry(m), layout, style
            if geometry(m) != initial_geometry or layout != initial_layout:
                reason, next_action = 'layout_change_rejected', 'Restore the exact approved template, fonts, margins and line spacing; do not shrink to fit.'
                break
            if style != initial_style:
                reason, next_action = 'presentation_version_changed', 'Start from the original candidate with the newly approved presentation version; compare every content round under the same style.'
                break
            quality = evaluate_layout(current, rendered)
            pending_items = list(pending_items) + quality['blocking_findings']
            save(step / 'layout-review.json', quality)
            cap = feedback(current, m, rendered.get('heading_locations'), rendered.get('tail_unit_ids'))
            cap['presentation_review'] = quality
            # Include all measured physical lines, not only the tail or a character estimate.
            cap['physical_lines_by_page'] = [{'page': p['page'], 'text_lines': p.get('text_lines', [])}
                                             for p in m['pages_detail']]
            save(step / 'capacity.json', cap)
            history.append({'round': round_no, 'candidate_version': d.version(current),
                            'pages': m['pages'], 'overflow_pt': cap['observed_overflow_flow_span_pt'],
                            'body_utilization_pct': [p.get('body_utilization_pct') for p in m['pages_detail']],
                            'layout_review_status': quality['status']})
            if m['pages'] == 1 and not quality['blocking_findings']:
                reason, next_action = 'one_page_needs_source_review', 'Review the entire current candidate against the source, including omissions and all changed claims.'
                break
            if quality['blocking_findings'] and not quality['content_rewrite_possible']:
                reason, next_action = 'layout_review_required', 'Resolve unverified or failed visible bold/physical measurements on this case; a one-page render is not completion.'
                break
            if round_no == max_rounds:
                if quality['blocking_findings']:
                    reason, next_action = 'layout_revision_limit_reached', 'The configured content revision limit has been reached (never more than two). Review the measured short-tail bullets locally while preserving facts, claim boundaries and typography.'
                break
            patch = optional_patch(current, plan) if m['pages'] > 1 else None
            if patch is None:
                if patch_stage is None:
                    reason, next_action = ('layout_review_required', 'Review the measured multi-line short tails; supply a source-preserving patch callback or revise locally. Never pad short single-line bullets.') if quality['blocking_findings'] else ('content_selection_required', 'Supply source-reviewed optional entry priorities or an authorized content-patch callback; the measured overflow and full text lines are saved.')
                    break
                request = build('patch', skill=skill, material_text=source, jd_text=jd,
                                candidate=current, capacity=cap, issues=[POLICY, TAIL_POLICY])
                save(step / 'patch-request.json', request)
                calls['patch'] += 1
                patch = patch_stage(f'patch-{round_no + 1}', deepcopy(request))
                origin = 'stage_callback'
            else:
                origin = 'explicit_optional_entry_selection'
            save(step / 'patch-response.json', patch)
            proposed, audit = apply_patch(current, patch, source, jd)
            boundaries = boundary_findings(current, proposed, (plan or {}).get('atomic_groups', []))
            save(step / 'boundary-audit.json', {'findings': boundaries,
                 'coverage': 'explicit_groups_only' if plan else 'unknown_requires_whole_source_review',
                 'source_support_certified': False})
            if boundaries:
                reason, next_action = 'boundary_change_rejected', boundaries[0]['action']
                break
            save_application(step / 'applied', proposed, {**audit, 'origin': origin})
            changed.update(audit['affected_ids'])
            current = proposed
        # Source review is independent of page count, including exhausted 2-page cases.
        if review_stage is not None and reason not in {'layout_change_rejected', 'render_integrity_blocked'}:
            request = build('final_review', skill=skill, material_text=source, jd_text=jd, candidate=current)
            save(root / 'final-review-request.json', request)
            calls['review'] += 1
            raw = review_stage('final-review', deepcopy(request))
            save(root / 'final-review-response.json', raw)
            review = audit_review(current, raw, source, changed_ids=changed, jd_text=jd)
            save(root / 'final-review-audit.json', review)
    except Exception as exc:
        reason, next_action = 'case_blocked', 'Inspect the preserved failure; correct the local input or dependency in a new run. Do not automatically retry an uncertain callback.'
        save(root / 'failure.json', {'type': type(exc).__name__, 'reason': str(exc)})
    result_gate = acceptance(protocol_usable=True, citations_locatable=bool(review),
        review_audit=review, known_issues=known_issues, measurement=m,
        clarification=clarification or {}, visual_preferences={'editorial_review': 'pending'},
        pending_items=pending_items)
    if reason == 'one_page_needs_source_review' and review is not None:
        reason = 'one_page_source_review_passed' if result_gate['complete_flow_pass'] else 'one_page_source_review_blocked'
        next_action = 'Complete final editorial/visual review before delivery.' if result_gate['complete_flow_pass'] else 'Resolve the independent source-review findings; a single page is not a factual pass.'
    # Never let acceptance of an older candidate override a rejected proposal or infrastructure failure.
    eligible = reason == 'one_page_source_review_passed' and result_gate['complete_flow_pass']
    out = {'status': reason, 'next_action': next_action, 'history': history,
           'candidate_version': d.version(current), 'rounds_applied': current['revision'] - original['revision'],
           'callback_calls': calls, 'page_count': m.get('pages'), 'acceptance': result_gate,
           'eligible_for_editorial_review': bool(eligible), 'automatic_fact_certification': False,
           'batch_stop': False, 'input_object_unchanged': doc == original,
           'source_review_status': review['source_judgment'] if review else 'unreviewed'}
    out['layout_review'] = quality
    save(root / 'candidate.json', current)
    save(root / 'RESULT.json', out)
    return out
