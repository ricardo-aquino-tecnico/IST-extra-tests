#!/usr/bin/env python3
"""Ferramentas do Makefile; todas as execuções de testes usam run_tests.py."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from run_tests import ROOT, select_cases
from generated import FAIL_DIRS


SUITE_DIRS = dict(zip(("stress", "scale", "fuzz-parse", "scale-collisions"), FAIL_DIRS))


def resolve_exe(value, cache, name, search=True):
    candidates = [value] if value else ([cache.read_text().strip()] if cache.is_file() else []) + (["../" + name, "../../" + name] if search else [])
    while True:
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if path.is_dir():
                path /= name
            if path.is_file() and os.access(path, os.X_OK):
                cache.write_text(str(path.resolve()) + "\n")
                return
        if value or not sys.stdin.isatty():
            raise ValueError(f"Executável {name} não encontrado. Define EXE=/caminho/{name} (ou EXE2 para compare).")
        candidates = [input(f"Indica o executável {name} ou a pasta do projeto: ").strip()]


def count_tests(names, stats):
    cases = [ROOT / name for name in names]
    lines = [f"{len(cases)} testes do exercício 1", "Testes por comando:"]
    for command in "DRALE":
        amount = sum(bool(re.search(rf"^{command}(?: |$)", case.read_text(), re.M)) for case in cases)
        lines.append(f"  {command}: {amount}")
    lines += [f"Com .arg: {sum(case.with_suffix('.arg').is_file() for case in cases)}",
              f"Com descrição: {sum(case.with_suffix('.txt').is_file() for case in cases)}"]
    lines.append("Scripts Python:")
    for name in ("random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py"):
        lines.append(f"  {name}: {'presente' if (ROOT / name).is_file() else 'ausente'}")
    for suite, directory in SUITE_DIRS.items():
        status = ROOT / directory / "suite.status.json"
        if status.is_file():
            meta = json.loads(status.read_text())
            lines.append(f"  {suite}: {meta['passed']} passaram, {meta['failed']} falharam, {meta['planned']} previstos")
    text = "\n".join(lines) + "\n"
    stats.write_text(text)
    print(text, end="")


def export_failures(args):
    destination = ROOT / "export"
    names = set()
    logs = [args.fail_log, args.compare_log, *(str(Path(directory) / "tests_failed.log") for directory in FAIL_DIRS)]
    for logfile in logs:
        path = ROOT / logfile
        if path.is_file():
            names.update(str(path.parent.relative_to(ROOT) / name) if Path(name).parent == Path(".") else name
                         for name in path.read_text().splitlines() if name)
    if not names and not (ROOT / args.stats).is_file():
        print("Não há testes falhados para exportar.")
        return
    cases = select_cases(sorted(names))
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for case in cases:
        for path in case.parent.glob(case.stem + ".*"):
            if path.is_file():
                target = destination / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    helpers = ("Makefile", "run_tests.py", "tools.py", "model.py", "generated.py", "random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py", "README.md")
    for name in (*helpers, *logs, args.stats, "test_summary.txt", *(str(Path(d) / "suite.status.json") for d in FAIL_DIRS)):
        path = ROOT / name
        if path.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    print(f"Exportados {len(names)} testes para {destination}")
    make_zip = args.zip or os.environ.get("AUTO_ZIP") == "1"
    interactive = sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1"
    if not make_zip and interactive:
        make_zip = input("Criar ZIP dos testes exportados? [y/N] ").strip().lower() == "y"
    if make_zip:
        filename = ROOT / ("export_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f"))
        archive = shutil.make_archive(str(filename), "zip", ROOT, "export")
        print(f"ZIP: {archive}")
        if interactive and input("Apagar a pasta export/ e preservar o ZIP? [y/N] ").strip().lower() == "y":
            shutil.rmtree(destination)


def run_suites(parts, exe, tests, env=None, overrides=None):
    results = []
    for part in parts:
        status = ROOT / SUITE_DIRS[part] / "suite.status.json" if part in SUITE_DIRS else ROOT / "test_run.status.json"
        status.unlink(missing_ok=True)
        command = ["make", "-s", part, f"EXE={exe}", "EXE_CACHE_FILE=.resolved_exe_suite", "NO_PROMPT=1", "EXPORTING="]
        if tests:
            command.append("TESTS=" + " ".join(tests))
        command += [f"{key}={value}" for key, value in (overrides or {}).items()]
        start = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, env=env)
        metadata = json.loads(status.read_text()) if status.is_file() else {}
        results.append({**metadata, "suite": part, "returncode": result.returncode, "elapsed": time.monotonic()-start})
    lines = ["", "Resumo das suites:", f"{'Suite':<20} {'Estado':<8} {'Passaram/executados':<22} Duração"]
    for result in results:
        counts = f"{result['passed']}/{result['passed']+result['failed']}" if "passed" in result else "—"
        lines.append(f"{result['suite']:<20} {'FAIL' if result['returncode'] else 'PASS':<8} {counts:<22} {result['elapsed']:.3f}s")
    failed = sum(bool(result["returncode"]) for result in results)
    lines.append(f"{len(results)-failed}/{len(results)} suites passaram; {failed} falharam.")
    summary = "\n".join(lines) + "\n"
    print(summary, end="", flush=True)
    (ROOT / "test_summary.txt").write_text(summary)
    (ROOT / "test_summary.status.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    if failed and sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1" and not os.environ.get("EXPORTING"):
        if input("Mostrar diferenças dos testes falhados? [Y/n] ").strip().lower() != "n":
            subprocess.run(["make", "show-diff"], cwd=ROOT)
    return bool(failed)


def rerun(args):
    failed = False
    found = False
    for logfile in (Path(args.fail_log), *(Path(d) / "tests_failed.log" for d in FAIL_DIRS)):
        path = ROOT / logfile
        names = path.read_text().splitlines() if path.is_file() else []
        if not names:
            continue
        found = True
        names = [str(logfile.parent / name) if Path(name).parent == Path(".") else name for name in names]
        command = [sys.executable, str(ROOT / "run_tests.py"), "--exe", args.exe, "--timeout", str(args.timeout), "--fail-log", str(logfile)]
        if args.fail:
            command.append("--fail")
        result = subprocess.run([*command, *names], cwd=ROOT)
        summary = ROOT / "test_run.status.json"
        if logfile.parent != Path(".") and summary.is_file():
            status = ROOT / logfile.parent / "suite.status.json"
            metadata = json.loads(status.read_text()) if status.is_file() else {}
            metadata.update(json.loads(summary.read_text()))
            metadata["rerun"] = True
            status.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        failed |= bool(result.returncode)
        if args.fail and failed:
            break
    if not found:
        print("Não há testes falhados para repetir.")
    return failed


def resolve_project(value, exe, cache):
    project = Path(value).expanduser().resolve() if value else Path(cache.read_text().strip()) if cache.is_file() else exe.parent
    if project.is_file():
        project = project.parent
    if not (project / "Makefile").is_file() or not list(project.rglob("*.c")):
        raise ValueError(f"Fontes/Makefile não encontrados em {project}. Define PROJECT_DIR=/caminho/do/projeto")
    cache.write_text(str(project.resolve()) + "\n")
    return project


def run_tool(args):
    exe = Path(args.exe).expanduser().resolve()
    project = resolve_project(args.project, exe, ROOT / args.src_cache)
    tests = args.tests
    if args.mode in ("analyse", "profile"):
        if not args.test:
            raise ValueError(f"Uso: make {args.mode} TEST=007")
        test = args.test
        if test.isdigit():
            test = f"test{int(test):03d}.in"
        tests = [str(Path(test).with_suffix(".in"))]
    command = [sys.executable, str(ROOT / "run_tests.py"), "--timeout", str(args.timeout), "--fail-log", args.fail_log]
    if args.fail:
        command.append("--fail")
    debugger = None
    if args.mode == "analyse":
        debugger = shutil.which("lldb") or shutil.which("gdb")
        if not debugger:
            raise ValueError("LLDB/GDB não encontrado.")
    if args.mode == "valgrind":
        if not shutil.which("valgrind"):
            raise ValueError("Valgrind não encontrado. Usa um ambiente com Valgrind instalado.")
    sources = sorted(p for p in project.rglob("*.c") if not any(part.startswith(".") for part in p.relative_to(project).parts))
    if not sources:
        raise ValueError(f"Não há fontes .c em {project}. Define PROJECT_DIR=/caminho/do/projeto")
    if args.mode == "lizard":
        if not shutil.which("lizard"):
            raise ValueError("Lizard não encontrado.")
        return subprocess.run(["lizard", *map(str, sources)]).returncode
    if not (project / "Makefile").is_file():
        raise ValueError(f"Makefile não encontrado em {project}")
    tool = "gprof" if args.mode == "profile" else "gcov" if args.mode == "coverage" else None
    if tool and not shutil.which(tool):
        raise ValueError(f"{tool} não encontrado.")
    with tempfile.TemporaryDirectory(prefix=f"so-{args.mode}-") as temp:
        build = Path(temp)
        for source in project.rglob("*"):
            relative = source.relative_to(project)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if source.is_file() and (source.suffix in (".c", ".h") or source.name == "Makefile"):
                target = build / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        flags = "-std=c17 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -g "
        flags += {"asan": "-O1 -fsanitize=address,undefined -fno-omit-frame-pointer",
                  "coverage": "-O0 --coverage", "profile": "-O2 -pg", "analyse": "-O0", "valgrind": "-O0"}[args.mode]
        subprocess.run(["make", "-C", str(build), "CC=" + os.environ.get("CC", "cc"), "CFLAGS=" + flags], check=True)
        binary = build / "cloudIST"
        if not binary.is_file():
            raise ValueError("A compilação não produziu cloudIST.")
        if args.output:
            output = Path(args.output).expanduser().resolve()
            if output in (exe, project / "cloudIST"):
                raise ValueError("O executável de análise não pode substituir o executável original do projeto")
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(binary, output)
            output.chmod(0o755)
            binary = output
        env = dict(os.environ)
        if args.mode == "asan":
            env.setdefault("ASAN_OPTIONS", "halt_on_error=1:detect_leaks=" + ("0" if sys.platform == "darwin" else "1"))
            env.setdefault("UBSAN_OPTIONS", "halt_on_error=1")
            return run_suites(("manual", "fuzz-parse", "scale-collisions"), binary, tests, env,
                              {"FUZZ_CASES": os.environ.get("ASAN_FUZZ_CASES", "150"),
                               "FUZZ_LINES": os.environ.get("ASAN_FUZZ_LINES", "180"),
                               "COLLISIONS_COUNT": os.environ.get("ASAN_COLLISIONS_COUNT", "120")})
        if args.mode == "analyse":
            return subprocess.run([*command, "--exe", str(binary), "--debugger", Path(debugger).name, *tests], cwd=ROOT).returncode
        if args.mode == "valgrind":
            return subprocess.run([*command, "--exe", str(binary), "--valgrind", *tests], cwd=ROOT).returncode
        extra = ["--profile"] if args.mode == "profile" else []
        result = subprocess.run([*command, "--exe", str(binary), *extra, *tests], cwd=ROOT, env=env)
        if args.mode == "profile":
            case = ROOT / tests[0]
            gmon = case.with_suffix(".gmon")
            if not gmon.exists():
                raise ValueError("gmon.out não foi gerado. Esta plataforma/compilador pode não suportar -pg.")
            report = subprocess.run(["gprof", "-b", str(binary), str(gmon)], capture_output=True, text=True, check=True)
            output = ROOT / ("profile_" + case.stem + ".txt")
            output.write_text(report.stdout)
            print(f"Perfil: {output}")
        elif args.mode == "coverage":
            notes = sorted(build.rglob("*.gcno"))
            if not notes:
                raise ValueError("O compilador não produziu ficheiros de cobertura .gcno")
            report = subprocess.run(["gcov", "-b", "-c", "-p", *[str(p.relative_to(build)) for p in notes]], cwd=build, capture_output=True, text=True)
            (ROOT / "coverage_report.txt").write_text(report.stdout + report.stderr)
            coverage = ROOT / "coverage"
            coverage.mkdir(exist_ok=True)
            for path in build.rglob("*.gcov"):
                shutil.copyfile(path, coverage / path.name)
            print(report.stdout + report.stderr)
            uncovered = [f"{path.name}: {line.strip()}" for path in build.rglob("*.gcov")
                         for line in path.read_text(errors="replace").splitlines() if line.lstrip().startswith("#####:")]
            print(f"Linhas não executadas: {len(uncovered)}")
            print("\n".join(uncovered[:40]))
            if report.returncode:
                return report.returncode
        return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("resolve", "resolve2", "resolve-src", "count", "export", "suites", "rerun", "asan", "valgrind", "analyse", "profile", "lizard", "coverage"))
    parser.add_argument("--exe", default="")
    parser.add_argument("--name", default="cloudIST")
    parser.add_argument("--cache", default=".resolved_exe")
    parser.add_argument("--project", default="")
    parser.add_argument("--src-cache", default=".resolved_src")
    parser.add_argument("--output", default="")
    parser.add_argument("--test", default="")
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--fail-log", default="tests_failed.log")
    parser.add_argument("--compare-log", default="compare_failed.log")
    parser.add_argument("--stats", default="test_stats.txt")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--tests", nargs="*", default=[])
    parser.add_argument("--parts", nargs="+", choices=("manual", *SUITE_DIRS), default=["manual", *SUITE_DIRS])
    args = parser.parse_args()
    try:
        if args.mode in ("resolve", "resolve2"):
            resolve_exe(args.exe, ROOT / args.cache, args.name, search=args.mode == "resolve")
        elif args.mode == "resolve-src":
            resolve_project(args.project, Path(args.exe).resolve(), ROOT / args.src_cache)
        elif args.mode == "count":
            count_tests(args.tests, ROOT / args.stats)
        elif args.mode == "export":
            export_failures(args)
        elif args.mode == "suites":
            return run_suites(args.parts, args.exe, args.tests)
        elif args.mode == "rerun":
            return rerun(args)
        else:
            return run_tool(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
