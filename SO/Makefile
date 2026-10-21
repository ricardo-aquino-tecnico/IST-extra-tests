MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DEFAULT_GOAL := manual-tests
.NOTPARALLEL:
.PHONY: all quick manual manual-tests exercise1 exercise2 exercise3 resolve-exe resolve-exe2 resolve-src python selftest d r a l e export export-zip zip compare count rerun show-diff asan valgrind analyse profile lizard coverage clean help stress scale fuzz-parse scale-collisions

PYTHON ?= python3
FAIL ?= 0
EXE ?=
EXE2 ?=
EXE_NAME ?= cloudIST
EXE_CACHE_FILE ?= .resolved_exe
EXE2_CACHE_FILE ?= .resolved_exe2
SRC_CACHE_FILE ?= .resolved_src
FAIL_LOG ?= tests_failed.log
COMPARE_FAIL_LOG ?= compare_failed.log
STATS_FILE ?= test_stats.txt
TESTS ?= $(sort $(wildcard test*.in))
EXERCISE2_TESTS ?= $(if $(filter-out file,$(origin TESTS)),$(TESTS),$(sort $(wildcard exercise2/test*.in)))
EXERCISE3_TESTS ?= $(if $(filter-out file,$(origin TESTS)),$(TESTS),$(sort $(wildcard exercise3/test*.in)))
EXERCISE2_FAIL_LOG ?= exercise2/tests_failed.log
EXERCISE3_FAIL_LOG ?= exercise3/tests_failed.log
MAX_THREADS ?=
ORIG_GOALS ?= $(if $(MAKECMDGOALS),$(MAKECMDGOALS),$(.DEFAULT_GOAL))
COMPARE_TESTS ?= $(TESTS)
CMD_LIST_PREFIX ?= comando_
TIMEOUT ?= 5
TEST ?=
ASAN_SRC ?=
PROJECT_DIR ?= $(ASAN_SRC)
AUTO_ZIP ?= 0
NO_PROMPT ?= 0
STRESS_RUNS ?= 1000
STRESS_STEPS ?= 1250
STRESS_SEED ?= $(shell date +%s)
STRESS_PROGRESS_EVERY ?= 25
STRESS_TIMEOUT ?= 8
SCALE_TYPES ?= 96
SCALE_FILES ?= 200
SCALE_PROGRESS_EVERY ?= 0
FUZZ_CASES ?= 1200
FUZZ_LINES ?= 900
FUZZ_SEED ?= $(shell date +%s)
FUZZ_PROGRESS_EVERY ?= 50
COLLISIONS_COUNT ?= 120
COLLISIONS_START ?= 1000000
COLLISIONS_PROGRESS_EVERY ?= 0
ASAN_MANUAL_TESTS ?= $(TESTS)
ASAN_FUZZ_CASES ?= 150
ASAN_FUZZ_LINES ?= 180
ASAN_COLLISIONS_COUNT ?= 120
VALGRIND_TESTS ?= $(TESTS)
COVERAGE_TESTS ?= $(TESTS)
ASAN_EXE ?= .build/asan/cloudIST
VALGRIND_EXE ?= .build/valgrind/cloudIST
ANALYSE_EXE ?= .build/analyse/cloudIST
PROFILE_EXE ?= .build/profile/cloudIST
COVERAGE_EXE ?= .build/coverage/cloudIST
export FAIL_LOG COMPARE_FAIL_LOG CC AUTO_ZIP NO_PROMPT ASAN_FUZZ_CASES ASAN_FUZZ_LINES ASAN_COLLISIONS_COUNT
export ORIG_GOALS STRESS_RUNS STRESS_STEPS STRESS_SEED STRESS_PROGRESS_EVERY STRESS_TIMEOUT
export SCALE_TYPES SCALE_FILES SCALE_PROGRESS_EVERY FUZZ_CASES FUZZ_LINES FUZZ_SEED FUZZ_PROGRESS_EVERY
export COLLISIONS_COUNT COLLISIONS_START COLLISIONS_PROGRESS_EVERY TIMEOUT
export MAX_THREADS

EXPORTING := $(filter export export-zip zip,$(MAKECMDGOALS))
export EXPORTING
RUN = $(PYTHON) run_tests.py --exe "$$(cat "$(EXE_CACHE_FILE)")" --timeout "$(TIMEOUT)" --fail-log "$(FAIL_LOG)" --command-prefix "$(CMD_LIST_PREFIX)" $(if $(filter 1,$(FAIL)),--fail)
TOOLS = $(PYTHON) tools.py
TOOL_TESTS = $(if $(filter asan,$@),$(ASAN_MANUAL_TESTS),$(if $(filter valgrind,$@),$(VALGRIND_TESTS),$(if $(filter coverage,$@),$(COVERAGE_TESTS),$(TESTS))))
TOOL_OUTPUT = $(if $(filter asan,$@),$(ASAN_EXE),$(if $(filter valgrind,$@),$(VALGRIND_EXE),$(if $(filter analyse,$@),$(ANALYSE_EXE),$(if $(filter profile,$@),$(PROFILE_EXE),$(if $(filter coverage,$@),$(COVERAGE_EXE))))))

manual-tests: manual

exercise1: manual

exercise2 exercise3: resolve-exe
	@status=0; $(RUN) --fail-log "$(if $(filter exercise2,$@),$(EXERCISE2_FAIL_LOG),$(EXERCISE3_FAIL_LOG))" $(if $(filter exercise2,$@),$(EXERCISE2_TESTS),$(EXERCISE3_TESTS)) || status=$$?; \
	if [ $$status -ne 0 ] && [ -z "$(EXPORTING)" ] && [ "$(NO_PROMPT)" != 1 ] && [ -t 0 ]; then \
		read -r -p "Executar 'make show-diff' para ver as diferenças? (Y/n) " ans; [[ "$$ans" = [nN] ]] || $(MAKE) show-diff ONLY_MANUAL=1; \
	fi; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

all: resolve-exe
	@status=0; $(TOOLS) suites --exe "$$(cat "$(EXE_CACHE_FILE)")" --tests $(TESTS) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

python: resolve-exe
	@status=0; $(TOOLS) suites --exe "$$(cat "$(EXE_CACHE_FILE)")" --parts stress scale fuzz-parse scale-collisions --tests $(TESTS) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

manual: resolve-exe
	@status=0; $(RUN) $(TESTS) || status=$$?; \
	if [ $$status -ne 0 ] && [ -z "$(EXPORTING)" ] && [ "$(NO_PROMPT)" != 1 ] && [ -t 0 ]; then \
		read -r -p "Executar 'make show-diff' para ver as diferenças? (Y/n) " ans; [[ "$$ans" = [nN] ]] || $(MAKE) show-diff ONLY_MANUAL=1; \
	fi; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

quick:
	@$(MAKE) all EXPORTING="$(EXPORTING)" ORIG_GOALS=quick \
		STRESS_RUNS=8 STRESS_STEPS=120 STRESS_PROGRESS_EVERY=2 \
		SCALE_TYPES=8 SCALE_FILES=16 SCALE_PROGRESS_EVERY=0 FUZZ_CASES=40 FUZZ_LINES=120 \
		FUZZ_PROGRESS_EVERY=10 COLLISIONS_COUNT=20 COLLISIONS_PROGRESS_EVERY=0

resolve-exe:
	@$(TOOLS) resolve --exe "$(EXE)" --name "$(EXE_NAME)" --cache "$(EXE_CACHE_FILE)"

resolve-exe2:
	@$(TOOLS) resolve2 --exe "$(EXE2)" --name "$(EXE_NAME)" --cache "$(EXE2_CACHE_FILE)"

resolve-src:
	@$(TOOLS) resolve-src --exe "$(EXE)" --cache "$(EXE_CACHE_FILE)" --project "$(PROJECT_DIR)" --src-cache "$(SRC_CACHE_FILE)"

d r a l e: resolve-exe
	@status=0; $(RUN) --command $@ $(TESTS) || status=$$?; \
	if [ $$status -ne 0 ] && [ -z "$(EXPORTING)" ] && [ "$(NO_PROMPT)" != 1 ] && [ -t 0 ]; then \
		read -r -p "Executar 'make show-diff' para ver as diferenças? (Y/n) " ans; [[ "$$ans" = [nN] ]] || $(MAKE) show-diff ONLY_MANUAL=1; \
	fi; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

rerun: resolve-exe
	@status=0; $(TOOLS) rerun --exe "$$(cat "$(EXE_CACHE_FILE)")" --timeout "$(TIMEOUT)" --fail-log "$(FAIL_LOG)" $(if $(filter 1,$(FAIL)),--fail) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

compare: resolve-exe resolve-exe2
	@status=0; $(RUN) --exe2 "$$(cat "$(EXE2_CACHE_FILE)")" --fail-log "$(COMPARE_FAIL_LOG)" $(COMPARE_TESTS) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

stress: resolve-exe
	@status=0; $(PYTHON) random_stress.py --exe "$$(cat "$(EXE_CACHE_FILE)")" --runs $(STRESS_RUNS) --steps $(STRESS_STEPS) --seed $(STRESS_SEED) --timeout $(STRESS_TIMEOUT) --progress-every $(STRESS_PROGRESS_EVERY) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

scale: resolve-exe
	@status=0; $(PYTHON) scale_limits.py --exe "$$(cat "$(EXE_CACHE_FILE)")" --types $(SCALE_TYPES) --files $(SCALE_FILES) --timeout $(TIMEOUT) --progress-every $(SCALE_PROGRESS_EVERY) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

fuzz-parse: resolve-exe
	@status=0; $(PYTHON) fuzz_parse.py --exe "$$(cat "$(EXE_CACHE_FILE)")" --cases $(FUZZ_CASES) --max-lines $(FUZZ_LINES) --seed $(FUZZ_SEED) --timeout $(TIMEOUT) --progress-every $(FUZZ_PROGRESS_EVERY) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

scale-collisions: resolve-exe
	@status=0; $(PYTHON) scale_collisions.py --exe "$$(cat "$(EXE_CACHE_FILE)")" --count $(COLLISIONS_COUNT) --start $(COLLISIONS_START) --timeout $(TIMEOUT) --progress-every $(COLLISIONS_PROGRESS_EVERY) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

count:
	@$(TOOLS) count --stats "$(STATS_FILE)" --command-prefix "$(CMD_LIST_PREFIX)" --tests $(TESTS)

export:
	@$(TOOLS) export --fail-log "$(FAIL_LOG)" --compare-log "$(COMPARE_FAIL_LOG)" --stats "$(STATS_FILE)" $(if $(filter zip,$(MAKECMDGOALS)),--zip)

export-zip:
	@$(TOOLS) export --fail-log "$(FAIL_LOG)" --compare-log "$(COMPARE_FAIL_LOG)" --stats "$(STATS_FILE)" --zip

zip:
	@$(if $(filter export,$(MAKECMDGOALS)),:,$(TOOLS) export --fail-log "$(FAIL_LOG)" --compare-log "$(COMPARE_FAIL_LOG)" --stats "$(STATS_FILE)" --zip)

selftest:
	@$(PYTHON) -m unittest -v test_runner test_generated test_advanced

asan valgrind analyse profile lizard coverage: resolve-src
	@status=0; $(TOOLS) $@ --exe "$(EXE)" --cache "$(EXE_CACHE_FILE)" --project "$(PROJECT_DIR)" --src-cache "$(SRC_CACHE_FILE)" --output "$(TOOL_OUTPUT)" --test "$(TEST)" --timeout "$(TIMEOUT)" --fail-log "$(FAIL_LOG)" $(if $(filter 1,$(FAIL)),--fail) --tests $(TOOL_TESTS) || status=$$?; \
	if [ -n "$(EXPORTING)" ]; then exit 0; else exit $$status; fi

clean:
	rm -f *.diff *.myout *.stdout *.stderr *.expected *.status.json *.cmpdiff *.reason *.gmon profile_*.txt coverage_report.txt coverage_report.gcov test_summary.txt *.gcno *.gcda *.gcov "$(FAIL_LOG)" "$(COMPARE_FAIL_LOG)" "$(STATS_FILE)"
	rm -rf coverage stress-failures scale-failures fuzz-failures collisions-failures .build
	@for directory in exercise2 exercise3; do if [ -d "$$directory" ]; then \
		find "$$directory" -type f \( -name '*.diff' -o -name '*.myout' -o -name '*.stdout' -o -name '*.stderr' -o -name '*.expected' -o -name '*.status.json' -o -name '*.cmpdiff' -o -name '*.reason' -o -name '*.gmon' -o -name '*.log' \) -delete; \
	fi; done

define PRETTY_DIFF_PY
import sys, os, glob, shutil, json, subprocess
from difflib import SequenceMatcher
R,RED,GRN,YEL,CYN,BLD = "\033[0m","\033[31m","\033[32m","\033[33m","\033[36m","\033[1m"
BYLW,BRED,DIM = "\033[1;33m","\033[1;31m","\033[2m"
BGRED,BGGRN = "\033[48;5;52m","\033[48;5;22m"
SEP = f"{BYLW}{'═'*60}{R}"
THIN = f"{DIM}{'─'*60}{R}"
def print_header(title, subtitle=None):
    print(); print(SEP); print(f"{BRED}  ✗ {title}{R}")
    if subtitle: print(f"{CYN}  {subtitle}{R}")
    print(SEP); print()
def print_description(p):
    if not os.path.isfile(p): return
    with open(p) as f: lines = f.read().strip().split("\n")
    for l in lines: print(f"{DIM}  │ {l}{R}")
    print(THIN)
def highlight_inline(a, b, w):
    at, bt = a[:w-1] if len(a)>w else a, b[:w-1] if len(b)>w else b
    sm = SequenceMatcher(None, at, bt)
    ep, ap = [], []
    for op,i1,i2,j1,j2 in sm.get_opcodes():
        if op=="equal": ep.append(at[i1:i2]); ap.append(bt[j1:j2])
        elif op=="replace": ep.append(f"{BGGRN}{BLD}{at[i1:i2]}{R}"); ap.append(f"{BGRED}{BLD}{bt[j1:j2]}{R}")
        elif op=="delete": ep.append(f"{BGGRN}{BLD}{at[i1:i2]}{R}"); ap.append(f"{BGRED}{DIM}{' ' * (i2-i1)}{R}")
        elif op=="insert": ap.append(f"{BGRED}{BLD}{bt[j1:j2]}{R}")
    if len(a)>w: ep.append(f"{DIM}…{R}")
    if len(b)>w: ap.append(f"{DIM}…{R}")
    return "".join(ep), "".join(ap)
def show_input_context(in_path, first_diff_line, output_lines):
    if not os.path.isfile(in_path): return
    with open(in_path) as f: cmds = f.read().splitlines()
    if not cmds: return
    events = [i for i, line in enumerate(cmds) if line.strip() == "L" or line.startswith("# COPY:")]
    outputs = [i for i, line in enumerate(output_lines) if "DATA CENTER STATUS" in line or line.startswith("COPY ")]
    event = max(0, sum(i <= first_diff_line for i in outputs) - 1)
    idx = events[min(event, len(events)-1)] if events else min(first_diff_line, len(cmds)-1)
    end = min(len(cmds), idx+2)
    print(f"\n  {YEL}{BLD}Comandos até à primeira diferença ({R}linha de output {first_diff_line+1}{YEL}{BLD}):{R}")
    indexes = list(range(end)) if end <= 8 else [0, 1, 2, *range(max(3, idx-2), end)]
    for position, i in enumerate(indexes):
        if position == 3 and i > 3: print(f"  {DIM}       ... (mais {i-3} comandos) ...{R}")
        if i == idx: print(f"  {BRED}▸ {i+1:>3}: {cmds[i]}{R}")
        else: print(f"  {DIM}  {i+1:>3}: {cmds[i]}{R}")
def sbs(exp_path, act_path, in_path=None):
    if not os.path.isfile(exp_path) or not os.path.isfile(act_path): return
    with open(exp_path) as f: el = f.read().splitlines()
    with open(act_path) as f: al = f.read().splitlines()
    total = max(len(el), len(al))
    if total == 0: return
    tw = shutil.get_terminal_size((100,24)).columns
    lw = len(str(total))+1
    max_line = max((len(l) for l in el+al), default=0)
    cw = max(min(max_line + 4, (tw-lw-10)//2), 15)
    print(f"  {DIM}{' '*lw} │{R} {CYN}Esperado (.out){' '*(cw-15)}{R}     {YEL}Obtido (.myout){R}")
    print(f"  {DIM}{' '*lw} │ {'─'*cw}  ─  {'─'*cw}{R}")
    # Pre-compute which lines differ
    diffs = []
    for i in range(total):
        e = el[i] if i<len(el) else None
        a = al[i] if i<len(al) else None
        diffs.append(e != a)
    dc = 0; first_diff = None; skip_count = 0; ctx = 2  # context lines around diffs
    def trunc(s): return (s[:cw-1]+"…" if len(s)>cw else s)
    for i in range(total):
        e = el[i] if i<len(el) else ""; a = al[i] if i<len(al) else ""
        ln = f"{i+1:>{lw}}"
        # Check if this line is near a diff (within ctx lines)
        near_diff = any(diffs[j] for j in range(max(0,i-ctx), min(total,i+ctx+1)))
        if e == a and not near_diff and total > 20:
            skip_count += 1
            continue
        if skip_count > 0:
            print(f"  {DIM}{'·':>{lw}} │ {'':^{cw}}  ·  ... {skip_count} linhas iguais ...{R}")
            skip_count = 0
        if e == a:
            t = trunc(e)
            print(f"  {DIM}{ln} │ {t:<{cw}}  ·  {t}{R}")
        else:
            if first_diff is None: first_diff = i
            dc += 1; mk = f"{BRED}≠{R}"
            if i>=len(el):
                ep2 = f"{BGGRN}    {R}"; ap2 = f"{BGRED}{BLD}{trunc(a)}{R}"; pad = cw-4
            elif i>=len(al):
                ep2 = f"{BGGRN}{BLD}{trunc(e)}{R}"; ap2 = f"{BGRED}    {R}"; pad = cw-min(len(e),cw)
            else:
                ep2, ap2 = highlight_inline(e, a, cw); pad = cw-min(len(e),cw)
            print(f"  {BYLW}{ln}{R} │ {ep2}{' '*pad}  {mk}  {ap2}")
    if skip_count > 0:
        print(f"  {DIM}{'·':>{lw}} │ {'':^{cw}}  ·  ... {skip_count} linhas iguais ...{R}")
    print()
    if dc: print(f"  {BYLW}{dc}{R} linha(s) difere(m)  (esperado: {len(el)}, obtido: {len(al)})")
    if first_diff is not None and in_path:
        show_input_context(in_path, first_diff, el)
found = False
interactive = sys.stdin.isatty() and os.environ.get("NO_PROMPT") != "1"
only_manual = os.environ.get("ONLY_MANUAL") == "1"
fail_log = os.environ.get("FAIL_LOG", "tests_failed.log")
if os.path.isfile(fail_log):
    with open(fail_log) as f: bases = [line.strip().removesuffix(".in") for line in f if line.strip()]
    diff_files = [base + ".diff" for base in bases if os.path.isfile(base + ".diff")]
else:
    diff_files = [f for f in sorted(glob.glob("test*.diff")) if f.count(".") == 1]
for directory in ("exercise2", "exercise3"):
    logfile = os.path.join(directory,"tests_failed.log")
    if os.path.isfile(logfile):
        with open(logfile) as f: names = [line.strip() for line in f if line.strip()]
        for name in names:
            base = os.path.join(directory,name) if not os.path.dirname(name) else name
            path = base.removesuffix(".in") + ".diff"
            if os.path.isfile(path) and path not in diff_files: diff_files.append(path)
python_diffs = []
for directory in (() if only_manual else ("stress-failures", "scale-failures", "fuzz-failures", "collisions-failures")):
    logfile = os.path.join(directory, "tests_failed.log")
    if os.path.isfile(logfile):
        with open(logfile) as f: names = [line.strip() for line in f if line.strip()]
        for name in names:
            base = os.path.join(directory, name) if os.path.dirname(name) == "" else name
            path = base.removesuffix(".in") + ".diff"
            if os.path.isfile(path) and path not in diff_files: python_diffs.append(path)
manual_count = len(diff_files)
diff_files += python_diffs
for n, df in enumerate(diff_files, 1):
    if n == manual_count+1 and manual_count and python_diffs and interactive:
        sys.stderr.write(f"\n  {BRED}Existem falhas nos testes em Python.{R} Ver as diferenças? (y/N) ")
        try: answer = input().strip().lower()
        except EOFError: answer = "n"
        if answer != "y": break
    found = True; base = df.rsplit(".diff",1)[0]
    print_header(f"{base} FAILED ({n})"); print_description(f"{base}.txt")
    status = f"{base}.status.json"
    if os.path.isfile(status):
        with open(status) as f: meta = json.load(f)
        print(f"  Código de saída: {meta['returncode']} | Timeout: {meta['timed_out']} | Duração: {meta['elapsed']:.3f}s")
        for reason in meta["reasons"]: print(f"  {RED}{reason}{R}")
    else:
        with open(df) as f: print(f.read())
    sbs(f"{base}.expected" if os.path.isfile(f"{base}.expected") else f"{base}.out", f"{base}.myout", f"{base}.in")
    stderr_path = f"{base}.stderr"
    if os.path.isfile(stderr_path):
        with open(stderr_path) as f: error_text = f.read().strip()
        if error_text:
            print(f"\n  {YEL}Stderr:{R}")
            for line in error_text.splitlines()[:10]: print(f"  {RED}{line}{R}")
compare_log = os.environ.get("COMPARE_FAIL_LOG", "compare_failed.log")
if os.path.isfile(compare_log):
    with open(compare_log) as f: compare_files = [line.strip().removesuffix(".in") + ".cmpdiff" for line in f if line.strip()]
else:
    compare_files = sorted(glob.glob("test*.cmpdiff"))
for df in ([] if only_manual else compare_files):
    if not os.path.isfile(df): continue
    found = True
    print_header(df.removesuffix(".cmpdiff") + " — comparação")
    with open(df) as f: print(f.read())

if not found: print("Não há diffs para mostrar. Todos os testes passaram ou ainda não foram executados.")
else:
    if interactive: sys.stderr.write(f"\n  {CYN}Executar 'make analyse' ? (y/N){R} ")
    try: ans = input().strip().lower() if interactive else "n"
    except EOFError: ans = "n"

    if ans == "y":
        while True:
            sys.stderr.write(f"  {DIM}Indica o ID ou caminho do teste (ou 'q' para sair): {R}")
            try: test = input().strip()
            except EOFError: break

            if not test or test.lower() in ("q", "n", "sair", "exit"): break
            real_id = test
            if test.isdigit(): real_id = f"test{int(test):03d}.in"
            elif not test.endswith(".in"): real_id = f"{test}.in"

            while True:
                sys.stderr.write(f"  {DIM}Alvo: {real_id}{R}\n  O que pretendes lançar? [d] Debugger | [p] Profiler | [c] Voltar | [q] Sair\n  > ")
                try: action = input().strip().lower()
                except EOFError: action = "q"

                if not action or action == "d":
                    tgt = "analyse"; break
                elif action == "p":
                    tgt = "profile"; break
                elif action == "c":
                    tgt = "voltar"; break
                elif action in ("q", "sair", "n", "exit"):
                    sys.exit(0)
                else:
                    sys.stderr.write(f"  {RED}Opção inválida.{R}\n")

            if tgt == "voltar":
                continue

            if tgt:
                sys.stderr.write(f"\n  {YEL}A iniciar o alvo '{tgt}' para {real_id}...{R}\n")
                subprocess.run(["make", "-s", tgt, f"TEST={real_id}"])
    print()
endef
export PRETTY_DIFF_PY

show-diff:
	@$(PYTHON) -c "$$PRETTY_DIFF_PY"

help:
	@printf '%s\n' \
	  '' \
	  '  Makefile — Suite de testes SO' \
	  '  ============================' \
	  '' \
	  'Comandos principais:' \
	  'make / make manual-tests      Testes manuais' \
	  'make exercise1                Exercício 1: 79 casos (50 novos)' \
	  'make exercise2                Exercício 2: 50 casos de processos e limites' \
	  'make exercise3                Exercício 3: 50 casos de ficheiros concorrentes' \
	  'make all                      Manual + stress + escala + fuzz + colisões' \
	  'make quick                    Todas as suites com limites reduzidos' \
	  'make python                   Apenas stress + escala + fuzz + colisões' \
	  'make asan                    ASAN/UBSan: manual + fuzz + colisões' \
	  '' \
	  'Scripts Python individuais:' \
	  'make stress                   Sequências aleatórias com modelo de referência' \
	  'make scale                    Muitos tipos, reservas e ficheiros .conf' \
	  'make fuzz-parse               Robustez com sintaxe inválida (exploratório)' \
	  'make scale-collisions         Identificadores semelhantes de 39 caracteres' \
	  '' \
	  'Testes por comando:' \
	  'make d|r|a|l|e               Seleção por comando; aceita comando_*.txt' \
	  '' \
	  'Comparação e estatísticas:' \
	  'make compare EXE2=path       Compara executáveis, stderr e códigos de saída' \
	  'make count                   Estatísticas e estado das suites Python' \
	  '' \
	  'Exportação:' \
	  'make export / export-zip     Exporta falhas manuais e geradas, com diagnósticos' \
	  'make export zip              Exporta e cria ZIP (equivalente a export-zip)' \
	  'make all count export-zip    Corre tudo e exporta mesmo se houver falhas' \
	  '' \
	  'Utilidades & Depuração (Debug):' \
	  'make rerun                   Repete falhas manuais e geradas' \
	  'make show-diff               Diferenças a cores + assistente de depuração' \
	  'make analyse TEST=007        Compila com -g -O0 e abre LLDB/GDB' \
	  'make profile TEST=007        Compila com -pg e gera relatório gprof' \
	  'make valgrind                Compila com símbolos e verifica leaks' \
	  'make coverage                Cobertura gcov e linhas não executadas' \
	  'make lizard                  Complexidade dos fontes C' \
	  'make selftest                Testa o executor, os geradores e o Makefile' \
	  'make clean                   Limpa resultados, falhas geradas e .build/' \
	  'make help                    Mostra esta ajuda' \
	  '' \
	  'Variáveis úteis:' \
	  'EXE=path / EXE2=path          Executável ou pasta de cloudIST (memorizados)' \
	  'PROJECT_DIR=path              Fontes; ASAN_SRC e SRC_CACHE_FILE também aceites' \
	  'TESTS="test004.in test007.in"  Seleção de casos, incluindo *-failures/*.in' \
	  'FAIL=1 / TIMEOUT=5            Para na primeira falha / limite por teste' \
	  'STRESS_RUNS / STRESS_STEPS / STRESS_SEED / STRESS_TIMEOUT / STRESS_PROGRESS_EVERY' \
	  'SCALE_TYPES=96 / SCALE_FILES=200 (máximos do código base: 128 / 256)' \
	  'SCALE_PROGRESS_EVERY / FUZZ_CASES / FUZZ_LINES / FUZZ_SEED / FUZZ_PROGRESS_EVERY' \
	  'COLLISIONS_COUNT=120 / COLLISIONS_START=1000000' \
	  'COLLISIONS_PROGRESS_EVERY / ORIG_GOALS (cabeçalho da tabela)' \
	  'ASAN_MANUAL_TESTS / ASAN_FUZZ_CASES / ASAN_FUZZ_LINES / ASAN_COLLISIONS_COUNT' \
	  'VALGRIND_TESTS / COVERAGE_TESTS / CMD_LIST_PREFIX / AUTO_ZIP / NO_PROMPT' \
	  'ONLY_MANUAL=1                Mostra apenas diferenças manuais em show-diff' \
	  'MAX_THREADS=N               Acrescenta o argumento de threads aos casos dos exercícios 1/2' \
	  'EXERCISE2_TESTS / EXERCISE3_TESTS  Seleção dos casos dos novos alvos' \
	  'ASAN_EXE / VALGRIND_EXE / ANALYSE_EXE / PROFILE_EXE / COVERAGE_EXE'
