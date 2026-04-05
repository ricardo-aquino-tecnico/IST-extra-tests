MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DEFAULT_GOAL := manual-tests
.PHONY: all quick manual manual-tests resolve-exe resolve-src python stress scale fuzz-parse scale-collisions asan clean p l a r f c d export export-zip zip compare count rerun show-diff valgrind lizard coverage help

FAIL=0
EXE ?=
EXE_NAME ?= proj
EXE_CACHE_FILE ?= .resolved_exe

FAIL_LOG=tests_failed.log
COMPARE_FAIL_LOG=compare_failed.log
STATS_FILE=test_stats.txt
TESTS ?= $(sort $(wildcard test*.in))
ORIG_GOALS ?= $(if $(MAKECMDGOALS),$(MAKECMDGOALS),$(.DEFAULT_GOAL))

ifeq ($(filter zip,$(MAKECMDGOALS)),zip)
AUTO_ZIP := 1
endif
ifneq ($(filter export export-zip zip,$(MAKECMDGOALS)),)
EXPORTING := 1
endif

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
VALGRIND_EXE ?= ../proj_valgrind
VALGRIND_TESTS ?= $(TESTS)
COVERAGE_EXE ?= ../proj_coverage
COVERAGE_TESTS ?= $(TESTS)
STATUS_TABLE_FUNC = \
print_status_table() { \
	arg_col_width=46; \
	status_header="$$1"; \
	shift; \
	arg_header="Arguments ($(ORIG_GOALS))"; \
	printf "+------------------+----------------------------+------------------------------------------------+\n"; \
	printf "| %-16s | %-26s | %-46s |\n" "Test Part" "$$status_header" "$$arg_header"; \
	printf "+------------------+----------------------------+------------------------------------------------+\n"; \
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
				arg2="$${arg2:0:43}..."; \
			fi; \
		fi; \
		printf "| %-16s | %-26s | %-46s |\n" "$$part" "$$status" "$$arg1"; \
		if [ -n "$$arg2" ]; then \
			printf "| %-16s | %-26s | %-46s |\n" "" "" "$$arg2"; \
		fi; \
		shift 3; \
	done; \
	printf "+------------------+----------------------------+------------------------------------------------+\n"; \
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
	manual_tests_total=$$(echo "$(TESTS)" | wc -w | tr -d ' '); \
	stress_tests_total=$(STRESS_RUNS); \
	scale_tests_total=1; \
	fuzz_tests_total=$(FUZZ_CASES); \
	collisions_tests_total=1; \
	manual_word="tests"; if [ "$$manual_tests_total" -eq 1 ]; then manual_word="test"; fi; \
	stress_word="tests"; if [ "$$stress_tests_total" -eq 1 ]; then stress_word="test"; fi; \
	scale_word="tests"; if [ "$$scale_tests_total" -eq 1 ]; then scale_word="test"; fi; \
	fuzz_word="tests"; if [ "$$fuzz_tests_total" -eq 1 ]; then fuzz_word="test"; fi; \
	collisions_word="tests"; if [ "$$collisions_tests_total" -eq 1 ]; then collisions_word="test"; fi; \
	if [ "$$manual_status" = "PASS" ]; then manual_label="PASS ($${manual_tests_total} $${manual_word})"; else manual_label="$$manual_status"; fi; \
	if [ "$$stress_status" = "PASS" ]; then stress_label="PASS ($${stress_tests_total} $${stress_word})"; else stress_label="$$stress_status"; fi; \
	if [ "$$scale_status" = "PASS" ]; then scale_label="PASS ($${scale_tests_total} $${scale_word})"; else scale_label="$$scale_status"; fi; \
	if [ "$$fuzz_status" = "PASS" ]; then fuzz_label="PASS ($${fuzz_tests_total} $${fuzz_word})"; else fuzz_label="$$fuzz_status"; fi; \
	if [ "$$collisions_status" = "PASS" ]; then collisions_label="PASS ($${collisions_tests_total} $${collisions_word})"; else collisions_label="$$collisions_status"; fi; \
	printf -v manual_status_disp "%-16s %s" "$$manual_label" "$$manual_time"; \
	printf -v stress_status_disp "%-16s %s" "$$stress_label" "$$stress_time"; \
	printf -v scale_status_disp "%-16s %s" "$$scale_label" "$$scale_time"; \
	printf -v fuzz_status_disp "%-16s %s" "$$fuzz_label" "$$fuzz_time"; \
	printf -v collisions_status_disp "%-16s %s" "$$collisions_label" "$$collisions_time"; \
	stress_args="runs $(STRESS_RUNS) steps $(STRESS_STEPS) seed $(STRESS_SEED) progress-every $(STRESS_PROGRESS_EVERY) timeout $(STRESS_TIMEOUT)"; \
	scale_args="products $(SCALE_PRODUCTS) invoices $(SCALE_INVOICES) progress-every $(SCALE_PROGRESS_EVERY)"; \
	fuzz_args="cases $(FUZZ_CASES) max-lines $(FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "All tests summary:"; \
	print_status_table \
		"$$status_header" \
		"manual" "$$manual_status_disp" "-" \
		"stress" "$$stress_status_disp" "$$stress_args" \
		"scale" "$$scale_status_disp" "$$scale_args" \
		"fuzz-parse" "$$fuzz_status_disp" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status_disp" "$$collisions_args"; \
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
	if [ $$failed -ne 0 ]; then if [ "$(EXPORTING)" != "1" ]; then exit 1; fi; fi

quick:
	@$(MAKE) $(MFLAGS) all ORIG_GOALS=quick \
		STRESS_RUNS=8 STRESS_STEPS=120 STRESS_PROGRESS_EVERY=2 \
		SCALE_PRODUCTS=500 SCALE_INVOICES=1200 SCALE_PROGRESS_EVERY=0 \
		FUZZ_CASES=40 FUZZ_LINES=120 FUZZ_PROGRESS_EVERY=10 \
		COLLISIONS_COUNT=20 COLLISIONS_PROGRESS_EVERY=0

manual: clean resolve-exe
	@rm -f $(FAIL_LOG)
	@touch $(FAIL_LOG)
	@exe=$$(cat "$(EXE_CACHE_FILE)"); \
	for i in $(TESTS); do \
		base=$${i%.in}; \
		if [ -f "$$base.arg" ]; then "$$exe" `cat "$$base.arg"` < "$$i" > "$$base.myout"; else "$$exe" < "$$i" > "$$base.myout"; fi; \
		if [ -f "$$base.out" ]; then diff "$$base.myout" "$$base.out" > "$$base.diff" || :; \
		else rm -f "$$base.diff"; echo "diff: $$base.out: No such file or directory"; fi; \
		if [ ! -f "$$base.diff" ] || [ `wc -l < "$$base.diff"` -eq 0 ]; then \
			echo -e "\e[1;32mtest $$i PASSED\e[0m"; \
			rm -f "$$base.diff" "$$base.myout"; \
		else \
			echo -e "\e[1;31mtest $$i FAILED\e[0m"; echo "$$i" >> "$(FAIL_LOG)"; \
			if [ $(FAIL) -eq 1 ]; then exit 1; fi; \
		fi; \
	done
	@total=`echo "$(TESTS)" | wc -w`; \
	failed=`wc -l < $(FAIL_LOG)`; \
	passed=`expr $$total - $$failed`; \
	echo "$$passed tests passed, $$failed tests failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "Manual suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		if [ "$(EXPORTING)" != "1" ]; then exit 1; fi; \
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
	stress_tests_total=$(STRESS_RUNS); \
	scale_tests_total=1; \
	fuzz_tests_total=$(FUZZ_CASES); \
	collisions_tests_total=1; \
	stress_word="tests"; if [ "$$stress_tests_total" -eq 1 ]; then stress_word="test"; fi; \
	scale_word="tests"; if [ "$$scale_tests_total" -eq 1 ]; then scale_word="test"; fi; \
	fuzz_word="tests"; if [ "$$fuzz_tests_total" -eq 1 ]; then fuzz_word="test"; fi; \
	collisions_word="tests"; if [ "$$collisions_tests_total" -eq 1 ]; then collisions_word="test"; fi; \
	if [ "$$stress_status" = "PASS" ]; then stress_label="PASS ($${stress_tests_total} $${stress_word})"; else stress_label="$$stress_status"; fi; \
	if [ "$$scale_status" = "PASS" ]; then scale_label="PASS ($${scale_tests_total} $${scale_word})"; else scale_label="$$scale_status"; fi; \
	if [ "$$fuzz_status" = "PASS" ]; then fuzz_label="PASS ($${fuzz_tests_total} $${fuzz_word})"; else fuzz_label="$$fuzz_status"; fi; \
	if [ "$$collisions_status" = "PASS" ]; then collisions_label="PASS ($${collisions_tests_total} $${collisions_word})"; else collisions_label="$$collisions_status"; fi; \
	printf -v stress_status_disp "%-16s %s" "$$stress_label" "$$stress_time"; \
	printf -v scale_status_disp "%-16s %s" "$$scale_label" "$$scale_time"; \
	printf -v fuzz_status_disp "%-16s %s" "$$fuzz_label" "$$fuzz_time"; \
	printf -v collisions_status_disp "%-16s %s" "$$collisions_label" "$$collisions_time"; \
	stress_args="runs $(STRESS_RUNS) steps $(STRESS_STEPS) seed $(STRESS_SEED) progress-every $(STRESS_PROGRESS_EVERY) timeout $(STRESS_TIMEOUT)"; \
	scale_args="products $(SCALE_PRODUCTS) invoices $(SCALE_INVOICES) progress-every $(SCALE_PROGRESS_EVERY)"; \
	fuzz_args="cases $(FUZZ_CASES) max-lines $(FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "Python suite summary:"; \
	print_status_table \
		"$$status_header" \
		"stress" "$$stress_status_disp" "$$stress_args" \
		"scale" "$$scale_status_disp" "$$scale_args" \
		"fuzz-parse" "$$fuzz_status_disp" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status_disp" "$$collisions_args"; \
	echo "$$passed/$$total parts passed, $$failed/$$total parts failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "Python suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		if [ "$(EXPORTING)" != "1" ]; then exit 1; fi; \
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
	manual_tests_total=$$(echo "$(ASAN_MANUAL_TESTS)" | wc -w | tr -d ' '); \
	fuzz_tests_total=$(ASAN_FUZZ_CASES); \
	collisions_tests_total=1; \
	manual_word="tests"; if [ "$$manual_tests_total" -eq 1 ]; then manual_word="test"; fi; \
	fuzz_word="tests"; if [ "$$fuzz_tests_total" -eq 1 ]; then fuzz_word="test"; fi; \
	collisions_word="tests"; if [ "$$collisions_tests_total" -eq 1 ]; then collisions_word="test"; fi; \
	if [ "$$manual_status" = "PASS" ]; then manual_label="PASS ($${manual_tests_total} $${manual_word})"; else manual_label="$$manual_status"; fi; \
	if [ "$$fuzz_status" = "PASS" ]; then fuzz_label="PASS ($${fuzz_tests_total} $${fuzz_word})"; else fuzz_label="$$fuzz_status"; fi; \
	if [ "$$collisions_status" = "PASS" ]; then collisions_label="PASS ($${collisions_tests_total} $${collisions_word})"; else collisions_label="$$collisions_status"; fi; \
	printf -v manual_status_disp "%-16s %s" "$$manual_label" "$$manual_time"; \
	printf -v fuzz_status_disp "%-16s %s" "$$fuzz_label" "$$fuzz_time"; \
	printf -v collisions_status_disp "%-16s %s" "$$collisions_label" "$$collisions_time"; \
	fuzz_args="cases $(ASAN_FUZZ_CASES) max-lines $(ASAN_FUZZ_LINES) seed $(FUZZ_SEED) progress-every $(FUZZ_PROGRESS_EVERY)"; \
	collisions_args="count $(ASAN_COLLISIONS_COUNT) start $(COLLISIONS_START) progress-every $(COLLISIONS_PROGRESS_EVERY)"; \
	echo ""; \
	echo "ASAN suite summary:"; \
	print_status_table \
		"$$status_header" \
		"manual" "$$manual_status_disp" "-" \
		"fuzz-parse" "$$fuzz_status_disp" "$$fuzz_args" \
		"scale-collisions" "$$collisions_status_disp" "$$collisions_args"; \
	echo "$$passed/$$total parts passed, $$failed/$$total parts failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "ASAN suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		if [ "$(EXPORTING)" != "1" ]; then exit 1; fi; \
	else \
		echo "ASAN suite PASSED."; \
	fi


clean::
	rm -rf *.diff *.myout *.cmpdiff $(FAIL_LOG) $(COMPARE_FAIL_LOG) $(STATS_FILE) *.gcno *.gcda *.gcov

export:
	@has_manual_fail=0; \
	if [ -s "$(FAIL_LOG)" ]; then has_manual_fail=1; fi; \
	has_py_fail=0; \
	for d in stress-failures scale-failures collisions-failures fuzz-failures; do \
		if [ -d "$$d" ]; then \
			if ls "$$d"/*.in >/dev/null 2>&1; then has_py_fail=1; fi; \
		fi; \
	done; \
	has_compare_fail=0; \
	if [ -s "$(COMPARE_FAIL_LOG)" ]; then has_compare_fail=1; fi; \
	if [ $$has_manual_fail -eq 0 ] && [ $$has_py_fail -eq 0 ] && [ $$has_compare_fail -eq 0 ]; then \
		echo "✔ Não há testes falhados para exportar."; \
	else \
		echo "Exporting failed tests to export/ directory..."; \
		rm -rf export; \
		mkdir -p export; \
		if [ $$has_manual_fail -eq 1 ]; then \
			while IFS= read -r t; do \
				base="$${t%.in}"; \
				[ -f "$$base.in" ] && cp "$$base.in" export/ || :; \
				[ -f "$$base.out" ] && cp "$$base.out" export/ || :; \
				[ -f "$$base.myout" ] && cp "$$base.myout" export/ || :; \
				[ -f "$$base.diff" ] && cp "$$base.diff" export/ || :; \
				[ -f "$$base.txt" ] && cp "$$base.txt" export/ || :; \
				[ -f "$$base.arg" ] && cp "$$base.arg" export/ || :; \
			done < "$(FAIL_LOG)"; \
			mv "$(FAIL_LOG)" export/; \
			echo "Manual failed tests exported."; \
		fi; \
		if [ $$has_py_fail -eq 1 ]; then \
			echo "Extracting Python failures..."; \
			for d in stress-failures scale-failures collisions-failures fuzz-failures; do \
				if [ -d "$$d" ]; then \
					for f in "$$d"/*.in; do \
						if [ -f "$$f" ]; then \
							echo "========================================" >> export/python_failures.txt; \
							echo "File: $$f" >> export/python_failures.txt; \
							seed=$$(echo "$$f" | grep -o 'seed_[0-9]*' | cut -d'_' -f2); \
							echo "Seed: $$seed" >> export/python_failures.txt; \
							echo "Cases:" >> export/python_failures.txt; \
							cat "$$f" >> export/python_failures.txt; \
							echo "" >> export/python_failures.txt; \
						fi; \
					done; \
				fi; \
			done; \
			echo "Python failures exported to export/python_failures.txt"; \
		fi; \
		if [ $$has_compare_fail -eq 1 ]; then \
			mkdir -p export/compare; \
			while IFS= read -r t; do \
				base="$${t%.in}"; \
				[ -f "$$base.in" ] && cp "$$base.in" export/compare/ || :; \
				[ -f "$$base.out" ] && cp "$$base.out" export/compare/ || :; \
				[ -f "$$base.cmpdiff" ] && cp "$$base.cmpdiff" export/compare/ || :; \
				[ -f "$$base.txt" ] && cp "$$base.txt" export/compare/ || :; \
				[ -f "$$base.arg" ] && cp "$$base.arg" export/compare/ || :; \
			done < "$(COMPARE_FAIL_LOG)"; \
			cp "$(COMPARE_FAIL_LOG)" export/compare/; \
			echo "Compare failures exported to export/compare/."; \
		fi; \
		zip_done=0; \
		if [ "$(AUTO_ZIP)" = "1" ]; then \
			zip_name="export_$$(date +%Y-%m-%d_%H-%M-%S).zip"; \
			zip -r "$$zip_name" export > /dev/null 2>&1; \
			zip_done=1; \
			echo "✔ Ficheiro $$zip_name criado automaticamente."; \
		else \
			read -r -p "Queres criar um ficheiro zip com os testes exportados? [y/N] " ans; \
			if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
				zip_name="export_$$(date +%Y-%m-%d_%H-%M-%S).zip"; \
				zip -r "$$zip_name" export > /dev/null 2>&1; \
				zip_done=1; \
				echo "✔ Ficheiro $$zip_name criado."; \
			fi; \
		fi; \
		if [ "$$zip_done" -eq 1 ]; then \
			read -r -p "Queres apagar a pasta export/ original? [y/N] " apagar; \
			if [ "$$apagar" = "y" ] || [ "$$apagar" = "Y" ]; then \
				rm -rf export; \
				echo "✔ Pasta export/ apagada."; \
			else \
				echo "  $$(pwd)/export preservado."; \
			fi; \
		fi; \
		echo "========================================"; \
		echo "✔ Export complete."; \
		echo "========================================"; \
	fi; \
	if [ -s "$(STATS_FILE)" ]; then \
		if [ ! -d export ]; then mkdir -p export; fi; \
		cp "$(STATS_FILE)" export/; \
		echo "Test statistics exported to export/$(STATS_FILE)."; \
	fi

export-zip:
	@$(MAKE) $(MFLAGS) export AUTO_ZIP=1

zip:
	@:

EXE2 ?=
EXE2_CACHE_FILE ?= .resolved_exe2
COMPARE_TESTS ?= $(TESTS)

compare: resolve-exe
	@if [ -z "$(EXE2)" ]; then \
		if [ -s "$(EXE2_CACHE_FILE)" ] && [ -x "$$(cat "$(EXE2_CACHE_FILE)")" ]; then \
			exe2=$$(cat "$(EXE2_CACHE_FILE)"); \
		else \
			if [ ! -t 0 ]; then \
				echo "EXE2 must be set. Usage: make compare EXE2=/path/to/second/executable"; \
				exit 1; \
			fi; \
			read -r -p "Indica o caminho do segundo executável para comparar: " input; \
			while true; do \
				if [ -x "$$input" ]; then exe2="$$input"; break; fi; \
				if [ -x "$$input/$(EXE_NAME)" ]; then exe2="$$input/$(EXE_NAME)"; break; fi; \
				read -r -p "Não encontrado. Indica outro caminho: " input; \
			done; \
		fi; \
	else \
		if [ ! -x "$(EXE2)" ]; then \
			echo "EXE2 path is not executable: $(EXE2)"; \
			exit 1; \
		fi; \
		exe2="$(EXE2)"; \
	fi; \
	echo "$$exe2" > "$(EXE2_CACHE_FILE)"; \
	exe1=$$(cat "$(EXE_CACHE_FILE)"); \
	rm -f "$(COMPARE_FAIL_LOG)"; \
	echo "Comparing:"; \
	echo "  EXE1: $$exe1"; \
	echo "  EXE2: $$exe2"; \
	echo ""; \
	total=0; same=0; differ=0; \
	for i in $(COMPARE_TESTS); do \
		total=$$((total + 1)); \
		base=$${i%.in}; \
		if [ -f "$$base.arg" ]; then \
			"$$exe1" `cat "$$base.arg"` < "$$i" > "$$base.cmp1" 2>/dev/null; \
			"$$exe2" `cat "$$base.arg"` < "$$i" > "$$base.cmp2" 2>/dev/null; \
		else \
			"$$exe1" < "$$i" > "$$base.cmp1" 2>/dev/null; \
			"$$exe2" < "$$i" > "$$base.cmp2" 2>/dev/null; \
		fi; \
		if diff -q "$$base.cmp1" "$$base.cmp2" > /dev/null 2>&1; then \
			echo -e "\e[1;32mtest $$i IDENTICAL\e[0m"; \
			same=$$((same + 1)); \
		else \
			echo -e "\e[1;31mtest $$i DIFFERS\e[0m"; \
			differ=$$((differ + 1)); \
			diff "$$base.cmp1" "$$base.cmp2" > "$$base.cmpdiff" || :; \
			echo "$$i" >> "$(COMPARE_FAIL_LOG)"; \
		fi; \
		rm -f "$$base.cmp1" "$$base.cmp2"; \
	done; \
	echo ""; \
	echo "$$same/$$total identical, $$differ/$$total differ"; \
	if [ $$differ -ne 0 ]; then \
		echo "Diff files saved as *.cmpdiff for differing tests."; \
		if [ "$(EXPORTING)" != "1" ]; then exit 1; fi; \
	fi

count:
	@{ \
	total=$$(echo "$(TESTS)" | wc -w | tr -d ' '); \
	with_arg=$$(ls -1 test*.arg 2>/dev/null | wc -l | tr -d ' '); \
	with_txt=$$(ls -1 test*.txt 2>/dev/null | wc -l | tr -d ' '); \
	echo "Test suite statistics"; \
	echo "===================="; \
	echo "Total tests:          $$total"; \
	echo "Tests with .arg file: $$with_arg"; \
	echo "Tests with .txt desc: $$with_txt"; \
	echo ""; \
	echo "Tests per command:"; \
	echo "--------------------"; \
	for cmd_file in $(CMD_LIST_PREFIX)*.txt; do \
		if [ -f "$$cmd_file" ]; then \
			cmd=$$(echo "$$cmd_file" | sed 's/$(CMD_LIST_PREFIX)//' | sed 's/\.txt$$//'); \
			cmd_count=$$(sed -e 's/#.*//' -e '/^[[:space:]]*$$/d' "$$cmd_file" | wc -l | tr -d ' '); \
			printf "  %-20s %s tests\n" "$$cmd" "$$cmd_count"; \
		fi; \
	done; \
	for cmd_file in "comando "*.txt; do \
		if [ -f "$$cmd_file" ]; then \
			cmd=$$(echo "$$cmd_file" | sed 's/comando //' | sed 's/\.txt$$//'); \
			cmd_count=$$(sed -e 's/#.*//' -e '/^[[:space:]]*$$/d' "$$cmd_file" | wc -l | tr -d ' '); \
			printf "  %-20s %s tests\n" "$$cmd" "$$cmd_count"; \
		fi; \
	done; \
	echo ""; \
	echo "Python test scripts:"; \
	echo "--------------------"; \
	for py in random_stress.py scale_limits.py fuzz_parse.py scale_collisions.py; do \
		if [ -f "$$py" ]; then \
			printf "  %-28s present\n" "$$py"; \
		else \
			printf "  %-28s missing\n" "$$py"; \
		fi; \
	done; \
	} | tee "$(STATS_FILE)"

rerun: resolve-exe
	@if [ ! -s "$(FAIL_LOG)" ]; then \
		echo "Não há testes falhados para re-executar ($(FAIL_LOG) vazio ou inexistente)."; \
		exit 0; \
	fi; \
	tests=$$(tr '\n' ' ' < "$(FAIL_LOG)"); \
	echo "Re-running failed tests: $$tests"; \
	$(MAKE) $(MFLAGS) manual TESTS="$$tests" EXE_CACHE_FILE="$(EXE_CACHE_FILE)"

show-diff:
	@found=0; \
	for f in *.diff; do \
		if [ -f "$$f" ] && [ -s "$$f" ]; then \
			found=1; \
			base=$${f%.diff}; \
			echo ""; \
			echo -e "\e[1;33m════════════════════════════════════════\e[0m"; \
			echo -e "\e[1;31m  $$base FAILED\e[0m"; \
			if [ -f "$$base.txt" ]; then \
				echo -e "\e[0;36m  $$(head -1 "$$base.txt")\e[0m"; \
			fi; \
			echo -e "\e[1;33m════════════════════════════════════════\e[0m"; \
			while IFS= read -r line; do \
				case "$$line" in \
					'<'*) echo -e "\e[31m$$line\e[0m" ;; \
					'>'*) echo -e "\e[32m$$line\e[0m" ;; \
					*) echo "$$line" ;; \
				esac; \
			done < "$$f"; \
		fi; \
	done; \
	for d in stress-failures scale-failures fuzz-failures collisions-failures; do \
		if [ -d "$$d" ]; then \
			for reason_file in "$$d"/*.reason; do \
				if [ -f "$$reason_file" ]; then \
					found=1; \
					base=$${reason_file%.reason}; \
					name=$$(basename "$$base"); \
					suite=$$(basename "$$d" -failures); \
					echo ""; \
					echo -e "\e[1;33m════════════════════════════════════════\e[0m"; \
					echo -e "\e[1;31m  [$$suite] $$name FAILED\e[0m"; \
					echo -e "\e[0;36m  Reason: $$(cat "$$reason_file")\e[0m"; \
					echo -e "\e[1;33m════════════════════════════════════════\e[0m"; \
					if [ -f "$$base.expected" ] && [ -f "$$base.out" ]; then \
						diffout=$$(diff "$$base.expected" "$$base.out" | head -60); \
						if [ -n "$$diffout" ]; then \
							echo -e "\e[0;33m  Expected vs Actual:\e[0m"; \
							echo "$$diffout" | while IFS= read -r line; do \
								case "$$line" in \
									'<'*) echo -e "\e[31m  $$line\e[0m" ;; \
									'>'*) echo -e "\e[32m  $$line\e[0m" ;; \
									*) echo "  $$line" ;; \
								esac; \
							done; \
						fi; \
					elif [ -f "$$base.out" ]; then \
						out_lines=$$(wc -l < "$$base.out" | tr -d ' '); \
						echo -e "\e[0;33m  Output ($$out_lines lines):\e[0m"; \
						head -20 "$$base.out" | while IFS= read -r line; do \
							echo "  $$line"; \
						done; \
						if [ "$$out_lines" -gt 20 ]; then \
							echo "  ... ($$out_lines lines total, showing first 20)"; \
						fi; \
					fi; \
					if [ -f "$$base.stderr" ] && [ -s "$$base.stderr" ]; then \
						echo -e "\e[0;33m  Stderr:\e[0m"; \
						head -10 "$$base.stderr" | while IFS= read -r line; do \
							echo -e "\e[31m  $$line\e[0m"; \
						done; \
					fi; \
				fi; \
			done; \
		fi; \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "Não há diffs para mostrar. Todos os testes passaram ou ainda não foram executados."; \
	fi

valgrind: resolve-src
	@if ! command -v valgrind >/dev/null 2>&1; then \
		echo "Erro: 'valgrind' não está instalado."; \
		echo "  macOS:  brew install valgrind"; \
		echo "  Ubuntu: sudo apt install valgrind"; \
		exit 1; \
	fi; \
	src=$$(cat "$(SRC_CACHE_FILE)"); \
	echo "Compiling with debug symbols for Valgrind..."; \
	gcc -g -O0 -Wall -Wextra -Wno-unused-result -o $(VALGRIND_EXE) "$$src" || exit 1; \
	echo ""; \
	total=0; passed=0; failed=0; \
	for i in $(VALGRIND_TESTS); do \
		total=$$((total + 1)); \
		base=$${i%.in}; \
		if [ -f "$$base.arg" ]; then \
			vg_out=$$(valgrind --leak-check=full --error-exitcode=42 --log-fd=2 \
				$(VALGRIND_EXE) `cat "$$base.arg"` < "$$i" > /dev/null 2>&1; echo $$?); \
		else \
			vg_out=$$(valgrind --leak-check=full --error-exitcode=42 --log-fd=2 \
				$(VALGRIND_EXE) < "$$i" > /dev/null 2>&1; echo $$?); \
		fi; \
		if [ "$$vg_out" -eq 42 ]; then \
			echo -e "\e[1;31mtest $$i LEAK/ERROR\e[0m"; \
			failed=$$((failed + 1)); \
		else \
			echo -e "\e[1;32mtest $$i CLEAN\e[0m"; \
			passed=$$((passed + 1)); \
		fi; \
	done; \
	echo ""; \
	echo "$$passed/$$total clean, $$failed/$$total with leaks/errors"; \
	if [ $$failed -ne 0 ]; then \
		echo "Corre 'valgrind --leak-check=full $(VALGRIND_EXE) < testXXX.in' para detalhes."; \
		exit 1; \
	fi

lizard: resolve-src
	@if ! command -v lizard >/dev/null 2>&1; then \
		echo "Erro: 'lizard' não está instalado."; \
		echo "  Instala com: pip install lizard"; \
		exit 1; \
	fi; \
	src=$$(cat "$(SRC_CACHE_FILE)"); \
	echo "Running Lizard complexity analysis on $$src..."; \
	echo ""; \
	lizard "$$src"

coverage: resolve-src
	@if ! command -v gcov >/dev/null 2>&1; then \
		echo "Erro: 'gcov' não está instalado."; \
		echo "  gcov faz parte do GCC. Instala gcc para obter gcov."; \
		exit 1; \
	fi; \
	src=$$(cat "$(SRC_CACHE_FILE)"); \
	cp "$$src" .cov_src.c; \
	echo "Compiling with coverage instrumentation..."; \
	gcc --coverage -g -O0 -Wall -Wextra -Wno-unused-result -o $(COVERAGE_EXE) .cov_src.c || { rm -f .cov_src.c; exit 1; }; \
	test_count=$$(echo "$(COVERAGE_TESTS)" | wc -w | tr -d ' '); \
	echo "Running $$test_count tests through coverage build..."; \
	for i in $(COVERAGE_TESTS); do \
		base=$${i%.in}; \
		if [ -f "$$base.arg" ]; then \
			$(COVERAGE_EXE) `cat "$$base.arg"` < "$$i" > /dev/null 2>&1 || :; \
		else \
			$(COVERAGE_EXE) < "$$i" > /dev/null 2>&1 || :; \
		fi; \
	done; \
	echo ""; \
	gcov .cov_src.c > /dev/null 2>&1; \
	echo "════════════════════════════════════════"; \
	gcov -n .cov_src.c 2>/dev/null | head -n 2; \
	echo "════════════════════════════════════════"; \
	echo ""; \
	uncovered=$$(grep -c '#####' .cov_src.c.gcov 2>/dev/null || echo 0); \
	if [ "$$uncovered" -eq 0 ]; then \
		echo -e "\e[1;32m✔ Todas as linhas foram executadas!\e[0m"; \
	else \
		echo -e "\e[1;33mLinhas não executadas ($$uncovered):\e[0m"; \
		echo ""; \
		grep -n '#####' .cov_src.c.gcov | while IFS= read -r line; do \
			echo -e "\e[31m  $$line\e[0m"; \
		done; \
	fi; \
	echo ""; \
	if [ -t 0 ]; then \
		read -r -p "Guardar relatório completo em coverage_report.gcov? [y/N] " ans; \
		if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
			cp .cov_src.c.gcov coverage_report.gcov; \
			echo "✔ Relatório guardado em coverage_report.gcov"; \
		fi; \
	fi; \
	rm -f .cov_src.c .cov_src.gcno .cov_src.gcda .cov_src.c.gcov $(COVERAGE_EXE) $(COVERAGE_EXE)-*.gcno $(COVERAGE_EXE)-*.gcda

help:
	@echo ""
	@echo "  Makefile — Suite de testes IAED"
	@echo "  ================================"
	@echo ""
	@echo "  Comandos principais:"
	@echo "    make                Corre apenas os testes manuais (default)"
	@echo "    make all            Corre tudo: manual + stress + scale + fuzz + collisions"
	@echo "    make quick          Igual a 'all' mas com limites reduzidos (rápido)"
	@echo "    make python         Corre apenas a suite Python (stress/scale/fuzz/collisions)"
	@echo "    make asan           Compila com ASAN/UBSan e corre testes de memória"
	@echo ""
	@echo "  Scripts Python individuais:"
	@echo "    make stress         Teste de stress com sequências aleatórias"
	@echo "    make scale          Teste de escala (muitos produtos/faturas)"
	@echo "    make fuzz-parse     Fuzzing do parser com inputs malformados"
	@echo "    make scale-collisions  Teste de colisões na hash table"
	@echo ""
	@echo "  Testes por comando:"
	@echo "    make p|l|a|r|f|c|d  Corre testes específicos de cada comando"
	@echo "                        (ex: 'make p' ou 'make a r f')"
	@echo ""
	@echo "  Comparação e estatísticas:"
	@echo "    make compare EXE2=path  Compara dois executáveis nos mesmos testes"
	@echo "    make count              Mostra estatísticas da suite de testes"
	@echo ""
	@echo "  Exportação:"
	@echo "    make export         Exporta testes falhados para export/"
	@echo "    make export-zip     Exporta + cria zip automaticamente"
	@echo "    make all export     Corre tudo e exporta os que falharam"
	@echo "    make count export   Inclui estatísticas na exportação"
	@echo ""
	@echo "  Utilidades:"
	@echo "    make rerun          Re-executa apenas os testes que falharam"
	@echo "    make show-diff      Mostra os diffs dos testes falhados (colorizado)"
	@echo "    make valgrind       Corre testes com Valgrind (deteta memory leaks)"
	@echo "    make lizard         Analisa complexidade do código com Lizard"
	@echo "    make coverage       Relatório de cobertura de código (gcov)"
	@echo "    make clean          Remove ficheiros gerados (*.diff, *.myout, logs)"
	@echo "    make help           Mostra esta ajuda"
	@echo ""
	@echo "  Variáveis úteis:"
	@echo "    EXE=path            Caminho do executável principal"
	@echo "    EXE2=path           Caminho do segundo executável (compare)"
	@echo "    FAIL=1              Parar ao primeiro teste falhado"
	@echo "    TESTS='t1.in t2.in' Correr apenas testes específicos"
	@echo "    STRESS_RUNS=N       Número de iterações do stress (default: $(STRESS_RUNS))"
	@echo "    FUZZ_CASES=N        Número de casos de fuzz (default: $(FUZZ_CASES))"
	@echo ""
