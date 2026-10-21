"""Regressões da auditoria de compatibilidade com o Makefile de IAED."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from run_tests import ROOT


class MakefileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="so-make-options-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "testes").mkdir(exist_ok=True)
        for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "advanced.py",
                     "vm_probe.c", "random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py",
                     "testes/exercicio1-test004.in", "testes/exercicio1-test004.out", "testes/exercicio1-test004.txt"):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, self.root / name)
        self.exe = self.root / "reference with spaces"
        self.exe.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport sys\n"
                            f"print(Path({str(ROOT / 'testes/exercicio1-test004.out')!r}).read_text(), end='')\n")
        self.exe.chmod(0o700)

    def make(self, *args, status=0, env=None):
        result = subprocess.run(["make", *args, f"EXE={self.exe}", "NO_PROMPT=1"], cwd=self.root,
                                capture_output=True, text=True, timeout=40, env=env)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def test_custom_logs_survive_show_export_rerun_and_clean(self):
        options = ["FAIL_LOG=logs/manual.log", "COMPARE_FAIL_LOG=logs/compare.log",
                   "EXERCISE2_FAIL_LOG=logs/two.log", "EXERCISE3_FAIL_LOG=logs/three.log"]
        for exercise in (2, 3):
            for suffix in (".in", ".out", ".txt"):
                shutil.copyfile(ROOT / ("testes/exercicio1-test004" + suffix),
                                self.root / "testes" / (f"exercicio{exercise}-test004" + suffix))
        original = self.exe.read_text()
        self.exe.write_text(original + "raise SystemExit(7)\n")
        for target in ("manual", "exercise2", "exercise3"):
            self.make(target, *options, status=2)
        self.make("compare", f"EXE2={self.exe}", *options, status=2)
        view = self.make("show-diff", *options).stdout
        for case in ("testes/exercicio1-test004", "testes/exercicio2-test004", "testes/exercicio3-test004"):
            self.assertIn(case + " FAILED", view)
        self.assertIn("comparação", view)
        self.make("export-zip", *options)
        with zipfile.ZipFile(next(self.root.glob("export_*.zip"))) as archive:
            for case in ("testes/exercicio1-test004", "testes/exercicio2-test004", "testes/exercicio3-test004"):
                self.assertIn("export/" + case + ".status.json", archive.namelist())
            self.assertIn("export/logs/three.log", archive.namelist())
        self.exe.write_text(original)
        result = self.make("rerun", *options)
        self.assertEqual(result.stdout.count(".in PASSED"), 3)
        self.assertFalse((self.root / "testes/suite.status.json").exists())
        for name in ("manual", "two", "three"):
            self.assertEqual((self.root / f"logs/{name}.log").read_text(), "")
        for exercise in (2, 3):
            self.assertEqual(json.loads((self.root / f"testes/exercicio{exercise}-suite.status.json").read_text())["passed"], 1)
        self.make("clean", *options)
        self.assertFalse(list((self.root / "logs").glob("*.log")))
        self.assertTrue((self.root / "testes/exercicio2-test004.in").is_file())
        self.assertTrue(next(self.root.glob("export_*.zip")).is_file())
        with tempfile.TemporaryDirectory(prefix="so-external-log-") as external:
            logfile = Path(external).resolve() / "outside.log"
            self.exe.write_text(original + "raise SystemExit(7)\n")
            self.make("manual", f"FAIL_LOG={logfile}", status=2)
            self.make("export", f"FAIL_LOG={logfile}")
            self.assertEqual((self.root / "export/outside.log").read_text(), "testes/exercicio1-test004.in\n")
            self.assertEqual(logfile.read_text(), "testes/exercicio1-test004.in\n")
            self.exe.write_text(original)
            self.make("rerun", f"FAIL_LOG={logfile}")
            self.assertEqual(logfile.read_text(), "")

    def test_exercises_runs_every_exercise_even_after_failure_and_exports(self):
        for exercise in (2, 3):
            for suffix in (".in", ".out", ".txt"):
                shutil.copyfile(ROOT / ("testes/exercicio1-test004" + suffix),
                                self.root / "testes" / (f"exercicio{exercise}-test004" + suffix))
        self.exe.write_text(self.exe.read_text() + "assert len(sys.argv)==7 and sys.argv[6]=='1'\n")
        result = self.make("exercises", "MAX_THREADS=1")
        self.assertEqual(result.stdout.count(".in PASSED"), 3)
        (self.root / "testes/exercicio1-test004.out").write_text("wrong expectation\n")
        result = self.make("exercises", "MAX_THREADS=1", status=2)
        self.assertIn("testes/exercicio1-test004.in FAILED", result.stdout)
        for exercise in (2, 3):
            self.assertIn(f"testes/exercicio{exercise}-test004.in PASSED", result.stdout)
            self.assertEqual((self.root / f"testes/exercicio{exercise}-tests_failed.log").read_text(), "")
        result = self.make("exercises", "export-zip", "MAX_THREADS=1")
        self.assertEqual(result.stdout.count(".in PASSED"), 2)
        with zipfile.ZipFile(next(self.root.glob("export_*.zip"))) as archive:
            self.assertIn("export/testes/exercicio1-test004.status.json", archive.namelist())

    def test_each_zip_combination_creates_one_archive(self):
        (self.root / "tests_failed.log").write_text("testes/exercicio1-test004.in\n")
        for goals in (("export-zip", "zip"), ("export", "zip"), ("zip", "export"), ("zip", "export-zip"),
                      ("zip",), ("export-zip",), ("export", "export-zip", "zip")):
            with self.subTest(goals=goals):
                for archive in self.root.glob("export_*.zip"):
                    archive.unlink()
                self.make(*goals)
                self.assertEqual(len(list(self.root.glob("export_*.zip"))), 1)
        (self.root / "tests_failed.log").unlink()
        self.exe.write_text(self.exe.read_text() + "raise SystemExit(7)\n")
        result = self.make("zip", "manual", "export")
        self.assertLess(result.stdout.index(".in FAILED"), result.stdout.index("Exportados"))
        self.assertTrue((self.root / "export/testes/exercicio1-test004.status.json").is_file())
        self.make("resolve-exe")
        for target in ("all", "python", "quick"):
            result = subprocess.run(["make", target, "export-zip", "EXE=/missing/cloudIST", "NO_PROMPT=1"],
                                    cwd=self.root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("não encontrado", result.stderr)
            self.assertIn("ZIP:", result.stdout)
            self.assertNotIn(".in PASSED", result.stdout)

    def test_selectors_stop_first_failure_caches_and_thread_argument(self):
        self.exe.write_text(self.exe.read_text() + "assert sys.argv[1:5] == ['1','2','3','4']\nassert sys.argv[6:] == ['3']\n")
        (self.root / "testes/exercicio1-test004.arg").write_text("1 2 3 4\n")
        for command in "drale":
            for filename in (f"pick_{command}.txt", f"comando {command}.txt"):
                selection = self.root / filename
                selection.write_text("# seleção\n\n testes/exercicio1-test004.in # comentário\n")
                result = self.make(command, "CMD_LIST_PREFIX=pick_", "MAX_THREADS=3", "EXE_CACHE_FILE=exe cache")
                self.assertIn("test testes/exercicio1-test004.in PASSED", result.stdout)
                selection.unlink()
        self.assertEqual((self.root / "exe cache").read_text().strip(), str(self.exe))
        for suffix in (".in", ".out"):
            shutil.copyfile(self.root / ("testes/exercicio1-test004" + suffix), self.root / ("testes/exercicio1-test005" + suffix))
        self.exe.write_text(f"#!{sys.executable}\nraise SystemExit(7)\n")
        for fail, executed in ((1, 1), (0, 2)):
            result = self.make("manual-tests", "TESTS=testes/exercicio1-test004.in testes/exercicio1-test005.in", f"FAIL={fail}", status=2)
            self.assertEqual(result.stdout.count(".in FAILED"), executed)
        for timeout in ("0", "nan", "-1"):
            result = self.make("manual", f"TIMEOUT={timeout}", status=2)
            self.assertIn("positivo e finito", result.stderr)

    def test_resolution_comparison_caches_and_statistics_options(self):
        project = self.root / "binary folder"
        project.mkdir()
        shutil.copy2(self.exe, project / "alternate")
        for name in ("EXE_CACHE_FILE", "EXE2_CACHE_FILE"):
            result = subprocess.run(["make", "resolve-exe" if name == "EXE_CACHE_FILE" else "resolve-exe2",
                                     f"{'EXE' if name == 'EXE_CACHE_FILE' else 'EXE2'}={project}",
                                     "EXE_NAME=alternate", f"{name}=custom {name}", f"PYTHON={sys.executable}"],
                                    cwd=self.root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((self.root / ("custom " + name)).read_text().strip(), str(project / "alternate"))
        self.make("compare", "COMPARE_TESTS=testes/exercicio1-test004.in", "TESTS=missing.in", f"EXE2={project / 'alternate'}",
                  "EXE2_CACHE_FILE=second cache")
        result = self.make("count", "STATS_FILE=reports/custom stats.txt", "TESTS=testes/exercicio1-test004.in", "CMD_LIST_PREFIX=pick_")
        self.assertEqual((self.root / "reports/custom stats.txt").read_text(), result.stdout)
        self.assertIn("Total tests:          1", result.stdout)
        (self.root / "testes/exercicio1-test004.arg").write_text("2 8 16 4\n")
        self.make("exercise1", "TESTS=testes/exercicio1-test004.in", f"PYTHON={sys.executable}")
        self.make("export", "AUTO_ZIP=1", "STATS_FILE=reports/custom stats.txt")
        with zipfile.ZipFile(next(self.root.glob("export_*.zip"))) as archive:
            self.assertIn("export/reports/custom stats.txt", archive.namelist())

    def test_help_covers_every_public_option_and_iaed_target(self):
        source = (ROOT / "Makefile").read_text().split("define PRETTY_DIFF_PY", 1)[0]
        options = set(re.findall(r"^([A-Z][A-Z0-9_]*) \?=", source, re.M))
        help_text = self.make("help").stdout
        report = (ROOT / "COMPATIBILITY.md").read_text()
        for option in options:
            self.assertRegex(help_text, rf"\b{option}\b", option)
            self.assertRegex(report, rf"\b{option}\b", option)
        iaed = (ROOT.parent / "IAED/Makefile").read_text()
        old_targets = set(re.search(r"^\.PHONY: (.*)$", iaed, re.M)[1].split())
        new_targets = set(re.search(r"^\.PHONY: (.*)$", source, re.M)[1].split())
        self.assertEqual(old_targets - new_targets, {"p", "f", "c"})
        self.assertTrue({"d", "r", "a", "l", "e"} <= new_targets)

    @unittest.skipUnless(shutil.which("cc"), "Requer compilador C")
    def test_source_build_preserves_make_dependencies_and_permissions(self):
        project = self.root / "project sources"
        project.mkdir()
        (project / "main.c").write_text('#include <stdio.h>\n#include "data.inc"\nint main(void) { puts(REPORT); }\n')
        (project / "data.inc").write_text("#define REPORT " + json.dumps((ROOT / "testes/exercicio1-test004.out").read_text()) + "\n")
        (project / "flags.mk").write_text("OBJECTS = main.o\n")
        (project / "prepare").write_text("#!/bin/sh\nexit 0\n")
        (project / "prepare").chmod(0o700)
        (project / "Makefile").write_text("include flags.mk\ncloudIST: $(OBJECTS)\n\t./prepare\n\t$(CC) $(CFLAGS) -o $@ $^\n")
        output = self.root / "custom output/asan"
        self.make("asan", f"ASAN_SRC={project / 'main.c'}", "SRC_CACHE_FILE=source cache",
                  f"ASAN_EXE={output}", "ASAN_MANUAL_TESTS=testes/exercicio1-test004.in", "TESTS=missing.in", "ASAN_FUZZ_CASES=0", "ASAN_COLLISIONS_COUNT=0")
        self.assertTrue(output.is_file())
        self.assertFalse((project / "main.o").exists())
        self.assertFalse((project / "cloudIST").exists())
        self.assertEqual((self.root / "source cache").read_text().strip(), str(project))

    @unittest.skipUnless(shutil.which("cc"), "Requer compilador C")
    def test_analysis_routes_custom_builds_reports_and_tool_errors(self):
        project, binaries = self.root / "sources", self.root / "bin"
        project.mkdir()
        binaries.mkdir()
        report = json.dumps((ROOT / "testes/exercicio1-test004.out").read_text())
        (project / "main.c").write_text('#include <stdio.h>\nint main(int argc, char **argv) {\n'
                                        '(void)argv; FILE *f=fopen("gmon.out","w"); if(f) fclose(f);\n'
                                        'if(argc==999) {\n puts("uncovered");\n}\n'
                                        f'fputs({report},stdout); return 0;\n}}\n')
        (project / "Makefile").write_text("cloudIST: main.o\n\t$(CC) $(CFLAGS) -o $@ $^\n")
        compiler = binaries / "compiler"
        compiler.write_text(f"#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n"
                            f"with Path({str(self.root / 'flags.log')!r}).open('a') as f: f.write(' '.join(sys.argv[1:])+'\\n')\n"
                            "os.execv('/usr/bin/cc',['cc',*[a for a in sys.argv[1:] if a!='-pg']])\n")
        compiler.chmod(0o700)
        # Controlos das ferramentas externas: validam integração; não medem leaks nem profiling real.
        scripts = {
            "valgrind": "import os,sys\nassert sys.argv[1:4]==['--quiet','--leak-check=full','--error-exitcode=42']\nos.execv(sys.argv[4],sys.argv[4:])\n",
            "lldb": "import sys\nfrom pathlib import Path\nassert sys.argv[1:5]==['-o','breakpoint set --name main','--',sys.argv[4]]\nassert (Path(sys.argv[-1])/'10.conf').read_text()=='L\\n'\n",
            "gprof": "import sys\nfrom pathlib import Path\nassert sys.argv[1]=='-b' and Path(sys.argv[2]).is_file() and Path(sys.argv[3]).is_file()\nprint('\\n'.join('profile row '+str(i) for i in range(30)))\n",
            "lizard": "import sys\nassert len(sys.argv)==2 and sys.argv[1].endswith('main.c')\nprint('complexity checked')\n",
        }
        for name, body in scripts.items():
            path = binaries / name
            path.write_text(f"#!{sys.executable}\n" + body)
            path.chmod(0o700)
        env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"])
        common = [f"PROJECT_DIR={project}", f"CC={compiler}", "TESTS=missing.in"]
        checks = [("valgrind", ["VALGRIND_TESTS=testes/exercicio1-test004.in"], "-O0"),
                  ("analyse", ["TEST=004"], "-O0"), ("profile", ["TEST=testes/exercicio1-test004"], "-pg")]
        if shutil.which("gcov"):
            checks.append(("coverage", ["COVERAGE_TESTS=testes/exercicio1-test004.in"], "--coverage"))
        for target, options, flag in checks:
            with self.subTest(target=target):
                output = self.root / f"custom binaries/{target}"
                (self.root / "flags.log").unlink(missing_ok=True)
                if target == "coverage":
                    (self.root / "coverage").mkdir()
                    (self.root / "coverage/previous-project.gcov").write_text("stale coverage\n")
                result = self.make(target, *common, *options, f"{target.upper()}_EXE={output}", env=env)
                self.assertTrue(output.is_file())
                self.assertIn(flag, (self.root / "flags.log").read_text())
                if target == "profile":
                    self.assertIn("profile row 24", result.stdout)
                    self.assertNotIn("profile row 25", result.stdout)
                    self.assertIn("profile row 29", (self.root / "profile_exercicio1-test004.txt").read_text())
                if target == "coverage":
                    self.assertIn('puts("uncovered")', result.stdout)
                    self.assertTrue(list((self.root / "coverage").glob("*.gcov")))
                    self.assertFalse((self.root / "coverage/previous-project.gcov").exists())
        self.assertIn("complexity checked", self.make("lizard", *common, env=env).stdout)
        (binaries / "valgrind").write_text("#!/bin/sh\nexit 42\n")
        result = self.make("valgrind", *common, "VALGRIND_TESTS=testes/exercicio1-test004.in", status=2, env=env)
        self.assertIn("LEAK/ERROR", result.stdout)
        self.assertIn("42", (self.root / "testes/exercicio1-test004.reason").read_text())
        self.make("analyse", *common, status=2, env=env)
        self.assertFalse((project / "cloudIST").exists())


if __name__ == "__main__":
    unittest.main()
