"""Inert, strict JSON preferences. No config code or file paths are executed/read."""
import copy
import math
from pathlib import PurePath

LAYOUT_KEYS = {'page_size','target_pages','fill_normal_body_area','font_and_margins',
 'body_last_line_min_ratio','body_last_line_min_exclusive','body_last_line_preferred_ratio',
 'dates_bold','graduation_label_and_date_bold','separate_long_adjacent_entries_when_space_allows',
 'section_rules','numeric_and_latin_auto_spacing','short_single_line_info_terminal_period',
 'english_spaces','punctuation_compression'}
TOP_KEYS={'schema_version','output_languages','formats','template_paths','layout','personal_fields','versioning'}
PERSONAL_KEYS={'photo','political_information','english_default_omit_photo_and_political_information'}
VERSION_KEYS={'preserve_originals','overwrite_delivered_versions'}
LANGUAGES={'zh-CN','en'}


def validate_preferences(p, partial=False):
    if not isinstance(p,dict) or set(p)-TOP_KEYS or (not partial and set(p)!=TOP_KEYS):
        raise ValueError('unknown or missing preference keys')
    if 'schema_version' in p and (type(p['schema_version']) is not int or p['schema_version']!=1):
        raise ValueError('unsupported preference schema_version')
    for key in ('output_languages','formats'):
        if key not in p: continue
        value=p[key]
        if key=='output_languages' and value is None: continue
        allowed=LANGUAGES if key=='output_languages' else {'docx','pdf'}
        if not isinstance(value,list) or not value or not all(isinstance(x,str) and x in allowed for x in value) or len(value)!=len(set(value)):
            raise ValueError('invalid '+key)
    if 'template_paths' in p:
        values=p['template_paths']
        if not isinstance(values,dict) or set(values)-LANGUAGES:
            raise ValueError('invalid template_paths')
        for value in values.values():
            if value is not None and (not isinstance(value,str) or not value.lower().endswith('.docx') or any(c in value for c in ('\x00','\n','\r','://','$','`',';','|')) or '..' in PurePath(value.replace('\\','/')).parts):
                raise ValueError('template references must be inert DOCX paths; never opened by adapter')
    if 'layout' in p:
        v=p['layout']
        if not isinstance(v,dict) or set(v)-LAYOUT_KEYS or (not partial and set(v)!=LAYOUT_KEYS):
            raise ValueError('unknown or missing layout keys')
        bools={'fill_normal_body_area','body_last_line_min_exclusive','dates_bold','graduation_label_and_date_bold','separate_long_adjacent_entries_when_space_allows','short_single_line_info_terminal_period'}
        for k in bools & v.keys():
            if type(v[k]) is not bool:raise ValueError(k+' must be boolean')
        if 'page_size' in v and v['page_size'] not in ('A4','Letter','Legal','A3','A5'):raise ValueError('unsupported page size')
        if 'target_pages' in v and (type(v['target_pages']) is not int or not 1<=v['target_pages']<=100):raise ValueError('invalid target pages')
        if 'body_last_line_min_ratio' in v and (type(v['body_last_line_min_ratio']) not in (int,float) or not math.isfinite(v['body_last_line_min_ratio']) or not 0<=v['body_last_line_min_ratio']<1):raise ValueError('invalid final-line minimum')
        if 'body_last_line_preferred_ratio' in v:
            a=v['body_last_line_preferred_ratio']
            if not isinstance(a,list) or len(a)!=2 or not all(type(x) in (int,float) and math.isfinite(x) for x in a) or not 0<=a[0]<=a[1]<=1:raise ValueError('invalid preferred ratio')
        enums={'font_and_margins':{'follow_template_or_confirm_available_defaults'},'numeric_and_latin_auto_spacing':{'follow_template','enabled','disabled'},'english_spaces':{'single_ascii_space'},'punctuation_compression':{'when_visual_issue','doNotCompress','follow_template'}}
        for k,allowed in enums.items():
            if k in v and (not isinstance(v[k],str) or v[k] not in allowed):raise ValueError('unsupported '+k)
        if 'section_rules' in v:
            rules=v['section_rules']
            if not isinstance(rules,dict) or set(rules)-LANGUAGES or not all(isinstance(x,str) and x in ('top_and_bottom','bottom_only','none','follow_template') for x in rules.values()):raise ValueError('invalid section rules')
    if 'personal_fields' in p:
        v=p['personal_fields']
        if not isinstance(v,dict) or set(v)-PERSONAL_KEYS or (not partial and set(v)!=PERSONAL_KEYS):raise ValueError('invalid personal fields')
        for k,value in v.items():
            if k=='english_default_omit_photo_and_political_information':
                if type(value) is not bool:raise ValueError('invalid personal field flag')
            elif value not in ('confirm_with_user_and_template','confirm_with_user_and_purpose','omit'):
                raise ValueError('personal fields require confirmation or omission, never inferred')
    if 'versioning' in p:
        v=p['versioning']
        if not isinstance(v,dict) or set(v)-VERSION_KEYS or (not partial and set(v)!=VERSION_KEYS):raise ValueError('invalid versioning')
        for k,value in v.items():
            if type(value) is not bool or value != (k=='preserve_originals'):raise ValueError('historical overwrite forbidden')
    return p


def merge_preferences(defaults, template=None, confirmed=None, current=None):
    """Precedence: public defaults < measured template < confirmed user < current request."""
    validate_preferences(defaults)
    result=copy.deepcopy(defaults)
    def merge(target,patch):
        for k,v in patch.items():
            if isinstance(v,dict):merge(target.setdefault(k,{}),v)
            else:target[k]=copy.deepcopy(v)
    for layer in (template,confirmed,current):
        if layer is not None:
            validate_preferences(layer,partial=True);merge(result,layer)
    validate_preferences(result)
    layout=result['layout']
    if layout['body_last_line_preferred_ratio'][0]<layout['body_last_line_min_ratio']:
        raise ValueError('preferred range below strict minimum')
    return result
