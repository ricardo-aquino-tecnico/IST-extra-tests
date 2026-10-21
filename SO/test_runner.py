import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from run_tests import END, ROOT, STATUS, check_copy, run_case, save_result, split_files
from tools import resolve_exe


class RunnerTests(unittest.TestCase):
    def test_resolve_accepts_project_folder_and_caches_absolute_file(self):
        with tempfile.TemporaryDirectory(prefix="so-resolve-") as temp:
            root = Path(temp)
            project = root / "project folder"
            project.mkdir()
            exe = project / "cloudIST"
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o700)
            cache = root / "cache"
            resolve_exe(str(project), cache, "cloudIST")
            self.assertEqual(cache.read_text().strip(), str(exe.resolve()))
            resolve_exe("", cache, "cloudIST")
            with self.assertRaises(ValueError):
                resolve_exe(str(root / "missing"), cache, "cloudIST")

    def test_make_uses_so_runner_and_checks_process(self):
        with tempfile.TemporaryDirectory(prefix="so-make-") as temp:
            root = Path(temp)
            for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "test004.in", "test004.out", "test004.txt"):
                shutil.copyfile(ROOT / name, root / name)
            exe = root / "fake cloudIST"
            for exitcode, stderr, expected_status in [(0, "", 0), (7, "", 2), (0, "problem", 2)]:
                exe.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport sys\n"
                               "assert len(sys.argv) == 6\n"
                               "assert (Path(sys.argv[5])/'10.conf').read_text() == 'L\\n'\n"
                               f"print(Path({str(ROOT / 'test004.out')!r}).read_text(), end='')\n"
                               f"sys.stderr.write({stderr!r})\nraise SystemExit({exitcode})\n")
                exe.chmod(0o700)
                result = subprocess.run(["make", "manual", "TESTS=test004.in", "NO_PROMPT=1", f"EXE={exe}"],
                                        cwd=root, capture_output=True, text=True, timeout=10)
                with self.subTest(exitcode=exitcode, stderr=stderr):
                    self.assertEqual(result.returncode, expected_status, result.stdout + result.stderr)
                    label = "\033[1;31mFAIL" if expected_status else "\033[1;32mPASS"
                    self.assertIn(label + " test004", result.stdout)
                    self.assertIn("\033[0m", result.stdout)
                    self.assertTrue((root / "test004.status.json").is_file())
                    metadata = json.loads((root / "test004.status.json").read_text())
                    self.assertEqual(metadata["returncode"], exitcode)
                    self.assertFalse(metadata["timed_out"])
            result = subprocess.run(["make", "count", "export-zip"], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(next(root.glob("export_*.zip"))) as archive:
                for name in ("test004.in", "test004.out", "test004.stdout", "test004.stderr", "test004.status.json",
                             "test_stats.txt", "Makefile", "run_tests.py", "tools.py"):
                    self.assertIn("export/" + name, archive.namelist())
            self.assertEqual((root / "tests_failed.log").read_text(), "test004.in\n")
            result = subprocess.run(["make", "rerun"], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_compare_includes_exit_code_and_stderr(self):
        with tempfile.TemporaryDirectory(prefix="so-compare-") as temp:
            root = Path(temp)
            for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "test004.in", "test004.out", "test004.txt"):
                shutil.copyfile(ROOT / name, root / name)
            reference, other = root / "reference", root / "other"
            code = (f"#!{sys.executable}\nfrom pathlib import Path\nimport sys\n"
                    f"print(Path({str(ROOT / 'test004.out')!r}).read_text(), end='')\n")
            reference.write_text(code)
            reference.chmod(0o700)
            for extra, expected in [("", 0), ("raise SystemExit(7)\n", 2), ("sys.stderr.write('problem')\n", 2)]:
                other.write_text(code + extra)
                other.chmod(0o700)
                result = subprocess.run(["make", "compare", "TESTS=test004.in", f"EXE={reference}", f"EXE2={other}"],
                                        cwd=root, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertEqual((root / "test004.cmpdiff").exists(), bool(expected))
            reference.write_text(code + "raise SystemExit(7)\n")
            other.write_text(code + "raise SystemExit(7)\n")
            result = subprocess.run(["make", "compare", "TESTS=test004.in", f"EXE={reference}", f"EXE2={other}"],
                                    cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Ambos os executáveis falharam", (root / "test004.cmpdiff").read_text())

    @unittest.skipUnless(shutil.which("cc"), "Requer compilador C")
    def test_asan_builds_multiple_sources_without_touching_project(self):
        with tempfile.TemporaryDirectory(prefix="so-asan-") as temp:
            root = Path(temp)
            suite = root / "suite"
            project = root / "source project"
            suite.mkdir()
            project.mkdir()
            for name in ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "test004.in", "test004.out", "test004.txt"):
                shutil.copyfile(ROOT / name, suite / name)
            (project / "main.c").write_text('#include <stdio.h>\nvoid report(void);\nint main(void) { report(); return 0; }\n')
            output = json.dumps((ROOT / "test004.out").read_text(), ensure_ascii=False)
            (project / "helper.c").write_text(f'#include <stdio.h>\nvoid report(void) {{ fputs({output}, stdout); }}\n')
            (project / "Makefile").write_text('cloudIST: main.o helper.o\n\t$(CC) $(CFLAGS) -o $@ $^\n')
            result = subprocess.run(["make", "asan", "TESTS=test004.in", "ASAN_FUZZ_CASES=0", "ASAN_COLLISIONS_COUNT=0", "EXE=/usr/bin/true", f"PROJECT_DIR={project}"],
                                    cwd=suite, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sorted(path.name for path in project.iterdir()), ["Makefile", "helper.c", "main.c"])
            self.assertEqual(json.loads((suite / "test004.status.json").read_text())["returncode"], 0)
            if shutil.which("gcov"):
                (project / "tests").mkdir()
                (project / "tests/unbuilt.c").write_text("#error This file must not be compiled\n")
                result = subprocess.run(["make", "coverage", "TESTS=test004.in", "EXE=/usr/bin/true", f"PROJECT_DIR={project}"],
                                        cwd=suite, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(list((suite / "coverage").glob("*.gcov")))
                self.assertNotIn("unbuilt", (suite / "coverage_report.txt").read_text())
            bin_dir = root / "bin"
            bin_dir.mkdir()
            valgrind = bin_dir / "valgrind"
            valgrind.write_text(f"#!{sys.executable}\nimport os,sys\n"
                                "assert sys.argv[1:4] == ['--quiet', '--leak-check=full', '--error-exitcode=42']\n"
                                "os.execv(sys.argv[4],sys.argv[4:])\n")
            valgrind.chmod(0o700)
            debugger = bin_dir / "lldb"
            debugger.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport sys\n"
                                "assert sys.argv[-5:-1] == ['2','8','16','4']\n"
                                "assert (Path(sys.argv[-1])/'10.conf').read_text() == 'L\\n'\n")
            debugger.chmod(0o700)
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
            for target, extra in (("valgrind", []), ("analyse", ["TEST=004"])):
                result = subprocess.run(["make", target, "TESTS=test004.in", "EXE=/usr/bin/true", f"PROJECT_DIR={project}", *extra],
                                        cwd=suite, capture_output=True, text=True, timeout=30, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((suite / ".build" / target / "cloudIST").is_file())

    def test_debugger_receives_real_arguments_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "test.in"
            case.write_text("# FILE: 10.conf\nL\n")
            case.with_suffix(".out").write_text("")
            seen = []

            def debugger(command, **options):
                self.assertEqual(command[0], "lldb")
                self.assertEqual(command[-5:-1], ["2", "8", "16", "4"])
                self.assertEqual((Path(command[-1]) / "10.conf").read_text(), "L\n")
                seen.append(Path(options["cwd"]))

            with patch("run_tests.subprocess.run", side_effect=debugger):
                self.assertIsNone(run_case(case, Path("/usr/bin/true"), 3, debugger="lldb"))
            self.assertFalse(seen[0].exists())

    def test_catalogue(self):
        cases = sorted(ROOT.glob("test*.in"))
        self.assertGreaterEqual(len(cases), 20)
        for case in cases:
            with self.subTest(case=case.stem):
                self.assertTrue(case.with_suffix(".out").is_file())
                self.assertTrue(case.with_suffix(".txt").read_text().startswith("Objetivo:"))
                for name, content in split_files(case.read_text()).items():
                    if name.endswith(".conf"):
                        self.assertLessEqual(sum(line.startswith("R ") for line in content.splitlines()), 1)

    def test_split_files_keeps_comments_and_eof(self):
        self.assertEqual(split_files(""), {})
        self.assertEqual(split_files("# FILE: b.conf\n# comment\n\nL\n# FILE: a.conf\nE 0"),
                         {"b.conf": "# comment\n\nL\n", "a.conf": "E 0"})
        for name in ("../x.conf", "/tmp/x.conf", "a.conf\n# FILE: a.conf"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                split_files(f"# FILE: {name}\n")

    def test_copy_checks_bytes_directories_and_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, dest = root / "source", root / "dest"
            source.mkdir()
            (source / "empty").mkdir()
            (source / "data").write_bytes(bytes(range(256)) * 81)
            shutil.copytree(source, dest)
            check_copy(source, dest)
            (dest / "data").write_bytes(b"truncated")
            with self.assertRaisesRegex(ValueError, "conteúdo"):
                check_copy(source, dest)
            (dest / "data").unlink()
            os.link(source / "data", dest / "data")
            with self.assertRaisesRegex(ValueError, "ligado"):
                check_copy(source, dest)
            (dest / "data").unlink()
            (dest / "data").symlink_to(source / "data")
            with self.assertRaisesRegex(ValueError, "simbólico"):
                check_copy(source, dest)
            (dest / "data").unlink()
            shutil.copyfile(source / "data", dest / "data")
            (dest / "extra").mkdir()
            with self.assertRaisesRegex(ValueError, "árvore"):
                check_copy(source, dest)

    def test_process_exit_timeout_and_missing_listing_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "test.in"
            case.write_text("# FILE: 10.conf\nL\n")
            case.with_suffix(".out").write_text(STATUS + "\n" + END + "\n")
            exe = root / "fake app"
            for code, reason, timeout in [("raise SystemExit(7)", "Código de saída: 7", 3),
                                          ("import time; time.sleep(2)", "Timeout", 0.1),
                                          ("pass", "Output diferente", 3),
                                          (f"print({STATUS!r})", "Listagem L incompleta", 3)]:
                exe.write_text(f"#!{sys.executable}\n{code}\n")
                exe.chmod(0o700)
                with self.subTest(code=code):
                    result = run_case(case, exe, timeout)
                    save_result(case, result)
                    self.assertIn(reason, "\n".join(result["reasons"]))
                    self.assertEqual(result["timed_out"], reason == "Timeout")
                    self.assertTrue(case.with_suffix(".diff").is_file())
            exe.write_text(f"#!{sys.executable}\nimport sys\nprint({STATUS!r})\nprint({END!r})\n"
                           "print('VM execution not implemented in base version.', file=sys.stderr)\n")
            result = run_case(case, exe, 3)
            save_result(case, result)
            self.assertEqual(result["reasons"], [])
            self.assertFalse(case.with_suffix(".diff").exists())
            case.with_suffix(".gmon").write_bytes(b"stale profile")
            result = run_case(case, exe, 3, profile=True)
            self.assertTrue(any("gmon.out ausente" in reason for reason in result["reasons"]))
            self.assertFalse(case.with_suffix(".gmon").exists())

    def test_listing_accepts_equivalent_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "test.in"
            case.write_text("# FILE: 10.conf\nD SMALL inputs app 1 1 1\nL\n")
            case.with_suffix(".out").write_text(STATUS + "\n├─ Executable : @EXE@\n└─ Input Dir : @INPUT@\n" + END + "\n")
            exe = root / "fake"
            for folder, should_fail in (("inputs", False), ("wrong-inputs", True)):
                exe.write_text(f"#!{sys.executable}\nprint({STATUS!r})\nprint('├─ Executable : app')\n"
                               f"print('└─ Input Dir : {folder}')\nprint({END!r})\n")
                exe.chmod(0o700)
                self.assertEqual(bool(run_case(case, exe, 3)["reasons"]), should_fail)

    def test_copy_end_to_end_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "test.in"
            case.write_text("# FILE: 10.conf\nD TEST @INPUT@ @EXE@ 1 1 1\n"
                            "R @RESERVA@ TEST 1 1\nA @RESERVA@\n"
                            "# COPY: @INPUT@ -> @RESERVA@/@RESERVA@_1\n")
            case.with_suffix(".out").write_text("COPY @RESERVA@/@RESERVA@_1 OK\n")
            exe = root / "fake app"
            code = (
                "from pathlib import Path\nimport shutil, sys\n"
                "lines=(Path(sys.argv[5])/'10.conf').read_text().splitlines()\n"
                "source=Path(next(x for x in lines if x.startswith('D ')).split()[2])\n"
                "rid=next(x for x in lines if x.startswith('R ')).split()[1]\n"
                "dest=Path('/tmp/CloudIST')/rid/(rid+'_1')\n"
                "shutil.copytree(source,dest)\n"
                f"Path({str(root / 'destination')!r}).write_text(str(dest.parent))\n"
            )
            exe.write_text(f"#!{sys.executable}\n{code}")
            exe.chmod(0o700)
            result = run_case(case, exe, 3)
            save_result(case, result)
            self.assertEqual(result["reasons"], [])
            dest = Path((root / "destination").read_text())
            self.assertFalse(dest.exists())
            self.assertFalse(dest.with_name("." + dest.name).exists())
            exe.write_text(f"#!{sys.executable}\n{code}(dest/'text.txt').write_text('broken')\n")
            self.assertIn("conteúdo", "\n".join(run_case(case, exe, 3)["reasons"]))
            self.assertFalse(Path((root / "destination").read_text()).exists())


if __name__ == "__main__":
    unittest.main()
