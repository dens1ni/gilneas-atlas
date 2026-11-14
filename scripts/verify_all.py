import unittest,sys,json,contextlib,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
log=io.StringIO()
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
output=ROOT/'docs/revision-test-results.json'
summary={'run':result.testsRun,'failures':[{'test':str(test),'error':error} for test,error in result.failures],'errors':[{'test':str(test),'error':error} for test,error in result.errors],'skipped':len(result.skipped),'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)}
Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-all-tests.txt').write_text(log.getvalue())
output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
