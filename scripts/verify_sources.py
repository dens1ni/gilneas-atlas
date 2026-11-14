"""Verify every retrieved supporting excerpt against its saved page text."""
import json, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=Path('/Users/daniil_si/.hermes/skills/research/grounded-citations/scripts/sources.py')
spec=importlib.util.spec_from_file_location('citation_verifier',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
checks=json.loads((ROOT/'docs/source-verification.json').read_text())
failures=[]
for entry in checks:
 path=Path(entry['path']) if entry.get('path') else None
 if not path or not path.exists() or not module.quote_in_evidence(entry['quote'],path.read_text()):
  failures.append({'source':entry['source'],'evidence_path':str(path)})
result={'checks':len(checks),'matched':len(checks)-len(failures),'failures':failures}
(ROOT/'docs/source-verification-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
if failures:raise SystemExit(1)
