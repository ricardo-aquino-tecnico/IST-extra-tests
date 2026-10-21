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
import textwrap
import time

from run_tests import ROOT, colour, command_names, select_cases, select_command_cases
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


def count_tests(names, stats, command_prefix="comando_"):
    cases = [ROOT / name for name in names]
    lines = ["Test suite statistics", "====================", f"Total tests:          {len(cases)}",
             f"Tests with .arg file: {sum(case.with_suffix('.arg').is_file() for case in cases)}",
             f"Tests with .txt desc: {sum(case.with_suffix('.txt').is_file() for case in cases)}",
             "", "Tests per command:", "--------------------"]
    for command in "drale":
        listed = command_names(command, command_prefix)
        amount = len(listed) if listed is not None else len(select_command_cases(command, cases, command_prefix))
        lines.append(f"  {command:<20} {amount} tests")
    lines += ["", "Python test scripts:", "--------------------"]
    for name in ("random_stress.py", "scale_limits.py", "fuzz_parse.py", "scale_collisions.py"):
        lines.append(f"  {name:<28} {'present' if (ROOT / name).is_file() else 'missing'}")
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
    python_failures = []
    for case in cases:
        for path in case.parent.glob(case.stem + ".*"):
            if path.is_file():
                target = destination / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        if case.parent.name in FAIL_DIRS:
            seed = re.search(r"seed_(\d+)", case.stem)
            python_failures.append("========================================\n"
                                   f"File: {case.relative_to(ROOT)}\nSeed: {seed[1] if seed else '—'}\nCases:\n{case.read_text()}\n")
    if python_failures:
        (destination / "python_failures.txt").write_text("".join(python_failures))
    compare_log = ROOT / args.compare_log
    if compare_log.is_file() and compare_log.read_text().strip():
        compare = destination / "compare"
        compare.mkdir()
        for case in select_cases(compare_log.read_text().splitlines()):
            for path in case.parent.glob(case.stem + ".*"):
                if path.is_file():
                    target = compare / path.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        shutil.copyfile(compare_log, compare / compare_log.name)
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
        make_zip = input("Queres criar um ficheiro zip com os testes exportados? [y/N] ").strip().lower() == "y"
    if make_zip:
        filename = ROOT / ("export_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f"))
        archive = shutil.make_archive(str(filename), "zip", ROOT, "export")
        print(f"ZIP: {archive}")
        if interactive and input("Queres apagar a pasta export/ original? [y/N] ").strip().lower() == "y":
            shutil.rmtree(destination)
    print("✔ Export complete.")


def status_table(results, goals):
    border = "+------------------+----------------------------+------------------------------------------------+"
    total_ms = sum(round(result["elapsed"] * 1000) for result in results)
    lines = [border, f"| {'Teste':<16} | {f'Status ({total_ms}ms)':<26} | {f'Argumentos ({goals})':<46} |", border]
    for result in results:
        count = result.get("planned", 0)
        label = "FAIL" if result["returncode"] else f"PASS ({count} {'test' if count == 1 else 'tests'})"
        status = f"{label:<16} {round(result['elapsed'] * 1000)}ms"
        arguments = textwrap.wrap(result["arguments"], 46, break_long_words=True, break_on_hyphens=False) or ["-"]
        lines.append(f"| {result['suite']:<16} | {status:<26} | {arguments[0]:<46} |")
        if len(arguments) > 1:
            second = arguments[1][:43] + "..." if len(arguments) > 2 else arguments[1]
            lines.append(f"| {'':<16} | {'':<26} | {second:<46} |")
    return "\n".join([*lines, border]) + "\n"


def run_suites(parts, exe, tests, env=None, overrides=None):
    config = {**os.environ, **(env or {}), **{key: str(value) for key, value in (overrides or {}).items()}}
    options = {"stress": ("STRESS_RUNS", "STRESS_STEPS", "STRESS_SEED", "STRESS_PROGRESS_EVERY", "STRESS_TIMEOUT"),
               "scale": ("SCALE_TYPES", "SCALE_FILES", "SCALE_PROGRESS_EVERY"),
               "fuzz-parse": ("FUZZ_CASES", "FUZZ_LINES", "FUZZ_SEED", "FUZZ_PROGRESS_EVERY"),
               "scale-collisions": ("COLLISIONS_COUNT", "COLLISIONS_START", "COLLISIONS_PROGRESS_EVERY")}
    flags = {"RUNS": "runs", "STEPS": "steps", "SEED": "seed", "PROGRESS_EVERY": "progress-every", "TIMEOUT": "timeout",
             "TYPES": "types", "FILES": "files", "CASES": "cases", "LINES": "max-lines", "COUNT": "count", "START": "start"}
    results = []
    for part in parts:
        status = ROOT / SUITE_DIRS[part] / "suite.status.json" if part in SUITE_DIRS else ROOT / "test_run.status.json"
        status.unlink(missing_ok=True)
        if part == "manual":
            (ROOT / config.get("FAIL_LOG", "tests_failed.log")).unlink(missing_ok=True)
        command = ["make", "-s", part, f"EXE={exe}", "EXE_CACHE_FILE=.resolved_exe_suite", "NO_PROMPT=1", "EXPORTING="]
        if tests:
            command.append("TESTS=" + " ".join(tests))
        command += [f"{key}={value}" for key, value in (overrides or {}).items()]
        start = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, env=env)
        metadata = json.loads(status.read_text()) if status.is_file() else {}
        arguments = " ".join(f"{flags[key.split('_', 1)[1]]} {config[key]}" for key in options.get(part, ()) if key in config) or "-"
        results.append({**metadata, "suite": part, "returncode": result.returncode, "elapsed": time.monotonic()-start, "arguments": arguments})
    failed = sum(bool(result["returncode"]) for result in results)
    suite = "ASAN" if env and "ASAN_OPTIONS" in env else "Python" if "manual" not in parts else "todos os testes"
    title = f"Resumo da suite {suite}:" if suite != "todos os testes" else "Resumo de todos os testes:"
    summary = "\n" + title + "\n" + status_table(results, config.get("ORIG_GOALS", "all"))
    if failed and "manual" in parts:
        fail_log = ROOT / config.get("FAIL_LOG", "tests_failed.log")
        if fail_log.is_file() and fail_log.read_text().strip():
            summary += "\nTestes manuais falhados:\n" + fail_log.read_text()
        elif any(result["suite"] == "manual" and result["returncode"] for result in results):
            summary += "\nA suite manual falhou antes de correr os testes individuais\n"
    summary += f"\n{len(results)-failed}/{len(results)} partes passaram, {failed}/{len(results)} partes falharam\n"
    if suite in ("ASAN", "Python"):
        summary += f"{suite} suite {'FAILED' if failed else 'PASSED'}.\n"
    display = summary.replace(title, colour(title, "1"))
    display = re.sub(r"\b(PASS|FAIL)\b", lambda match: colour(match[0], "1;31" if match[0] == "FAIL" else "1;32"), display)
    print(display, end="", flush=True)
    (ROOT / "test_summary.txt").write_text(summary)
    (ROOT / "test_summary.status.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    if failed and sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1" and not os.environ.get("EXPORTING"):
        if input("Executar 'make show-diff' para ver as diferenças? (Y/n) ").strip().lower() != "n":
            subprocess.run(["make", "show-diff"], cwd=ROOT)
    if failed and not os.environ.get("EXPORTING"):
        print(colour("\nPodes ignorar os erros do 'make' abaixo", "1"))
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
    elif failed and sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1" and not os.environ.get("EXPORTING"):
        if input("Executar 'make show-diff' para ver as diferenças? (Y/n) ").strip().lower() != "n":
            subprocess.run(["make", "show-diff"], cwd=ROOT)
    return failed


def resolve_project(value, exe, cache):
    candidate = value or (cache.read_text().strip() if cache.is_file() else str(exe if exe.is_dir() else exe.parent))
    while True:
        project = Path(candidate).expanduser().resolve()
        if project.is_file():
            project = project.parent
        if (project / "Makefile").is_file() and next(project.rglob("*.c"), None):
            cache.write_text(str(project) + "\n")
            return project
        if value or not sys.stdin.isatty():
            raise ValueError(f"Fontes/Makefile não encontrados em {project}. Define PROJECT_DIR=/caminho/do/projeto")
        candidate = input("Indica a pasta do projeto ou o caminho de um ficheiro .c: ").strip()


def run_tool(args):
    cache = ROOT / args.cache
    value = args.exe or (cache.read_text().strip() if cache.is_file() else "cloudIST")
    exe = Path(value).expanduser().resolve()
    if exe.is_dir():
        exe /= "cloudIST"
    project = resolve_project(args.project, exe, ROOT / args.src_cache)
    tests = args.tests
    if args.mode in ("analyse", "profile"):
        if not args.test:
            raise ValueError(f"Uso: make {args.mode} TEST=007")
        test = args.test
        if test.isdigit():
            test = f"test{int(test):03d}.in"
        test = str(Path(test).with_suffix(".in"))
        if not (ROOT / test).is_file() and Path(test).parent == Path("."):
            matches = sorted(ROOT.glob("*-failures/" + test))
            if matches:
                test = str(matches[0].relative_to(ROOT))
        tests = [str(case.relative_to(ROOT)) for case in select_cases([test])]
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
        print(colour(f"\nA compilar para {args.mode}: {flags}", "1;33"), flush=True)
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
            print(colour(f"A iniciar {Path(debugger).name.upper()}. Os argumentos e os ficheiros .conf estão preparados. Executa 'run' para iniciar.", "2"), flush=True)
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
            print("\n".join(report.stdout.splitlines()[:25]))
            print(colour(f"Relatório detalhado guardado em {output}", "2"))
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
            if uncovered:
                print(colour(f"Linhas não executadas ({len(uncovered)}):", "1;33"))
                for line in uncovered:
                    print(colour("  " + line, "31"))
            else:
                print(colour("✔ Todas as linhas foram executadas!", "1;32"))
            if sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1":
                if input("Guardar relatório completo em coverage_report.gcov? [y/N] ").strip().lower() == "y":
                    (ROOT / "coverage_report.gcov").write_text("\n".join(path.read_text() for path in sorted(coverage.glob("*.gcov"))))
                    print("✔ Relatório guardado em coverage_report.gcov")
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
    parser.add_argument("--command-prefix", default="comando_")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--tests", nargs="*", default=[])
    parser.add_argument("--parts", nargs="+", choices=("manual", *SUITE_DIRS), default=["manual", *SUITE_DIRS])
    args = parser.parse_args()
    try:
        if args.mode in ("resolve", "resolve2"):
            resolve_exe(args.exe, ROOT / args.cache, args.name, search=args.mode == "resolve")
        elif args.mode == "resolve-src":
            cache = ROOT / args.cache
            exe = args.exe or (cache.read_text().strip() if cache.is_file() else str(ROOT / args.name))
            resolve_project(args.project, Path(exe).expanduser().resolve(), ROOT / args.src_cache)
        elif args.mode == "count":
            count_tests(args.tests, ROOT / args.stats, args.command_prefix)
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
