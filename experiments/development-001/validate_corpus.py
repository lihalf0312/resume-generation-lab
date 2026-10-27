"""Read-only structural and best-effort bilingual/date validation; no semantic scoring."""
import json,pathlib,re,hashlib,collections,sys
root=pathlib.Path(__file__).parent
errors=[]; warnings=[]; seen_identity=set();seen_family=set();sectors=collections.Counter();labels=collections.Counter();files=[]
def check(ok,msg):
 if not ok: errors.append(msg)
def nums(s):return collections.Counter(re.findall(r'\d+(?:\.\d+)?',s))
# Initial frozen corpus only; extensions have independent validators/manifests.
for d in sorted(d for b in ('batch-001','batch-002','batch-003') for d in (root/b).glob('case-*')):
 if not d.is_dir():continue
 p=json.loads((d/'profile.json').read_text());j=json.loads((d/'job.json').read_text());cid=d.name
 files += [d/'profile.json',d/'job.json']
 check(p['case_id']==j['case_id']==cid,f'{cid}: case ID mismatch')
 for field,seen in [('identity_id',seen_identity),('source_family',seen_family)]:
  check(p[field] not in seen,f'{cid}: duplicate {field}');seen.add(p[field])
 check(p['synthetic'] is True and j['synthetic'] is True,f'{cid}: synthetic label')
 check(p['source_family'] != p['creation_batch'],f'{cid}: lineage conflated with creation batch')
 check('synthetic' in j['vacancy_label'].lower(),f'{cid}: vacancy provenance')
 facts=p['facts'];reqs=j['requirements'];ids={f['id'] for f in facts};sectors[p['sector']]+=1
 check(8<=len(facts)<=12,f'{cid}: fact count');check(3<=len(reqs)<=5,f'{cid}: requirement count')
 check(len(ids)==len(facts),f'{cid}: duplicate fact ID')
 check(len({r['id'] for r in reqs})==len(reqs),f'{cid}: duplicate requirement ID')
 check(any(f['kind']=='education' for f in facts),f'{cid}: education missing')
 check(any(f['kind']=='employment' and re.search(r'20\d\d-\d\d',f['en']) for f in facts),f'{cid}: dated work missing')
 for f in facts:
  check(bool(f['en']) and bool(f['zh']) and bool(f['provenance']),f'{cid}/{f["id"]}: incomplete factual text')
  check(nums(f['en'])==nums(f['zh']),f'{cid}/{f["id"]}: bilingual numeric mismatch')
  dates=re.findall(r'\b(20\d\d)-(\d\d)\b',f['en'])
  check(all(1<=int(m)<=12 for y,m in dates),f'{cid}/{f["id"]}: invalid month')
  if f['kind']=='employment' and len(dates)==2:check(dates[0]<=dates[1],f'{cid}/{f["id"]}: reversed employment dates')
  # Degree/certificate wording is a manual-review flag, never silently repaired.
  if re.search(r'\b(bachelor|bsc|ba)\b',f['en'],re.I):check('学士' in f['zh'],f'{cid}/{f["id"]}: bachelor translation mismatch')
  if 'diploma' in f['en'].lower():check('文凭' in f['zh'] or '专科' in f['zh'],f'{cid}/{f["id"]}: diploma translation mismatch')
 for r in reqs:
  label=r['evidence_status'];labels[label]+=1;support=r['supporting_fact_ids']
  check(label in {'direct','transferable','missing'},f'{cid}/{r["id"]}: invalid truth label')
  check(set(support)<=ids,f'{cid}/{r["id"]}: unknown fact references')
  check((not support) if label=='missing' else bool(support),f'{cid}/{r["id"]}: support/label contradiction')
  check(nums(r['en'])==nums(r['zh']),f'{cid}/{r["id"]}: bilingual requirement numeric mismatch')
 check(any(r['evidence_status']=='direct' for r in reqs),f'{cid}: no direct evidence')
 check(any(r['evidence_status']=='missing' for r in reqs),f'{cid}: no genuine gap')
# Assert frozen source hashes, not mutable output artifacts.
manifest=root/'source_manifest.sha256.json'
if manifest.exists():
 m=json.loads(manifest.read_text())
 for rel,expected in m['files'].items():check(hashlib.sha256((root/rel).read_bytes()).hexdigest()==expected,f'{rel}: frozen hash mismatch')
 check(set(m['files'])=={str(p.relative_to(root)) for p in files},'Frozen manifest file coverage mismatch')
report=dict(cases=len(seen_identity),source_files=len(files),distinct_lineages=len(seen_family),sector_counts=dict(sectors),requirement_labels=dict(labels),errors=errors,warnings=warnings,limitations=['Semantic entailment, truthfulness of fictional provenance, and degree chronology require human/native-LLM review; numeric equality is not proof of translation equivalence.','No real-world qualification validity, employment verification, or causal inference is claimed.'])
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(errors))
