#!/usr/bin/env python3
"""Testes do exercício 1; apenas biblioteca standard de Python 3."""

import argparse
import difflib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parent
STATUS = "=================================== DATA CENTER STATUS ==================================="
END = "================================================================--------------------------"


def split_files(text):
    """Os marcadores são comentários válidos nos próprios ficheiros .conf."""
    files = {}
    name = None
    for line in text.splitlines(keepends=True):
        if line.startswith("# FILE: "):
            name = line.removeprefix("# FILE: ").strip()
            path = Path(name)
            if not name or path.is_absolute() or ".." in path.parts or name in files:
                raise ValueError(f"Nome de ficheiro inválido ou repetido: {name!r}")
            files[name] = ""
        else:
            if name is None:
                name = "10.conf"
                files[name] = ""
            files[name] += line
    return files


def listings(stdout):
    # shortcut: reconhece o formato L do código base, adaptar se o projeto alterar a listagem.
    result = []
    inside = False
    for line in stdout.splitlines():
        if line == STATUS:
            if inside:
                raise ValueError("Listagem L sem terminador")
            inside = True
        if inside:
            result.append(line.rstrip())
        if inside and line == END:
            inside = False
    if inside:
        raise ValueError("Listagem L incompleta")
    return normalise("\n".join(result))


def normalise(text):
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    return "\n".join(lines) + ("\n" if lines else "")


def resolve_listing_paths(text, work):
    return re.sub(r"^(├─ Executable|└─ Input Dir) : (.+)$",
                  lambda match: f"{match[1]} : {(work / match[2]).resolve()}", text, flags=re.M)


def check_copy(source, destination):
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError(f"Pasta da VM ausente ou ligada simbolicamente: {destination}")
    if {p.relative_to(source) for p in source.rglob("*")} != {p.relative_to(destination) for p in destination.rglob("*")}:
        raise ValueError(f"A árvore de ficheiros copiada é diferente: {destination}")
    for src in [source, *source.rglob("*")]:
        dst = destination / src.relative_to(source)
        if dst.is_symlink():
            raise ValueError(f"A cópia contém um link simbólico: {dst}")
        if src.is_dir():
            if not dst.is_dir():
                raise ValueError(f"Subpasta ausente: {dst}")
        elif not dst.is_file() or dst.read_bytes() != src.read_bytes():
            raise ValueError(f"Ficheiro ausente ou conteúdo diferente: {dst}")
        elif os.path.samefile(src, dst) or dst.stat().st_nlink > 1:
            raise ValueError(f"O ficheiro foi ligado em vez de copiado: {dst}")


def run_case(case, exe, timeout, *, command_prefix=(), debugger=None, profile=False):
    template = case.read_text()
    robustness = "# ROBUSTNESS" in template.splitlines()
    expected_template = case.with_suffix(".out").read_text()
    expected = normalise(expected_template)
    reasons = []
    stdout = stderr = actual = ""
    returncode = None
    timed_out = False
    elapsed = 0
    replacements = {}
    # O claim exclusivo protege a limpeza sem pré-criar a pasta que o projeto deve criar.
    prefix = "SO_" + uuid.uuid4().hex[:24]
    reservations = {}
    owned = []
    claims = []
    try:
        if profile:
            case.with_suffix(".gmon").unlink(missing_ok=True)
        for token in sorted(set(re.findall(r"@RESERV(?:[A-Z]|\d{1,6})@", template + expected_template))):
            name = prefix + token.removeprefix("@RESERV").removesuffix("@")
            folder = Path("/tmp/CloudIST") / name
            folder.parent.mkdir(exist_ok=True)
            claim = folder.with_name("." + name)
            claim.mkdir()
            claims.append(claim)
            if folder.exists() or folder.is_symlink():
                raise ValueError(f"A pasta da reserva já existe: {folder}")
            owned.append(folder)
            reservations[token] = name
        with tempfile.TemporaryDirectory(prefix="so-ex1-") as temp:
            work = Path(temp).resolve()
            inputs = work / "inputs"
            (inputs / "nested/deep/level3/level4/level5").mkdir(parents=True)
            (inputs / "empty subfolder").mkdir()
            (inputs / "nested/empty").mkdir()
            (inputs / "text.txt").write_bytes(b"CloudIST\nsecond line\n")
            (inputs / ".hidden").write_bytes(b"hidden\n")
            (inputs / "empty.bin").write_bytes(b"")
            (inputs / "nested/deep/level3/level4/level5/dados.bin").write_bytes(bytes(range(256)) * 81)
            (inputs / "nested/espaços e acentos.txt").write_text("Olá, SO!\n")
            (inputs / "ignored.conf").write_text("# Dados da VM, não configuração do centro\n")
            empty = work / "empty"
            empty.mkdir()
            app = work / "app"
            shutil.copyfile(shutil.which("true") or "/usr/bin/true", app)
            app.chmod(0o700)
            replacements = {"@INPUT@": str(inputs), "@EMPTY@": str(empty), "@EXE@": str(app), **reservations}
            replacements["@WORK@"] = str(work)

            def expand(text):
                for old, new in replacements.items():
                    text = text.replace(old, new)
                return text

            expected = normalise(expand(expected_template))
            configs = work / "config files"
            configs.mkdir()
            # Criar em ordem inversa expõe implementações que usam a ordem de criação.
            for name, content in reversed(list(split_files(expand(template)).items())):
                target = configs / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if f"# NO_NEWLINE: {name}" in template.splitlines():
                    content = content.removesuffix("\n")
                target.write_text(content)
            argfile = case.with_suffix(".arg")
            args = argfile.read_text().split() if argfile.exists() else ["2", "8", "16", "4"]
            if len(args) != 4:
                raise ValueError("O ficheiro .arg deve conter SERVERS RAM DISK CPU")
            command = [str(exe), *args, str(configs)]
            if debugger:
                if debugger == "lldb":
                    command = [debugger, "-o", "breakpoint set --name main", "--", *command]
                else:
                    command = [debugger, "-ex", "break main", "--args", *command]
                subprocess.run(command, cwd=work, check=True)
                return None
            originals = {p: p.read_bytes() for p in inputs.rglob("*") if p.is_file()}
            start = time.monotonic()
            process = subprocess.Popen(
                [*command_prefix, *command], cwd=work, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                reasons.append(f"Timeout ({timeout:g} s)")
                timed_out = True
            except BaseException:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
            elapsed = time.monotonic() - start
            returncode = process.returncode
            if process.returncode not in ((0, 1) if robustness else (0,)):
                reasons.append(f"Código de saída: {process.returncode}")
            # O aviso do stub fornecido pertence ao exercício 2.
            errors = [line for line in stderr.splitlines() if line != "VM execution not implemented in base version."]
            if errors and not robustness:
                reasons.append("stderr: " + " | ".join(errors[:5]))
            if robustness and re.search(r"AddressSanitizer|LeakSanitizer|UndefinedBehaviorSanitizer|runtime error:|Sanitizer:DEADLYSIGNAL", stdout + stderr):
                reasons.append("Diagnóstico de ASAN/UBSan")
            actual = normalise(stdout) if robustness else listings(stdout)
            if not robustness:
                actual = resolve_listing_paths(actual, work)
                expected = resolve_listing_paths(expected, work)
            for line in expand(template).splitlines():
                if line.startswith("# COPY: "):
                    source, relative = line.removeprefix("# COPY: ").split(" -> ")
                    target = Path("/tmp/CloudIST") / relative
                    if target.parent not in owned or not re.fullmatch(re.escape(target.parent.name) + r"_[1-9]\d*", target.name):
                        raise ValueError(f"Destino de cópia fora da reserva do teste: {target}")
                    check_copy(Path(source), target)
                    actual += f"COPY {relative} OK\n"
                elif line.startswith("# WAIT: "):
                    minimum = int(line.removeprefix("# WAIT: ")) / 1000
                    if elapsed < minimum:
                        reasons.append(f"E não esperou o mínimo de {minimum:g} s ({elapsed:.3f} s)")
            if any(not p.is_file() or p.read_bytes() != data for p, data in originals.items()):
                reasons.append("Os ficheiros de entrada foram alterados")
            actual = normalise(actual)
            if not robustness and actual != expected:
                reasons.append("Output diferente")
            if profile:
                gmon = work / "gmon.out"
                if not gmon.is_file():
                    reasons.append("gmon.out ausente: o compilador/plataforma pode não suportar -pg")
                else:
                    shutil.copyfile(gmon, case.with_suffix(".gmon"))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        reasons.append(str(error))
    finally:
        for folder in owned:
            if folder.is_symlink():
                folder.unlink()
            elif folder.exists():
                shutil.rmtree(folder)
        for claim in claims:
            claim.rmdir()
    def stable(text):
        for token, value in sorted(replacements.items(), key=lambda pair: len(pair[1]), reverse=True):
            text = text.replace(value, token)
        return text

    reasons = [stable(reason) for reason in reasons]
    return {"expected": stable(expected), "actual": stable(actual), "stdout": stdout, "stderr": stderr,
            "returncode": returncode, "timed_out": timed_out, "elapsed": elapsed, "reasons": reasons,
            "comparison": stable(actual) + f"\nEXIT: {returncode}\nTIMEOUT: {timed_out}\nSTDERR:\n" + stable(stderr)
                          + "\nREASONS:\n" + "\n".join(reasons)}


def save_result(case, result, tag=""):
    base = case.with_suffix("")

    def path(suffix):
        return base.with_name(base.name + tag + suffix)

    metadata = {key: result[key] for key in ("returncode", "timed_out", "elapsed", "reasons")}
    path(".status.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    diff = "".join(difflib.unified_diff(result["expected"].splitlines(True), result["actual"].splitlines(True),
                                        fromfile=case.with_suffix(".out").name,
                                        tofile=case.with_suffix(".myout").name))
    if result["reasons"] or tag:
        for suffix, key in ((".myout", "actual"), (".stdout", "stdout"), (".stderr", "stderr"), (".expected", "expected")):
            path(suffix).write_text(result[key])
        path(".diff").write_text("\n".join(result["reasons"]) + "\n" + diff)
    else:
        for suffix in (".myout", ".stdout", ".stderr", ".diff", ".expected"):
            path(suffix).unlink(missing_ok=True)


def select_cases(names):
    allowed = {ROOT, *(ROOT / name for name in ("stress-failures", "scale-failures", "fuzz-failures", "collisions-failures"))}
    cases = [(ROOT / Path(name).with_suffix(".in")).resolve() for name in names]
    if any(case.parent not in allowed or not case.is_file() for case in cases):
        raise ValueError("Seleciona testes existentes na raiz de SO ou nas pastas *-failures da suite")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--exe2")
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--command", choices=list("drale"))
    parser.add_argument("--command-prefix", default="comando_")
    parser.add_argument("--debugger", choices=("lldb", "gdb"))
    parser.add_argument("--valgrind", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--fail-log", default="tests_failed.log")
    parser.add_argument("tests", nargs="*")
    args = parser.parse_args()
    exe = Path(args.exe).expanduser().resolve()
    if not exe.is_file() or not os.access(exe, os.X_OK):
        parser.error(f"Executável não encontrado ou sem permissão: {exe}. Define EXE=/caminho/cloudIST")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("TIMEOUT deve ser positivo e finito")
    names = args.tests
    exe2 = Path(args.exe2).expanduser().resolve() if args.exe2 else None
    if exe2 and (not exe2.is_file() or not os.access(exe2, os.X_OK)):
        parser.error(f"Segundo executável inválido: {exe2}")
    log = ROOT / args.fail_log
    if args.rerun:
        names = log.read_text().splitlines() if log.exists() else []
        if not names:
            print("Não há testes falhados para repetir.")
            return 0
    try:
        cases = select_cases(names) if names else sorted(ROOT.glob("test*.in"))
    except ValueError as error:
        parser.error(str(error))
    if args.command:
        command_file = ROOT / f"{args.command_prefix}{args.command}.txt"
        if not command_file.exists():
            command_file = ROOT / f"comando {args.command}.txt"
        if command_file.exists():
            wanted = [name for line in command_file.read_text().splitlines() for name in line.split("#", 1)[0].split()]
            try:
                selected = select_cases(wanted)
            except ValueError as error:
                parser.error(str(error))
            cases = [case for case in selected if case in cases]
        else:
            cases = [case for case in cases if re.search(rf"^{args.command.upper()}(?: |$)", case.read_text(), re.M)]
    if not cases:
        parser.error("Nenhum teste selecionado")
    if args.debugger:
        if len(cases) != 1:
            parser.error("analyse requer exatamente um teste (TEST=test007.in)")
        result = run_case(cases[0], exe, args.timeout, debugger=args.debugger)
        if result:
            print("; ".join(result["reasons"]), file=sys.stderr)
            return 1
        return 0
    prefix = ["valgrind", "--quiet", "--leak-check=full", "--error-exitcode=42"] if args.valgrind else []
    failed = []
    count = 0
    start = time.monotonic()
    for case in cases:
        result = run_case(case, exe, args.timeout, command_prefix=prefix, profile=args.profile)
        reasons = result["reasons"]
        if exe2:
            other = run_case(case, exe2, args.timeout)
            save_result(case, result, ".cmp1")
            save_result(case, other, ".cmp2")
            diff = "".join(difflib.unified_diff(result["comparison"].splitlines(True), other["comparison"].splitlines(True),
                                                fromfile="EXE", tofile="EXE2"))
            if diff or reasons or other["reasons"]:
                reasons = ["Executáveis diferentes" if diff else "Ambos os executáveis falharam"] + reasons + other["reasons"]
                case.with_suffix(".cmpdiff").write_text("\n".join(reasons) + "\n" + diff)
            else:
                case.with_suffix(".cmpdiff").unlink(missing_ok=True)
        else:
            save_result(case, result)
        count += 1
        if reasons:
            failed.append(str(case.relative_to(ROOT)))
        print(f"{'FAIL' if reasons else 'PASS'} {case.stem}" + (": " + "; ".join(reasons) if reasons else ""), flush=True)
        if reasons and args.fail:
            break
    log.write_text("".join(name + "\n" for name in failed))
    (ROOT / "test_run.status.json").write_text(json.dumps({"planned": len(cases), "passed": count-len(failed),
                                                          "failed": len(failed), "elapsed": time.monotonic()-start}) + "\n")
    print(f"\n{count - len(failed)}/{count} passaram; {len(failed)} falharam.")
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
