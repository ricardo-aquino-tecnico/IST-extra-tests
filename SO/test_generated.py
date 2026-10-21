import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from generated import collision_case, fuzz_case, scale_case, stress_case
from model import Model
from run_tests import ROOT, normalise, run_case, split_files


class GeneratedTests(unittest.TestCase):
    def test_quick_completes_all_five_suites_with_a_model_test_double(self):
        with tempfile.TemporaryDirectory(prefix="so-quick-") as temp:
            root = Path(temp)
            for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py",
                         "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "test004.in", "test004.out", "test004.txt"):
                shutil.copyfile(ROOT / name, root / name)
            exe = root / "model test double"
            exe.write_text(f"#!{sys.executable}\n" + '''from pathlib import Path
import shutil,sys
sys.path.insert(0, str(Path(__file__).parent))
from model import Model
model=Model(*map(int,sys.argv[1:5]))
try:
    for path in sorted(Path(sys.argv[5]).iterdir()):
        if not path.is_file() or path.suffix != '.conf': continue
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'): continue
            words=line.split()
            if words[0]=='D' and len(words)==7:
                model.define(words[1],int(words[4]),int(words[5]),float(words[6]),words[2],words[3])
            elif words[0]=='R' and len(words)>=5 and len(words[2:])%3==0:
                model.reserve(words[1],[(words[i],int(words[i+1]),int(words[i+2])) for i in range(2,len(words),3)])
            elif words[0]=='L' and len(words)==1:
                print(model.listing(),end='')
            elif words[0]=='E' and len(words)==2 and int(words[1])==0:
                pass
            elif words[0]=='A' and len(words)==2:
                for rid,vid,name,_ in model.vms():
                    if rid!=words[1]: continue
                    target=Path('/tmp/CloudIST')/rid/vid
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copytree(model.types[name][3],target)
                del model.reservations[words[1]]
            else: raise ValueError('invalid command')
except (ValueError,KeyError,IndexError):
    raise SystemExit(1)
''')
            exe.chmod(0o700)
            result = subprocess.run(["make", "quick", f"EXE={exe}", "TESTS=test004.in", "STRESS_SEED=42", "FUZZ_SEED=42"],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((root / "test_summary.status.json").read_text())
            self.assertEqual(len(summary), 5)
            self.assertTrue(all(part["returncode"] == 0 for part in summary))
            self.assertEqual(summary[1]["passed"], 8)
            self.assertEqual(summary[3]["passed"], 12)
            original = exe.read_text()
            exe.write_text(f"#!{sys.executable}\nraise SystemExit(7)\n")
            result = subprocess.run(["make", "stress", f"EXE={exe}", "STRESS_RUNS=1", "STRESS_STEPS=4", "STRESS_SEED=42"],
                                    cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            exe.write_text(original)
            result = subprocess.run(["make", "rerun", f"EXE={exe}"], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "stress-failures/tests_failed.log").read_text(), "")
            status = json.loads((root / "stress-failures/suite.status.json").read_text())
            self.assertEqual(status["failed"], 0)
            self.assertTrue(status["rerun"])

    def test_model_matches_fixed_manual_expectations(self):
        model = Model(2, 8, 16, 4)
        self.assertEqual(model.listing(), normalise((ROOT / "test004.out").read_text()))
        model.define("SMALL")
        self.assertEqual(model.listing(), normalise((ROOT / "test005.out").read_text()))
        model.reserve("@RESERVA@", [("SMALL", 1, 1)])
        self.assertEqual(model.listing(), normalise((ROOT / "test010.out").read_text()))
        before = model.listing()
        with self.assertRaises(ValueError):
            model.reserve("@RESERVB@", [("SMALL", 1, 2), ("SMALL", 100, 1)])
        self.assertEqual(model.listing(), before)

    def test_generators_are_reproducible_and_keep_one_reservation_per_file(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "case"
            first, second = stress_case(123, 120), stress_case(123, 120)
            self.assertEqual(first.files, second.files)
            self.assertEqual(first.expected, second.expected)
            self.assertNotEqual(first.files, stress_case(124, 120).files)
            for case in (first, scale_case(128, 256), collision_case(128, 1000000)):
                case.write(base, "self-check")
                files = split_files(base.with_suffix(".in").read_text())
                for content in files.values():
                    self.assertLessEqual(sum(line.startswith("R ") for line in content.splitlines()), 1)
                for server in range(1, 5):
                    self.assertTrue(all(used <= total for used, total in zip(case.model.used(server), case.model.args[1:])))
            names = list(collision_case(128, 1000000).model.types)
            self.assertEqual(len(set(names)), 128)
            self.assertEqual({len(name) for name in names}, {39})

    def test_fuzz_policy_accepts_rejection_but_rejects_crashes_and_sanitizers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "case"
            fuzz_case(42, 10).write(base, "fuzz test")
            exe = root / "fake"
            for code, should_fail in [("import sys; sys.stderr.write('invalid command'); sys.exit(1)", False),
                                      ("raise SystemExit(2)", True),
                                      ("import os,signal; os.kill(os.getpid(), signal.SIGTERM)", True),
                                      ("import sys; sys.stderr.write('runtime error: invalid access')", True)]:
                exe.write_text(f"#!{sys.executable}\n{code}\n")
                exe.chmod(0o700)
                result = run_case(base.with_suffix(".in"), exe, 3)
                self.assertEqual(bool(result["reasons"]), should_fail, result)

    def test_all_runs_every_suite_and_exports_generated_failures(self):
        with tempfile.TemporaryDirectory(prefix="so-all-") as temp:
            root = Path(temp)
            for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py",
                         "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "test004.in", "test004.out", "test004.txt"):
                shutil.copyfile(ROOT / name, root / name)
            args = ["EXE=/usr/bin/false", "TESTS=test004.in", "STRESS_RUNS=1", "STRESS_STEPS=4", "STRESS_SEED=42",
                    "SCALE_TYPES=2", "SCALE_FILES=2", "FUZZ_CASES=1", "FUZZ_LINES=4", "FUZZ_SEED=42", "COLLISIONS_COUNT=2"]
            result = subprocess.run(["make", "all", "count", "export-zip", *args], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((root / "test_summary.status.json").read_text())
            self.assertEqual(len(summary), 5)
            self.assertEqual(sum(bool(part["returncode"]) for part in summary), 4)
            self.assertTrue(summary[0]["failed"])
            with zipfile.ZipFile(next(root.glob("export_*.zip"))) as archive:
                names = archive.namelist()
                for folder in ("stress-failures", "scale-failures", "collisions-failures"):
                    self.assertTrue(any(name.startswith("export/"+folder+"/") and name.endswith(".status.json") for name in names), folder)
                self.assertIn("export/generated.py", names)
                self.assertIn("export/model.py", names)
                self.assertIn("export/test_summary.txt", names)
            result = subprocess.run(["make", "rerun", "EXE=/usr/bin/false"], cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout.count("FAIL seed_"), 3, result.stdout)
            result = subprocess.run(["make", "show-diff"], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("stress-failures", result.stdout)


if __name__ == "__main__":
    unittest.main()
