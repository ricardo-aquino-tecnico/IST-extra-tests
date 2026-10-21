"""Observações de processos e de ficheiros concorrentes dos exercícios 2 e 3."""

from collections import Counter
from contextlib import ExitStack
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from run_tests import END, STATUS, ROOT, check_copy, normalise, prepare_configs, prepare_inputs


def directives(template, name):
    return [json.loads(line[len(name)+4:]) for line in template.splitlines() if line.startswith(f"# {name}: ")]


def read_events(path):
    text = path.read_text() if path.exists() else ""
    if text and not text.endswith("\n"):
        text = text.rsplit("\n",1)[0] if "\n" in text else ""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def stop_process(process):
    try:
        os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def check_assertion(check, events, cpu_calls, stdout, elapsed, parent_pid, observed):
    kind = check["kind"]
    starts = [event for event in events if event["event"] == "start"]
    ends = [event for event in events if event["event"] == "end"]
    if kind == "executions":
        expected = Counter(check["counts"])
        if Counter(event["tag"] for event in starts) != expected or Counter(event["tag"] for event in ends) != expected:
            raise ValueError("Número de execuções/inícios/fins diferente do esperado")
    elif kind == "processes":
        if not starts or len({event["pid"] for event in starts}) != len(starts) or any(event["pid"] == parent_pid for event in starts):
            raise ValueError("Cada VM deve executar num processo distinto do CloudIST e das outras VMs")
    elif kind == "before_exec":
        if not starts or any(not event["ready"] for event in starts):
            raise ValueError("A cópia não estava disponível quando a aplicação arrancou")
    elif kind == "overlap":
        selected = [event for event in starts if event["tag"] in check["tags"]]
        finished = [event for event in ends if event["tag"] in check["tags"]]
        if len(selected) < 2 or len(finished) != len(selected) or max(event["time"] for event in selected) >= min(event["time"] for event in finished):
            raise ValueError("As VMs foram serializadas; os intervalos de execução não se sobrepõem")
    elif kind == "nonblocking":
        first = [event["time"] for event in ends if event["tag"] == check["slow"]]
        following = [event["time"] for event in starts if event["tag"] == check["next"]]
        if not first or not following or min(following) >= min(first):
            raise ValueError("A bloqueou o processamento dos comandos seguintes até à conclusão da VM")
    elif kind == "limits":
        selected = [event for event in starts if event["tag"] == check["tag"]]
        if not selected:
            raise ValueError("A aplicação que observa os limites não arrancou")
        for resource in ("ram", "disk"):
            if resource in check:
                limit = check[resource] * (1 << 30)
                if any(event[resource + "_soft"] != limit or event[resource + "_hard"] != limit for event in selected):
                    raise ValueError(f"Limite {resource} soft/hard não corresponde a {check[resource]} GB")
    elif kind == "cpu":
        calls = [call for call in cpu_calls if call["tag"] == check["tag"]]
        if len(calls) != check.get("count", 1) or any(not math.isfinite(call["percent"]) or abs(call["percent"]-check["percent"]) > .01 for call in calls):
            raise ValueError("Percentagem/número de invocações de cpulimit diferente da fórmula do enunciado")
    elif kind == "real_cpu":
        selected = [event for event in events if event["tag"] == check["tag"]]
        if len(selected) != 2:
            raise ValueError("A aplicação de medição CPU não terminou")
        start, end = sorted(selected, key=lambda event: event["time"])
        wall = end["time"]-start["time"]
        cpu = end["cpu"]-start["cpu"]
        if wall <= 0 or cpu / wall > check["percent"] / 100 * 1.5 + .10:
            raise ValueError("O consumo observado de CPU ultrapassou a tolerância do limite pedido")
    elif kind == "snapshot":
        blocks = stdout.split(STATUS)[1:]
        index = check.get("index", -1)
        if not blocks or not (-len(blocks) <= index < len(blocks)) or END not in blocks[index]:
            raise ValueError("Listagem L ausente ou incompleta para verificar libertação de recursos")
        block = blocks[index].split(END, 1)[0]
        used = re.findall(r"Resources Used\s*:\s*([\d.]+) vCPUs\s*\|\s*(\d+) GB RAM\s*\|\s*(\d+) GB Disk", block)
        expected = check["used"]
        if len(used) != len(expected) or any(any(abs(float(a)-float(b)) > .01 for a,b in zip(row,want)) for row,want in zip(used,expected)):
            raise ValueError("Os recursos usados na listagem não correspondem às VMs ainda existentes")
        reservations = re.search(r"\[ RESERVATIONS \]\s*\((\d+) total\)", block)
        if not reservations or int(reservations[1]) != check["reservations"]:
            raise ValueError("A reserva terminada não foi removida, ou uma reserva ainda ativa foi removida")
    elif kind == "duration":
        if elapsed * 1000 < check["min_ms"] or elapsed * 1000 > check["max_ms"]:
            raise ValueError(f"Duração {elapsed:.3f}s fora de [{check['min_ms']}, {check['max_ms']}] ms; verificar E/MAX_THREADS")
    elif kind == "after":
        first = observed.get(check["path"])
        if first is None or first * 1000 < check["min_ms"]:
            raise ValueError("A diretoria da VM apareceu antes da espera E correspondente ou não foi criada")
    elif kind == "absent":
        if Path(check["path"]).exists():
            raise ValueError("Um ficheiro sem extensão .conf foi processado")
    else:
        raise ValueError(f"Asserção desconhecida: {kind}")


def compile_probes(apps, replacements, work):
    paths = {}
    for app in apps:
        tag = app["name"]
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", tag):
            raise ValueError("Nome da aplicação de teste inválido")
        directory = app["copy"]
        for old,new in replacements.items():
            directory = directory.replace(old,new)
        if any(not Path(part).is_relative_to(Path("/tmp/CloudIST")) for part in directory.split("|")):
            raise ValueError("A sonda só pode observar cópias na reserva de teste")
        values = {"APP_TAG": tag, "TRACE_FILE": str(work / "events.jsonl"), "COPY_DIR": directory,
                  "CHECK_CONTENT": app.get("content", True), "SLEEP_MS": app.get("sleep_ms", 0),
                  "BUSY_MS": app.get("busy_ms", 0), "EXIT_CODE": app.get("exit", 0), "RAISE_SIGNAL": app.get("signal", 0)}
        command = [*shlex.split(os.environ.get("CC") or "cc"), "-std=c17", "-D_POSIX_C_SOURCE=200809L", "-O1", "-Wall", "-Wextra", "-Werror"]
        command += [f"-D{key}={json.dumps(value) if isinstance(value,str) else int(value)}" for key,value in values.items()]
        binary = work / ("probe_"+tag)
        result = subprocess.run([*command, str(ROOT / "vm_probe.c"), "-o", str(binary)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError("Compilação da aplicação de teste falhou: " + result.stderr)
        paths[f"@APP_{tag}@"] = str(binary)
    return paths


def install_cpu_spy(work, real_cpu, probe):
    # shortcut: observa cpulimit em PATH; usar rastreio de execve se o projeto fixar um caminho absoluto.
    actual = shutil.which("cpulimit") if real_cpu else None
    bin_dir = work / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "cpulimit"
    wrapper.write_text("#!/bin/sh\nexec " + shlex.join([probe,"--spy",str(work/"cpu.jsonl"),actual or ""]) + ' "$@"\n')
    wrapper.chmod(0o700)
    return str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def run_advanced(case, exe, timeout, *, command_prefix=(), debugger=None, profile=False):
    template = case.read_text()
    exercise = int(re.search(r"^# EXERCISE: ([23])$", template, re.M)[1])
    expected = normalise(case.with_suffix(".out").read_text())
    result = dict(expected=expected, actual="", stdout="", stderr="", returncode=None, timed_out=False, elapsed=0, reasons=[], comparison="")
    requirements = directives(template, "REQUIRE")
    if "linux" in requirements and sys.platform != "linux":
        result["skipped"] = "Medição de RLIMIT_AS requer Linux/Sigma"
        return result
    real_cpu = "cpulimit" in requirements
    if real_cpu and not shutil.which("cpulimit"):
        result["skipped"] = "cpulimit real não instalado"
        return result
    if real_cpu:
        try:
            help_result = subprocess.run([shutil.which("cpulimit"),"--help"],capture_output=True,text=True,timeout=3)
        except (OSError,subprocess.TimeoutExpired):
            result["skipped"] = "Não foi possível verificar a compatibilidade do cpulimit instalado"
            return result
        usage = help_result.stdout + help_result.stderr
        if not all(re.search(rf"(?:^|\s)-{flag}(?:[,\s]|$)",usage,re.M) for flag in ("q","f")):
            result["skipped"] = "cpulimit instalado não suporta -q/-f do enunciado; usar Linux/Sigma"
            return result
        # A ajuda pode funcionar mesmo com um binário Linux instalado num Mac.
        try:
            probe = subprocess.Popen([shutil.which("cpulimit"), "-q", "-f", "-l", "100", "--",
                                      sys.executable, "-c", "import time; time.sleep(.15)"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                _, errors = probe.communicate(timeout=3)
                if probe.returncode:
                    result["skipped"] = "cpulimit instalado falha ao executar: " + errors.decode(errors="replace").strip()[:200]
            finally:
                stop_process(probe)
        except (OSError, subprocess.TimeoutExpired):
            result["skipped"] = "cpulimit instalado não consegue executar uma aplicação de controlo"
        if result.get("skipped"):
            return result
    owned = []
    claims = []
    process = None
    replacements = {}
    try:
        for token in sorted(set(re.findall(r"@RESERV(?:[A-Z]|\d{1,6})@", template))):
            name = "SO_" + uuid.uuid4().hex[:24]
            folder = Path("/tmp/CloudIST") / name
            folder.parent.mkdir(exist_ok=True)
            claim = folder.with_name("."+name)
            claim.mkdir()
            claims.append(claim)
            if folder.exists() or folder.is_symlink():
                raise ValueError("A reserva de teste já existe")
            owned.append(folder)
            replacements[token] = name
        with tempfile.TemporaryDirectory(prefix=f"so-ex{exercise}-") as temp, ExitStack() as cleanup:
            work = Path(temp).resolve()
            replacements.update(prepare_inputs(work))
            probes = compile_probes(directives(template, "APP"), replacements, work)
            replacements.update(probes)
            expanded = template
            comparison_expected = expected
            for old,new in replacements.items():
                expanded = expanded.replace(old,new)
                comparison_expected = comparison_expected.replace(old,new)
            checks = directives(expanded, "ASSERT")
            configs = prepare_configs(template, replacements, work)
            args = case.with_suffix(".arg").read_text().split()
            if len(args) != 4:
                raise ValueError(".arg deve conter SERVERS RAM DISK CPU")
            command = [str(exe), *args, str(configs)]
            if exercise == 3 or os.environ.get("MAX_THREADS"):
                threads = str(directives(template, "THREADS")[0]) if exercise == 3 else os.environ["MAX_THREADS"]
                if int(threads) < 1:
                    raise ValueError("MAX_THREADS deve ser positivo")
                command.append(threads)
            env = dict(os.environ)
            if probes:
                env["PATH"] = install_cpu_spy(work,real_cpu,next(iter(probes.values())))
            if debugger:
                prefix = [debugger,"-o","breakpoint set --name main","--"] if debugger == "lldb" else [debugger,"-ex","break main","--args"]
                subprocess.run([*prefix,*command], cwd=work, env=env, check=True)
                return None
            original = {path:path.read_bytes() for path in (work/"inputs").rglob("*") if path.is_file()}
            observed = {}
            watched = [check["path"] for check in checks if check["kind"] == "after"]
            copies = []
            verified = set()
            for line in expanded.splitlines():
                if line.startswith("# COPY: "):
                    source,relative = line[8:].split(" -> ")
                    target = Path("/tmp/CloudIST")/relative
                    if target.parent not in owned or not re.fullmatch(re.escape(target.parent.name)+r"_[1-9]\d*",target.name):
                        raise ValueError("Destino fora da reserva de teste")
                    copies.append(((work/source).resolve(),target,relative))
            def observe_copies():
                for source,target,_ in copies:
                    if target not in verified and target.is_dir():
                        try: check_copy(source,target)
                        except (ValueError,OSError): continue
                        verified.add(target)
            start = time.monotonic()
            with (work/"stdout").open("w+") as output, (work/"stderr").open("w+") as errors:
                process = subprocess.Popen([*command_prefix,*command],cwd=work,env=env,stdin=subprocess.DEVNULL,
                                           stdout=output,stderr=errors,start_new_session=True)
                cleanup.callback(stop_process,process)
                while process.poll() is None:
                    elapsed = time.monotonic()-start
                    for path in watched:
                        if path not in observed and Path(path).exists(): observed[path] = elapsed
                    observe_copies()
                    if elapsed > timeout:
                        os.killpg(process.pid, signal.SIGKILL)
                        result["timed_out"] = True
                        break
                    time.sleep(.005)
                process.wait()
                result["elapsed"] = time.monotonic()-start
                result["returncode"] = process.returncode
                observe_copies()
                for path in watched:
                    if path not in observed and Path(path).exists(): observed[path] = result["elapsed"]
                # O CloudIST pode chegar ao EOF antes dos seus últimos filhos; esperar as sondas sem exigir wait no EOF.
                counts = next((check["counts"] for check in checks if check["kind"] == "executions"), {})
                deadline = start + timeout
                while counts and time.monotonic() < deadline:
                    events = read_events(work/"events.jsonl")
                    observe_copies()
                    if Counter(e["tag"] for e in events if e["event"] == "end") == Counter(counts): break
                    if process.returncode or "VM execution not implemented in base version." in (work/"stderr").read_text(): break
                    time.sleep(.01)
                output.seek(0); result["stdout"] = output.read()
                errors.seek(0); result["stderr"] = errors.read()
            if result["timed_out"]: result["reasons"].append(f"Timeout ({timeout:g} s)")
            allowed = directives(template, "ALLOW_EXIT")
            if process.returncode not in (allowed[0] if allowed else [0]): result["reasons"].append(f"Código de saída: {process.returncode}")
            if re.search(r"AddressSanitizer|LeakSanitizer|UndefinedBehaviorSanitizer|runtime error:|Sanitizer:DEADLYSIGNAL", result["stdout"]+result["stderr"]):
                result["reasons"].append("Diagnóstico de ASAN/UBSan")
            events = read_events(work/"events.jsonl")
            cpu_calls = read_events(work/"cpu.jsonl")
            actual = []
            for i,check in enumerate(checks,1):
                try:
                    duration = result["elapsed"]
                    if exercise == 3 and observed:
                        # shortcut: observa cópias em A; adaptar a medição se o projeto as antecipar para R.
                        first_wait = min(c["min_ms"] for c in checks if c["kind"] == "after") + 20
                        duration = max(observed.values()) - min(observed.values()) + first_wait / 1000
                    check_assertion(check,events,cpu_calls,result["stdout"],duration,process.pid,observed)
                    actual.append(f"CHECK {i:02d} {check['kind']} OK")
                except ValueError as error:
                    result["reasons"].append(str(error))
            for source,target,relative in copies:
                if target.exists() or target.is_symlink() or target not in verified:
                    check_copy(source,target)
                actual.append(f"COPY {relative} OK")
            if any(not path.is_file() or path.read_bytes()!=data for path,data in original.items()):
                result["reasons"].append("Os inputs foram alterados")
            if profile:
                gmon = work/"gmon.out"
                if not gmon.is_file(): result["reasons"].append("gmon.out ausente")
                else: shutil.copyfile(gmon,case.with_suffix(".gmon"))
            result["actual"] = normalise("\n".join(actual))
            if result["actual"] != comparison_expected:
                result["reasons"].append("Observações diferentes das expectativas")
            result["events"] = events
            result["cpu_calls"] = cpu_calls
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        result["reasons"].append(str(error))
    finally:
        for folder in owned:
            if folder.is_symlink(): folder.unlink()
            elif folder.exists(): shutil.rmtree(folder)
        for claim in claims: claim.rmdir()
    for token,value in sorted(replacements.items(),key=lambda pair:len(pair[1]),reverse=True):
        result["actual"] = result["actual"].replace(value,token)
        result["reasons"] = [reason.replace(value,token) for reason in result["reasons"]]
    compare_stderr = result["stderr"]
    result["comparison_stdout"] = result["stdout"]
    for token,value in sorted(replacements.items(),key=lambda pair:len(pair[1]),reverse=True):
        compare_stderr = compare_stderr.replace(value,token)
        result["comparison_stdout"] = result["comparison_stdout"].replace(value,token)
    for event in result.get("events",[]):
        compare_stderr = re.sub(rf"\b{event['pid']}\b", "@PID@", compare_stderr)
        result["comparison_stdout"] = re.sub(rf"\b{event['pid']}\b", "@PID@", result["comparison_stdout"])
    result["comparison"] = result["actual"] + f"EXIT: {result['returncode']}\nTIMEOUT: {result['timed_out']}\nSTDERR:\n" + compare_stderr + "\n".join(result["reasons"])
    return result
