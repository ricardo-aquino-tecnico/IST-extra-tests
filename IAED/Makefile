.SUFFIXES: .in .out .diff
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DEFAULT_GOAL := manual-tests
.PHONY: all manual manual-tests python stress scale fuzz-parse scale-collisions asan clean p l a r f c d
OK="\e[1;32mtest $< PASSED\e[0m"
KO="\e[1;31mtest $< FAILED\e[0m"
FAIL=0
EXE ?= ../../proj
LOG=tests.log
TESTS ?= $(sort $(wildcard test*.in))
CMD_LIST_PREFIX ?= comando_
STRESS_RUNS ?= 1000
STRESS_STEPS ?= 1250
STRESS_SEED ?= $(shell date +%s)
SCALE_PRODUCTS ?= 10000
SCALE_INVOICES ?= 100001
FUZZ_CASES ?= 400
FUZZ_LINES ?= 300
FUZZ_SEED ?= $(shell date +%s)
COLLISIONS_COUNT ?= 200
COLLISIONS_START ?= 1000000
ASAN_EXE ?= ../proj_asan

all:
	@total=2; passed=0; failed=0; \
	$(MAKE) $(MFLAGS) manual && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	$(MAKE) $(MFLAGS) python && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	echo "$$passed suites passed, $$failed suites failed"; \
	test $$failed -eq 0

manual: clean
	@rm -f $(LOG)
	@touch $(LOG)
	@for i in $(TESTS); do $(MAKE) $(MFLAGS) $${i%.in}.diff || exit; done
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
	$(MAKE) $(MFLAGS) manual TESTS="$$tests"

python:
	@total=4; passed=0; failed=0; \
	$(MAKE) $(MFLAGS) stress && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	$(MAKE) $(MFLAGS) scale && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	$(MAKE) $(MFLAGS) fuzz-parse && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	$(MAKE) $(MFLAGS) scale-collisions && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	echo "$$passed python tests passed, $$failed python tests failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "Python suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		exit 1; \
	else \
		echo "Python suite PASSED."; \
	fi

stress:
	@echo "stress seed: $(STRESS_SEED)"
	@python3 random_stress.py --exe $(EXE) --runs $(STRESS_RUNS) --steps $(STRESS_STEPS) --seed $(STRESS_SEED) && \
	echo "1 stress test passed, 0 stress tests failed" || \
	{ echo "0 stress tests passed, 1 stress tests failed"; exit 1; }

scale:
	@python3 scale_limits.py --exe $(EXE) --products $(SCALE_PRODUCTS) --invoices $(SCALE_INVOICES) && \
	echo "1 scale test passed, 0 scale tests failed" || \
	{ echo "0 scale tests passed, 1 scale tests failed"; exit 1; }

fuzz-parse:
	@echo "fuzz seed: $(FUZZ_SEED)"
	@python3 fuzz_parse.py --exe $(EXE) --cases $(FUZZ_CASES) --max-lines $(FUZZ_LINES) --seed $(FUZZ_SEED) && \
	echo "1 fuzz-parse test passed, 0 fuzz-parse tests failed" || \
	{ echo "0 fuzz-parse tests passed, 1 fuzz-parse tests failed"; exit 1; }

scale-collisions:
	@python3 scale_collisions.py --exe $(EXE) --count $(COLLISIONS_COUNT) --start $(COLLISIONS_START) && \
	echo "1 scale-collisions test passed, 0 scale-collisions tests failed" || \
	{ echo "0 scale-collisions tests passed, 1 scale-collisions tests failed"; exit 1; }

asan:
	@gcc -fsanitize=address,undefined -fno-omit-frame-pointer -g -O1 -Wall -Wextra -Werror -Wno-unused-result -o $(ASAN_EXE) ../project.c
	@total=3; passed=0; failed=0; \
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 $(MAKE) EXE=$(ASAN_EXE) manual; \
	manual_total=`ls test*.in | wc -l`; \
	manual_passed=`wc -l < $(LOG)`; \
	manual_failed=`expr $$manual_total - $$manual_passed`; \
	if [ $$manual_failed -eq 0 ]; then passed=$$((passed + 1)); else failed=$$((failed + 1)); fi; \
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 fuzz_parse.py --exe $(ASAN_EXE) --cases 150 --max-lines 180 --seed $(FUZZ_SEED) && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 scale_collisions.py --exe $(ASAN_EXE) --count 120 --start $(COLLISIONS_START) && passed=$$((passed + 1)) || failed=$$((failed + 1)); \
	echo "$$passed asan tests passed, $$failed asan tests failed"; \
	if [ $$failed -ne 0 ]; then \
		echo "ASAN suite FAILED: $$failed test(s) failed. 'make' returns Error 1 on purpose."; \
		exit 1; \
	else \
		echo "ASAN suite PASSED."; \
	fi

.in.diff:
	@-if [ -f $*.arg ]; then $(EXE) `cat $*.arg` < $< > $*.myout; else $(EXE) < $< > $*.myout; fi
	@-diff $*.myout $*.out > $@ ||:
	@if [ `wc -l < $@` -eq 0 ]; then echo -e $(OK); echo $* >> $(LOG); else echo -e $(KO); if [ $(FAIL) -eq 1 ]; then false; fi; fi;

clean::
	rm -rf *.diff *.myout $(LOG)
