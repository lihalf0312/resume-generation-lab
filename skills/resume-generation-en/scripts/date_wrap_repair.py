"""Generic measured orphan-status relocation; no person/JD selection."""
import copy,re

def repair(rows,measurement):
 out=copy.deepcopy(rows);changes=[];metrics={p['id']:p for p in measurement['paragraphs']}
 for e in [p for p in out if p['kind']=='entry']:
  m=metrics[e['id']]
  if not (e.get('date','').endswith(' (awarded)') and m['physical_lines']>1 and m['last_line']=='(awarded)'):continue
  date=e['date'][:-len(' (awarded)')];end=re.split(r'\s*[–—]\s*',date)[-1].strip()
  if not re.fullmatch(r'[A-Za-z]+ \d{4}',end):continue
  bs=[p for p in out if p['kind']=='bullet' and (p.get('section'),p.get('item'))==(e.get('section'),e.get('item'))]
  if not bs:continue
  b=bs[0];old_e=copy.deepcopy(e);old_b=copy.deepcopy(b)
  e['date']=date
  b['text']='Degree awarded '+end+'. '+b['text']
  changes.append({'class':'automatic_structure','rule':'relocate_orphan_award_status_keep_exact_month_and_study_range','before':[old_e,old_b],'after':[copy.deepcopy(e),copy.deepcopy(b)],'semantic_quality_pass':None})
 return out,changes

