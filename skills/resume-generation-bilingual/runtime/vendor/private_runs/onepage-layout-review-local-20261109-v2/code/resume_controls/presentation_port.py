"""Opt-in adapter for the user's approved lead-in/balanced-heading style.

Labels are keyed by stable node ID and bound to exact text. Removed labels are
dropped with their entire claim. Changed text requires a new reviewed label, not
silent rebinding. Added visible label words remain a separate source-review gate.
"""
from pathlib import Path
import importlib.util
import sys
from copy import deepcopy
from . import document as d
from .common import file_hash, read
from .physical_tail_review import measure_tail_lines


def bind_labels(doc, presentation):
    """Convert a reviewed positional presentation to stable-ID bindings once."""
    labels = presentation.get('bullet_labels', {})
    result, seen = {}, set()
    for si, section in enumerate(n for n in doc['nodes'] if n['kind'] == 'section'):
        for ei, entry in enumerate(n for n in doc['nodes'] if n['parent'] == section['id']):
            for bi, bullet in enumerate(n for n in doc['nodes'] if n['parent'] == entry['id'] and n['kind'] == 'sentence'):
                key = f's{si}.e{ei}.b{bi}'
                if key in labels:
                    label = deepcopy(labels[key])
                    if label.get('source_text') != bullet['text']:
                        raise ValueError('label_not_bound_to_initial_text')
                    if key in presentation.get('bullet_breaks', {}):
                        breaking = deepcopy(presentation['bullet_breaks'][key])
                        if breaking.get('source_text') != bullet['text']:
                            raise ValueError('linebreak_not_bound_to_initial_text')
                        label['_bullet_break'] = breaking
                    result[bullet['id']] = label
                    seen.add(key)
    if seen != set(labels) or set(presentation.get('bullet_breaks', {}))-seen:
        raise ValueError('initial_label_path_not_found')
    return result


def make_renderer(module_path, stable_labels):
    """stable_labels may be a map or an explicit local callback(doc)->map.
    A callback can return newly reviewed labels after a text revision. This port
    never infers/reuses a stale label and never makes an external request itself.
    """
    path = Path(module_path)
    expected_hash = file_hash(path)
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('approved_resume_style', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def render(doc, directory):
        if file_hash(path) != expected_hash:
            raise ValueError('approved_style_module_changed_during_run')
        current_labels = stable_labels(deepcopy(doc)) if callable(stable_labels) else stable_labels
        labels, stable_ids, breaks = {}, {}, {}
        for si, section in enumerate(n for n in doc['nodes'] if n['kind'] == 'section'):
            for ei, entry in enumerate(n for n in doc['nodes'] if n['parent'] == section['id']):
                for bi, bullet in enumerate(n for n in doc['nodes'] if n['parent'] == entry['id'] and n['kind'] == 'sentence'):
                    label = current_labels.get(bullet['id'])
                    if label is None:
                        raise ValueError('current_bullet_requires_source_bound_lead_in')
                    if label.get('source_text') != bullet['text']:
                        raise ValueError('changed_bullet_requires_new_reviewed_lead_in')
                    rid = f's{si}.e{ei}.b{bi}'
                    labels[rid] = deepcopy(label)
                    breaking = labels[rid].pop('_bullet_break', None)
                    if breaking is not None:
                        if breaking.get('source_text') != bullet['text']:
                            raise ValueError('changed_bullet_requires_new_reviewed_linebreaks')
                        breaks[rid] = breaking
                    stable_ids[rid] = bullet['id']
        measurement = module.render_candidate({'resume': d.to_resume(doc)}, doc['language'], directory,
                                             {'bullet_labels': labels, 'bullet_breaks': breaks})
        return bind_render_evidence(doc, directory, measurement, stable_ids, labels)
    return render


def bind_render_evidence(doc, directory, measurement, stable_ids, labels):
    folder = Path(directory)
    pdf = Path(measurement.get('pdf_path') or folder / 'attempt-01/resume.pdf')
    if not pdf.is_absolute():
        pdf = folder / pdf
    if not pdf.resolve().is_relative_to(folder.resolve()):
        raise ValueError('final_presentation_pdf_outside_current_render')
    rows = read(folder / 'content.json')['paragraphs']
    tails = measure_tail_lines(pdf, folder / 'resume.docx', rows)
    for b in tails['bullets']:
        b['physical_row_id'] = b['id']
        b['id'] = stable_ids[b['id']]
    measurement['tail_line_review'] = tails
    # Preserve the producer's bold proof and its original PDF binding. Never
    # rewrite its PDF hash to make a stale proof look current.
    if isinstance(measurement.get('visual_bold'), dict):
        bold = measurement['visual_bold']
        try:
            evidence = Path(bold['evidence_path'])
            if not evidence.is_absolute(): evidence = folder / evidence
            if not evidence.resolve().is_relative_to(folder.resolve()):
                raise ValueError('bold_evidence_outside_current_render')
            receipt = read(evidence)
            if any(receipt.get(k) != bold.get(k) for k in ['status', 'method', 'pdf_sha256', 'checked_labels', 'labels',
                    'evidence_kind', 'visual_evidence_path', 'visual_evidence_sha256']):
                raise ValueError('bold_receipt_does_not_match_measured_proof')
            if receipt.get('pdf_sha256') != file_hash(pdf):
                raise ValueError('bold_receipt_bound_to_other_pdf')
            bold['artifact_verified'] = True
            bold['evidence_sha256'] = file_hash(evidence)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            bold['artifact_verified'] = False
            bold['evidence_error'] = str(exc)
        for label in bold.get('labels', []):
            if bold.get('evidence_kind', 'pixel_ab') == 'pixel_ab':
                try:
                    import pymupdf as fitz
                    images = {key: Path(label[key]) for key in ['regular_image_path', 'bold_image_path']}
                    for key, image in images.items():
                        if not image.is_absolute(): images[key] = folder / image
                        if not images[key].resolve().is_relative_to(folder.resolve()):
                            raise ValueError('pixel_comparison_image_outside_render')
                    pixels = {key: fitz.Pixmap(str(path)) for key,path in images.items()}
                    if any(p.n != 1 or p.alpha for p in pixels.values()):
                        raise ValueError('expected_exact_grayscale_pixel_comparison')
                    sums = {key: sum(255-x for x in p.samples) for key,p in pixels.items()}
                    label['pixel_artifact_verified'] = (sums['regular_image_path'] == label['regular_ink']
                                                       and sums['bold_image_path'] == label['bold_ink'])
                    label['pixel_images_sha256'] = {k:file_hash(v) for k,v in images.items()}
                except (OSError, ValueError, KeyError, TypeError):
                    label['pixel_artifact_verified'] = False
            if bold.get('evidence_kind') == 'embedded_bold_with_visual_inspection':
                try:
                    visual = Path(label.get('visual_evidence_path', bold.get('visual_evidence_path')))
                    if not visual.is_absolute(): visual = folder / visual
                    if not visual.resolve().is_relative_to(folder.resolve()):
                        raise ValueError('native_bold_visual_evidence_outside_render')
                    label['visual_artifact_verified'] = file_hash(visual) == label.get('visual_evidence_sha256', bold.get('visual_evidence_sha256'))
                except (OSError, ValueError, KeyError, TypeError):
                    label['visual_artifact_verified'] = False
            label['physical_row_id'] = label['id']
            label['id'] = stable_ids.get(label['id'], label['id'])
    return {'candidate_version': d.version(doc), 'measurement': measurement,
            'typography_fingerprint': measurement['typography_fingerprint'],
            'style_fingerprint': measurement['style_fingerprint'],
            'pdf': str(pdf), 'pdf_sha256': file_hash(pdf), 'docx': str(folder / 'resume.docx'),
            'presentation_requirements': {'tail_lines': True, 'visible_bold': True},
            'label_expected_ids': list(stable_ids.values()),
            'label_expected_text': {stable_ids[rid]: label['text'] + ('：' if doc['language']=='zh' else ':')
                                    for rid,label in labels.items()},
            'pending_items': [{'route': 'source_review', 'closed': False, 'blocks_current_draft': True,
                'reason': 'Visible lead-in labels add words outside the original fact manifest. Review their complete source support independently before delivery.'}] if labels else []}
