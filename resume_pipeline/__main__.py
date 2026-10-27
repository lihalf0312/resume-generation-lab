import argparse
import json
from .core import load_records, public_gate, run

p = argparse.ArgumentParser(description="Offline resume research, synthetic baseline only")
p.add_argument("command", choices=["validate", "run", "public-gate"])
p.add_argument("--data", default="fixtures/synthetic.jsonl")
p.add_argument("--out", default="private_runs/experiment-v2")
p.add_argument("--limit", type=int, default=10)
p.add_argument("--milestone", action="store_true")
a = p.parse_args()
r = load_records(a.data)
if a.command == "run":
    print(json.dumps(run(r, a.out, a.limit, a.milestone), indent=2))
elif a.command == "public-gate":
    public_gate(r)
    print("PASS: record gate only; repository requires separate release audit")
else:
    print("Validated %s records" % len(r))
