import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from advanced import check_assertion, directives
from run_tests import ROOT, END, STATUS, normalise, run_case, save_result, split_files


class AdvancedTests(unittest.TestCase):
    def test_150_new_cases_have_distinct_inputs_and_complete_expectations(self):
        groups = [[ROOT / "testes" / f"exercicio1-test{i:03d}.in" for i in range(30,80)],
                  sorted((ROOT/"testes").glob("exercicio2-test*.in")), sorted((ROOT/"testes").glob("exercicio3-test*.in"))]
        fingerprints = set()
        for exercise,cases in enumerate(groups,1):
            self.assertEqual(len(cases),50)
            for case in cases:
                with self.subTest(case=case):
                    text = case.read_text()
                    fingerprints.add(hashlib.sha256(text.encode()).digest())
                    self.assertTrue(case.with_suffix(".out").is_file())
                    self.assertEqual(len(case.with_suffix(".arg").read_text().split()),4)
                    self.assertTrue(case.with_suffix(".txt").read_text().startswith("Objetivo:"))
                    for name,body in split_files(text).items():
                        if name.endswith(".conf"):
                            self.assertLessEqual(sum(line.startswith("R ") for line in body.splitlines()),1)
                    if exercise > 1:
                        checks = directives(text,"ASSERT")
                        labels = [f"CHECK {i:02d} {check['kind']} OK" for i,check in enumerate(checks,1)]
                        labels += ["COPY " + line[8:].split(" -> ")[1] + " OK" for line in text.splitlines() if line.startswith("# COPY: ")]
                        self.assertEqual(normalise("\n".join(labels)),normalise(case.with_suffix(".out").read_text()))
        self.assertEqual(len(fingerprints),150)

    def test_checks_reject_serial_execution_wrong_limits_cpu_and_thread_bounds(self):
        events = [dict(event="start",tag="A",pid=2,time=0,ready=1),dict(event="end",tag="A",pid=2,time=1),
                  dict(event="start",tag="B",pid=3,time=2,ready=1),dict(event="end",tag="B",pid=3,time=3)]
        failures = [dict(kind="overlap",tags=["A","B"]),dict(kind="nonblocking",slow="A",next="B"),
                    dict(kind="cpu",tag="A",percent=25),dict(kind="limits",tag="MISSING",ram=1),
                    dict(kind="duration",min_ms=100,max_ms=1000),dict(kind="after",path="missing",min_ms=100)]
        for check in failures:
            with self.subTest(check=check),self.assertRaises(ValueError):
                check_assertion(check,events,[dict(tag="A",percent=100)],"",2,1,{})
        events[2]["time"] = .2
        check_assertion(dict(kind="overlap",tags=["A","B"]),events,[],"",.4,1,{})
        check_assertion(dict(kind="executions",counts={"A":1,"B":1}),events,[],"",.4,1,{})
        check_assertion(dict(kind="processes"),events,[],"",.4,1,{})
        with self.assertRaises(ValueError):
            check_assertion(dict(kind="cpu",tag="A",percent=25),events,[dict(tag="A",percent=float('nan'))],"",.4,1,{})

    @unittest.skipUnless(shutil.which("cc"),"Requer compilador C")
    def test_native_probes_execute_copy_observe_limits_and_cpu_spy(self):
        # Controlo de laboratório de uma VM; não gere recursos/reservas nem implementa o projeto.
        with tempfile.TemporaryDirectory() as temp:
            exe = Path(temp)/"controller"
            exe.write_text(f"#!{sys.executable}\n" + '''from pathlib import Path
import shutil,subprocess,sys,resource
lines=[line for p in sorted(Path(sys.argv[5]).glob('*.conf')) for line in p.read_text().splitlines()]
definition=next(line.split() for line in lines if line.startswith('D '))
reservation=next(line.split()[1] for line in lines if line.startswith('R '))
target=Path('/tmp/CloudIST')/reservation/(reservation+'_1')
shutil.copytree(definition[2],target)
def limits(): resource.setrlimit(resource.RLIMIT_FSIZE,(int(definition[5])<<30,)*2)
percent=float(definition[6])/float(sys.argv[4])*int(sys.argv[1])*100
subprocess.run(['cpulimit','-q','-f','-l',str(percent),'--',definition[3]],check=True,preexec_fn=limits)
''' + f"print({STATUS!r})\n" +
                "for _ in range(int(sys.argv[1])): print('Resources Used : 0.00 vCPUs | 0 GB RAM | 0 GB Disk')\n" +
                f"print('[ RESERVATIONS ] (0 total)')\nprint({END!r})\n")
            exe.chmod(0o700)
            numbers = [1,36,41] + ([50] if shutil.which("cpulimit") else [])
            for number in numbers:
                case = ROOT/"testes"/f"exercicio2-test{number:03d}.in"
                with self.subTest(case=case.name):
                    result = run_case(case,exe,6)
                    if result.get("skipped"):
                        self.assertIn("cpulimit",result["skipped"])
                        continue
                    self.assertFalse(result["reasons"],result)
                    self.assertEqual(len(result["events"]),2)
                    self.assertEqual(result["cpu_calls"][0]["tag"],result["events"][0]["tag"])
                    self.assertTrue(result["events"][0]["ready"])
            exe.write_text(f"#!{sys.executable}\nimport sys\nsys.stderr.write('VM execution not implemented in base version.\\n')\n")
            result = run_case(ROOT/"testes/exercicio2-test001.in",exe,1)
            self.assertTrue(result["reasons"])

    @unittest.skipUnless(shutil.which("cc"),"Requer compilador C")
    def test_exercise3_accepts_both_bases_and_vm_directory_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/'controller'
            body='''from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil,subprocess,sys,time
def job(path):
    lines=[line.split() for line in path.read_text().splitlines()]
    definitions=[w for w in lines if w and w[0]=='D']
    if not definitions:return
    d=definitions[0];r=next(w[1] for w in lines if w and w[0]=='R')
    delay=int(next(w[1] for w in lines if w and w[0]=='E'))/1000
    time.sleep(delay)
    target=Path('/tmp/CloudIST')/r/(r+'_1');shutil.copytree(d[2],target)
    return (subprocess.Popen([d[3]]),target) if RUN_VM else None
with ThreadPoolExecutor(max_workers=int(sys.argv[6])) as pool:
    results=list(pool.map(job,Path(sys.argv[5]).glob('*.conf')))
for result in results:
    if result:
        result[0].wait();shutil.rmtree(result[1])
'''
            for base in (1,2):
                exe.write_text(f'#!{sys.executable}\nRUN_VM={base==2}\n'+body);exe.chmod(0o700)
                result=run_case(ROOT/'testes/exercicio3-test011.in',exe,3)
                self.assertFalse(result['reasons'],result)

    def test_threads_check_accepts_parallel_and_rejects_serial_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "testes").mkdir(exist_ok=True)
            case = root/"test.in"
            checks = [dict(kind="after",path=f"/tmp/CloudIST/@RESERV{i:06d}@/@RESERV{i:06d}@_1",min_ms=580) for i in range(2)]
            checks.append(dict(kind="duration",min_ms=580,max_ms=1100))
            template = '# EXERCISE: 3\n# THREADS: 2\n' + ''.join('# ASSERT: '+json.dumps(check)+'\n' for check in checks)
            for i in range(2):
                r=f"@RESERV{i:06d}@"
                template+=f'# COPY: @INPUT@ -> {r}/{r}_1\n# FILE: {i}.conf\nR {r} T 1 1\nE 600\nA {r}\n'
            case.write_text(template)
            case.with_suffix('.arg').write_text('2 8 16 4\n')
            case.with_suffix('.out').write_text(''.join(f'CHECK {i:02d} {check["kind"]} OK\n' for i,check in enumerate(checks,1))+''.join(f'COPY @RESERV{i:06d}@/@RESERV{i:06d}@_1 OK\n' for i in range(2)))
            exe=root/'controller'
            code='''from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil,sys,time
def job(path):
    lines=path.read_text().splitlines()
    rs=[line.split()[1] for line in lines if line.startswith('R ')]
    if not rs:return
    time.sleep(.6)
    r=rs[0];shutil.copytree(Path.cwd()/'inputs',Path('/tmp/CloudIST')/r/(r+'_1'))
files=sorted(Path(sys.argv[5]).glob('*.conf'))
'''
            for parallel in (True,False):
                exe.write_text(f'#!{sys.executable}\n'+code+('with ThreadPoolExecutor(max_workers=int(sys.argv[6])) as pool: list(pool.map(job,files))\n' if parallel else 'for path in files: job(path)\n'))
                exe.chmod(0o700)
                result=run_case(case,exe,2)
                self.assertEqual(bool(result['reasons']),not parallel,result)

    def test_linux_only_case_is_reported_as_skipped_without_running(self):
        with patch('advanced.sys.platform','darwin'):
            result=run_case(ROOT/'testes/exercicio2-test031.in',Path('/usr/bin/false'),1)
        self.assertIn('skipped',result)
        self.assertIsNone(result['returncode'])
        self.assertFalse(result['reasons'])

    def test_broken_cpulimit_is_skipped_even_when_help_advertises_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            tool = Path(temp) / "cpulimit"
            tool.write_text('#!/bin/sh\nif [ "$1" = --help ]; then printf " -q, --quiet\\n -f, --foreground\\n"; exit 0; fi\necho "opendir: unavailable" >&2\nexit 2\n')
            tool.chmod(0o700)
            with patch.dict(os.environ, {"PATH": temp + os.pathsep + os.environ["PATH"]}):
                result = run_case(ROOT / 'testes/exercicio2-test050.in', Path('/usr/bin/false'), 1)
            self.assertIn('opendir: unavailable', result['skipped'])
            self.assertIsNone(result['returncode'])
            self.assertFalse(result['reasons'])

    def test_timeout_stops_descendants_before_removing_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root / "testes").mkdir(exist_ok=True)
            marker=root/'child-finished';started=root/'started'
            exe=root/'controller'
            exe.write_text('#!/bin/sh\n(sleep 1; printf done > '+shlex.quote(str(marker))+') &\nprintf ready > '+shlex.quote(str(started))+'\nwait\n')
            exe.chmod(0o700)
            case=root/'test.in'
            case.write_text('# EXERCISE: 3\n# THREADS: 1\n# FILE: a.conf\nE 1000\n')
            case.with_suffix('.arg').write_text('1 1 1 1\n');case.with_suffix('.out').write_text('')
            result=run_case(case,exe,.5)
            self.assertTrue(result['timed_out'],result)
            self.assertTrue(started.exists())
            time.sleep(.6)
            self.assertFalse(marker.exists())

    def test_make_export_and_rerun_support_flat_exercise_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root / "testes").mkdir(exist_ok=True)
            for name in ('Makefile','run_tests.py','tools.py','model.py','generated.py','advanced.py','vm_probe.c'):
                shutil.copyfile(ROOT/name,root/name)
            for suffix in ('.in','.out','.arg','.txt'):
                name='testes/exercicio3-test001'+suffix
                shutil.copyfile(ROOT/name,root/name)
            result=subprocess.run(['make','exercise3','export-zip','EXE=/usr/bin/false','NO_PROMPT=1'],cwd=root,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with zipfile.ZipFile(next(root.glob('export_*.zip'))) as archive:
                for name in ('testes/exercicio3-test001.status.json','testes/exercicio3-test001.in','advanced.py','vm_probe.c'):
                    self.assertIn('export/'+name,archive.namelist())
            result=subprocess.run(['make','rerun','EXE=/usr/bin/false','NO_PROMPT=1'],cwd=root,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            self.assertIn('testes/exercicio3-test001.in FAILED',result.stdout)


if __name__ == '__main__':
    unittest.main()
