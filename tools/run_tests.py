"""Run actual pytest checks and generate a small static HTML test report."""
import hashlib
import html
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import uuid
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    """Run the current test suite; report failures/skips without claiming real-fault validation."""
    private=ROOT/'results/test_run';private.mkdir(parents=True,exist_ok=True)
    xml=private/'junit.xml'
    temporary=(private/('tmp_'+uuid.uuid4().hex[:10])).resolve()
    temporary.relative_to(ROOT.resolve())
    process=subprocess.run([sys.executable,'-m','pytest','--basetemp',str(temporary),'--junitxml',str(xml)],cwd=ROOT,
                           text=True,capture_output=True,encoding='utf-8',errors='replace')
    print(process.stdout,flush=True)
    if process.stderr:print(process.stderr,file=sys.stderr)
    (private/'pytest.log').write_text(process.stdout+'\n'+process.stderr,encoding='utf-8')
    if not xml.exists():raise RuntimeError('pytest did not generate its actual result file.')
    tree=ET.parse(xml)
    cases=tree.findall('.//testcase')
    rows=[];counts={'passed':0,'skipped':0,'failed':0}
    for case in cases:
        state='failed' if case.find('failure') is not None or case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        counts[state]+=1
        rows.append('<tr><td>'+html.escape(case.get('classname',''))+'</td><td>'+html.escape(case.get('name',''))+'</td><td>'+state+'</td></tr>')
    files=sorted(p for folder in ['src','tests','tools','notebooks','config'] for p in (ROOT/folder).rglob('*')
                 if p.is_file() and p.suffix in ['.py','.ipynb','.json'] and p!=ROOT/'config/local.json')
    digests={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result={'executed_utc':datetime.now(timezone.utc).isoformat(),'counts':counts,
            'exit_code':process.returncode,'source_sha256':digests,
            'note':'Integration checks skip if private local runs are unavailable. No measurements are included in this report.'}
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    (out/'test_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    body='<!doctype html><html lang="en"><meta charset="utf-8"><title>CO2 project test report</title><style>body{font:16px/1.5 system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#18232c}h1,h2{color:#000}table{border-collapse:collapse;width:100%}td,th{border:1px solid #d9d9d9;padding:8px;text-align:left}th{background:#e8eef2}code{overflow-wrap:anywhere}</style><body><h1>CO2 project test report</h1>'
    body+='<p>Actual pytest execution: '+html.escape(result['executed_utc'])+'</p><p>'+html.escape(str(counts))+'</p>'
    body+='<p>Unit tests use manufactured inputs. Integration checks compare completed experiments with aggregate references. This verifies implementation consistency, not effectiveness on real faults. Private execution outputs and full test logs remain under results/.</p>'
    body+='<table><thead><tr><th>Module</th><th>Test case</th><th>Result</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></body></html>'
    (out/'test_report.html').write_text(body,encoding='utf-8')
    print(json.dumps(counts))
    raise SystemExit(process.returncode)


if __name__=='__main__':main()
