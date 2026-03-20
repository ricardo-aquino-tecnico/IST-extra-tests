.SUFFIXES: .in .out .diff
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DEFAULT_GOAL := manual-tests
.PHONY: all quick manual manual-tests resolve-exe resolve-src python stress scale fuzz-parse scale-collisions asan clean p l a r f c d
OK="\e[1;32mtest $< PASSED\e[0m"
KO="\e[1;31mtest $< FAILED\e[0m"
FAIL=0
EXE ?=
EXE_NAME ?= proj
EXE_CACHE_FILE ?= .resolved_exe
LOG=tests.log
FAIL_LOG=tests_failed.log
TESTS ?= $(sort $(wildcard test*.in))
CMD_LIST_PREFIX ?= comando_
STRESS_RUNS ?= 1000
STRESS_STEPS ?= 1250
STRESS_SEED ?= $(shell date +%s)
STRESS_PROGRESS_EVERY ?= 25
STRESS_TIMEOUT ?= 8
SCALE_PRODUCTS ?= 10000
SCALE_INVOICES ?= 100001
SCALE_PROGRESS_EVERY ?= 20000
FUZZ_CASES ?= 1200
FUZZ_LINES ?= 900
FUZZ_SEED ?= $(shell date +%s)
FUZZ_PROGRESS_EVERY ?= 50
COLLISIONS_COUNT ?= 200
COLLISIONS_START ?= 1000000
COLLISIONS_PROGRESS_EVERY ?= 500000
ASAN_EXE ?= ../proj_asan
ASAN_SRC ?= ../../project.c
SRC_CACHE_FILE ?= .resolved_src
ASAN_MANUAL_TESTS ?= $(TESTS)
ASAN_FUZZ_CASES ?= 150
ASAN_FUZZ_LINES ?= 180
ASAN_COLLISIONS_COUNT ?= 120
STATUS_TABLE_FUNC = \
print_status_table() { \
	arg_col_width=62; \
	status_header="$$1"; \
	shift; \
	printf "+------------------+------------------+----------------------------------------------------------------+\n"; \
	printf "| %-16s | %-16s | %-62s |\n" "Test Part" "$$status_header" "Arguments"; \
	printf "+------------------+------------------+----------------------------------------------------------------+\n"; \
	while [ -n "$$1" ] && [ -n "$$2" ] && [ -n "$$3" ]; do \
		part="$$1"; \
		status="$$2"; \
		args="$$3"; \
		if [ "$$args" = "-" ]; then \
			arg1="-"; \
			arg2=""; \
			arg3=""; \
		else \
			wrapped="$$(printf '%s' "$$args" | fold -s -w $$arg_col_width)"; \
			arg1="$$(printf '%s\n' "$$wrapped" | sed -n '1p')"; \
			arg2="$$(printf '%s\n' "$$wrapped" | sed -n '2p')"; \
			arg3="$$(printf '%s\n' "$$wrapped" | sed -n '3p')"; \
			if [ -n "$$arg3" ]; then \
				arg2="$${arg2:0:59}..."; \
			fi; \
		fi; \
		printf "| %-16s | %-16s | %-62s |\n" "$$part" "$$status" "$$arg1"; \
		if [ -n "$$arg2" ]; then \
			printf "| %-16s | %-16s | %-62s |\n" "" "" "$$arg2"; \
		fi; \
		shift 3; \
	done; \
	printf "+------------------+------------------+----------------------------------------------------------------+\n"; \
}; \
now_ms() { \
	python3 -c 'import time; print(int(time.time() * 1000))'; \
}; \

all:
	@$(STATUS_TABLE_FUNC) \
	manual_status="FAIL"; stress_status="FAIL"; scale_status="FAIL"; fuzz_status="FAIL"; collisions_status="FAIL"; \
	manual_time="-"; stress_time="-"; scale_time="-"; fuzz_time="-"; collisions_time="-"; \
	manual_ms=0; stress_ms=0; scale_ms=0; fuzz_ms=0; collisions_ms=0; \
	total=5; passed=0; failed=0; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) manual; then manual_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); manual_ms="$$(($$t1 - $$t0))"; manual_time="$${manual_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) stress; then stress_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); stress_ms="$$(($$t1 - $$t0))"; stress_time="$${stress_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) scale; then scale_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); scale_ms="$$(($$t1 - $$t0))"; scale_time="$${scale_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) fuzz-parse; then fuzz_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); fuzz_ms="$$(($$t1 - $$t0))"; fuzz_time="$${fuzz_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) scale-collisions; then collisions_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); collisions_ms="$$(($$t1 - $$t0))"; collisions_time="$${collisions_ms}ms"; \
	sum_ms=$$((manual_ms + stress_ms + scale_ms + fuzz_ms + collisions_ms)); \
	status_header="Status ($${sum_ms}ms)"; \
	stress_args="runs $(STRESS_RUNS) steps $(STRESS_STEPS) seed $(STRESS_SEED) progress-every $(STRESS_PROGRESS_EVERY) timeout $(STRESS_TIMEOUT)"; \
	scale_args="products $(SCALE_PRODUCTS) invoices $(SCALE_INVOICES) progress-every $(SCALE_PROGRESS_EVERY)"; \
	fuzz_args="cases $(FUZZ_CASES) max-lines $(FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "All tests summary:"; \
	print_status_table \
		"$$status_header" \
		"manual" "$$manual_status $$manual_time" "-" \
		"stress" "$$stress_status $$stress_time" "$$stress_args" \
		"scale" "$$scale_status $$scale_time" "$$scale_args" \
		"fuzz-parse" "$$fuzz_status $$fuzz_time" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status $$collisions_time" "$$collisions_args"; \
	echo ""; \
	if [ "$$manual_status" = "PASS" ]; then \
		echo "Manual tests Passed"; \
	elif [ -s "$(FAIL_LOG)" ]; then \
		echo "Manual failed tests:"; \
		while IFS= read -r t; do printf "%s\n" "$$t"; done < "$(FAIL_LOG)"; \
	else \
		echo "Manual suite failed before per-test execution"; \
	fi; \
	echo "$$passed/$$total parts passed, $$failed/$$total parts failed"; \
	test $$failed -eq 0

quick:
	@$(MAKE) $(MFLAGS) all \
		STRESS_RUNS=8 STRESS_STEPS=120 STRESS_PROGRESS_EVERY=2 \
		SCALE_PRODUCTS=500 SCALE_INVOICES=1200 SCALE_PROGRESS_EVERY=0 \
		FUZZ_CASES=40 FUZZ_LINES=120 FUZZ_PROGRESS_EVERY=10 \
		COLLISIONS_COUNT=20 COLLISIONS_PROGRESS_EVERY=0

manual: clean resolve-exe
	@rm -f $(LOG) $(FAIL_LOG)
	@touch $(LOG)
	@touch $(FAIL_LOG)
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	for i in $(TESTS); do \
		base=$${i%.in}; \
		if [ -f "$$base.arg" ]; then "$$exe" `cat "$$base.arg"` < "$$i" > "$$base.myout"; else "$$exe" < "$$i" > "$$base.myout"; fi; \
		if [ -f "$$base.out" ]; then diff "$$base.myout" "$$base.out" > "$$base.diff" || :; \
		else rm -f "$$base.diff"; echo "diff: $$base.out: No such file or directory"; fi; \
		if [ ! -f "$$base.diff" ] || [ `wc -l < "$$base.diff"` -eq 0 ]; then \
			echo -e "\e[1;32mtest $$i PASSED\e[0m"; echo "$$base" >> "$(LOG)"; \
		else \
			echo -e "\e[1;31mtest $$i FAILED\e[0m"; echo "$$i" >> "$(FAIL_LOG)"; \
			if [ $(FAIL) -eq 1 ]; then exit 1; fi; \
		fi; \
	done
	@total=`echo "$(TESTS)" | wc -w`; \
	passed=`wc -l < $(LOG)`; \
	failed=`expr $$total - $$passed`; \
	echo "$$passed tests passed, $$failed tests failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "Manual suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		exit 1; \
	else \
		echo "Manual suite PASSED."; \
	fi

manual-tests: manual

resolve-exe:
	@if [ -n "$(EXE)" ]; then \
		if [ -x "$(EXE)" ]; then \
			resolved="$(EXE)"; \
		else \
			echo "EXE path is not executable: $(EXE)"; \
			exit 1; \
		fi; \
	elif [ -s "$(EXE_CACHE_FILE)" ] && [ -x "$$(cat "$(EXE_CACHE_FILE)")" ]; then \
		resolved="$$(cat "$(EXE_CACHE_FILE)")"; \
	elif [ -x "../$(EXE_NAME)" ]; then \
		resolved="../$(EXE_NAME)"; \
	elif [ -x "../../$(EXE_NAME)" ]; then \
		resolved="../../$(EXE_NAME)"; \
	else \
		if [ ! -t 0 ]; then \
			echo "Projeto '$(EXE_NAME)' nao foi encontrado em ../ nem ../../ and stdin is not interactive."; \
			echo "Pass EXE=/path/to/executable or set a valid $(EXE_CACHE_FILE)."; \
			exit 1; \
		fi; \
		echo "Projeto '$(EXE_NAME)' nao foi encontrado em ../ nem ../../."; \
		read -r -p "Indica o diretorio do projeto ou o caminho do executavel: " input; \
		while true; do \
			if [ -x "$$input" ]; then resolved="$$input"; break; fi; \
			if [ -x "$$input/$(EXE_NAME)" ]; then resolved="$$input/$(EXE_NAME)"; break; fi; \
			read -r -p "Nao encontrado. Indica outro diretorio ou executavel: " input; \
		done; \
	fi; \
	echo "$$resolved" > "$(EXE_CACHE_FILE)"

resolve-src:
	@if [ -n "$(ASAN_SRC)" ] && [ -f "$(ASAN_SRC)" ]; then \
		resolved="$(ASAN_SRC)"; \
	elif [ -s "$(SRC_CACHE_FILE)" ] && [ -f "$$(cat "$(SRC_CACHE_FILE)")" ]; then \
		resolved="$$(cat "$(SRC_CACHE_FILE)")"; \
	elif [ -f "../../project.c" ]; then \
		resolved="../../project.c"; \
	elif [ -f "../project.c" ]; then \
		resolved="../project.c"; \
	else \
		if [ ! -t 0 ]; then \
			echo "project.c nao foi encontrado em ../../ nem ../ and stdin is not interactive."; \
			echo "Pass ASAN_SRC=/path/to/project.c or set a valid $(SRC_CACHE_FILE)."; \
			exit 1; \
		fi; \
		echo "project.c nao foi encontrado em ../../ nem ../."; \
		read -r -p "Indica o diretorio do projeto ou o caminho do ficheiro .c: " input; \
		while true; do \
			if [ -f "$$input" ]; then resolved="$$input"; break; fi; \
			if [ -f "$$input/project.c" ]; then resolved="$$input/project.c"; break; fi; \
			read -r -p "Nao encontrado. Indica outro diretorio ou ficheiro .c: " input; \
		done; \
	fi; \
	echo "$$resolved" > "$(SRC_CACHE_FILE)"

p l a r f c d:
	@cmd_file="$(CMD_LIST_PREFIX)$@.txt"; \
	if [ ! -f "$$cmd_file" ]; then \
		alt_file="comando $@.txt"; \
		if [ -f "$$alt_file" ]; then \
			cmd_file="$$alt_file"; \
		else \
			echo "No command list file found for '$@' (tried '$$cmd_file' and '$$alt_file')"; \
			exit 1; \
		fi; \
	fi; \
	tests=$$(sed -e 's/#.*//' -e '/^[[:space:]]*$$/d' "$$cmd_file" | tr '\n' ' '); \
	if [ -z "$$tests" ]; then \
		echo "No tests listed for command '$@' in '$$cmd_file'"; \
		exit 1; \
	fi; \
	echo "Running tests for command '$@' using '$$cmd_file'"; \
	$(MAKE) $(MFLAGS) manual TESTS="$$tests" EXE_CACHE_FILE="$(EXE_CACHE_FILE)"

python:
	@$(STATUS_TABLE_FUNC) \
	stress_status="FAIL"; scale_status="FAIL"; fuzz_status="FAIL"; collisions_status="FAIL"; \
	stress_time="-"; scale_time="-"; fuzz_time="-"; collisions_time="-"; \
	stress_ms=0; scale_ms=0; fuzz_ms=0; collisions_ms=0; \
	total=4; passed=0; failed=0; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) stress; then stress_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); stress_ms="$$(($$t1 - $$t0))"; stress_time="$${stress_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) scale; then scale_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); scale_ms="$$(($$t1 - $$t0))"; scale_time="$${scale_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) fuzz-parse; then fuzz_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); fuzz_ms="$$(($$t1 - $$t0))"; fuzz_time="$${fuzz_ms}ms"; \
	t0=$$(now_ms); \
	if $(MAKE) $(MFLAGS) scale-collisions; then collisions_status="PASS"; passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	t1=$$(now_ms); collisions_ms="$$(($$t1 - $$t0))"; collisions_time="$${collisions_ms}ms"; \
	sum_ms=$$((stress_ms + scale_ms + fuzz_ms + collisions_ms)); \
	status_header="Status ($${sum_ms}ms)"; \
	stress_args="runs $(STRESS_RUNS) steps $(STRESS_STEPS) seed $(STRESS_SEED) progress-every $(STRESS_PROGRESS_EVERY) timeout $(STRESS_TIMEOUT)"; \
	scale_args="products $(SCALE_PRODUCTS) invoices $(SCALE_INVOICES) progress-every $(SCALE_PROGRESS_EVERY)"; \
	fuzz_args="cases $(FUZZ_CASES) max-lines $(FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "Python suite summary:"; \
	print_status_table \
		"$$status_header" \
		"stress" "$$stress_status $$stress_time" "$$stress_args" \
		"scale" "$$scale_status $$scale_time" "$$scale_args" \
		"fuzz-parse" "$$fuzz_status $$fuzz_time" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status $$collisions_time" "$$collisions_args"; \
	echo "$$passed/$$total parts passed, $$failed/$$total parts failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "Python suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		exit 1; \
	else \
		echo "Python suite PASSED."; \
	fi

stress: resolve-exe
	@echo "stress seed: $(STRESS_SEED)"
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	python3 random_stress.py --exe "$$exe" --runs $(STRESS_RUNS) --steps $(STRESS_STEPS) --seed $(STRESS_SEED) --progress-every $(STRESS_PROGRESS_EVERY) --timeout $(STRESS_TIMEOUT) && \
	echo "1 stress test passed, 0 stress tests failed" || \
	{ echo "0 stress tests passed, 1 stress tests failed"; exit 1; }

scale: resolve-exe
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	python3 scale_limits.py --exe "$$exe" --products $(SCALE_PRODUCTS) --invoices $(SCALE_INVOICES) --progress-every $(SCALE_PROGRESS_EVERY) && \
	echo "1 scale test passed, 0 scale tests failed" || \
	{ echo "0 scale tests passed, 1 scale tests failed"; exit 1; }

fuzz-parse: resolve-exe
	@echo "fuzz seed: $(FUZZ_SEED)"
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	python3 fuzz_parse.py --exe "$$exe" --cases $(FUZZ_CASES) --max-lines $(FUZZ_LINES) --seed $(FUZZ_SEED) --progress-every $(FUZZ_PROGRESS_EVERY) && \
	echo "1 fuzz-parse test passed, 0 fuzz-parse tests failed" || \
	{ echo "0 fuzz-parse tests passed, 1 fuzz-parse tests failed"; exit 1; }

scale-collisions: resolve-exe
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	python3 scale_collisions.py --exe "$$exe" --count $(COLLISIONS_COUNT) --start $(COLLISIONS_START) --progress-every $(COLLISIONS_PROGRESS_EVERY) && \
	echo "1 scale-collisions test passed, 0 scale-collisions tests failed" || \
	{ echo "0 scale-collisions tests passed, 1 scale-collisions tests failed"; exit 1; }

asan: resolve-src
	@src=$$(cat "$(SRC_CACHE_FILE)"); \
	gcc -fsanitize=address,undefined -fno-omit-frame-pointer -g -O1 -Wall -Wextra -Werror -Wno-unused-result -o $(ASAN_EXE) "$$src"
	@$(STATUS_TABLE_FUNC) \
	manual_status="FAIL"; fuzz_status="FAIL"; collisions_status="FAIL"; \
	manual_time="-"; fuzz_time="-"; collisions_time="-"; \
	manual_ms=0; fuzz_ms=0; collisions_ms=0; \
	total=3; passed=0; failed=0; \
	t0=$$(now_ms); \
	if ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
		$(MAKE) EXE="$(ASAN_EXE)" EXE_CACHE_FILE=".resolved_exe_asan" manual TESTS="$(ASAN_MANUAL_TESTS)"; then \
		manual_status="PASS"; passed=$$((passed + 1)); \
	else \
		failed=$$((failed + 1)); \
	fi; \
	t1=$$(now_ms); manual_ms="$$(($$t1 - $$t0))"; manual_time="$${manual_ms}ms"; \
	t0=$$(now_ms); \
	if ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
		python3 fuzz_parse.py --exe $(ASAN_EXE) --cases $(ASAN_FUZZ_CASES) --max-lines $(ASAN_FUZZ_LINES) --seed $(FUZZ_SEED) --progress-every $(FUZZ_PROGRESS_EVERY); then \
		fuzz_status="PASS"; passed=$$((passed + 1)); \
	else \
		failed=$$((failed + 1)); \
	fi; \
	t1=$$(now_ms); fuzz_ms="$$(($$t1 - $$t0))"; fuzz_time="$${fuzz_ms}ms"; \
	t0=$$(now_ms); \
	if ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
		python3 scale_collisions.py --exe $(ASAN_EXE) --count $(ASAN_COLLISIONS_COUNT) --start $(COLLISIONS_START) --progress-every $(COLLISIONS_PROGRESS_EVERY); then \
		collisions_status="PASS"; passed=$$((passed + 1)); \
	else \
		failed=$$((failed + 1)); \
	fi; \
	t1=$$(now_ms); collisions_ms="$$(($$t1 - $$t0))"; collisions_time="$${collisions_ms}ms"; \
	sum_ms=$$((manual_ms + fuzz_ms + collisions_ms)); \
	status_header="Status ($${sum_ms}ms)"; \
	fuzz_args="cases $(ASAN_FUZZ_CASES) max-lines $(ASAN_FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(ASAN_COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "ASAN suite summary:"; \
	print_status_table \
		"$$status_header" \
		"manual" "$$manual_status $$manual_time" "-" \
		"fuzz-parse" "$$fuzz_status $$fuzz_time" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status $$collisions_time" "$$collisions_args"; \
	echo "$$passed/$$total parts passed, $$failed/$$total parts failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "ASAN suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		exit 1; \
	else \
		echo "ASAN suite PASSED."; \
	fi

.in.diff:
	@-if [ -f $*.arg ]; then "$(EXE)" `cat $*.arg` < $< > $*.myout; else "$(EXE)" < $< > $*.myout; fi
	@-diff $*.myout $*.out > $@ ||:
	@if [ `wc -l < $@` -eq 0 ]; then echo -e $(OK); echo $* >> $(LOG); else echo -e $(KO); if [ $(FAIL) -eq 1 ]; then false; fi; fi;

clean::
	rm -rf *.diff *.myout $(LOG) $(FAIL_LOG)
