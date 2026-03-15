.SUFFIXES: .in .out .diff
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DEFAULT_GOAL := manual-tests
.PHONY: all manual manual-tests python stress scale fuzz-parse scale-collisions asan clean
OK="\e[1;32mtest $< PASSED\e[0m"
KO="\e[1;31mtest $< FAILED\e[0m"
FAIL=0
EXE=../proj
LOG=tests.log
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

all: manual python

manual: clean
	@rm -f $(LOG)
	@for i in `ls test*.in | sed -e "s/in/diff/"`; do $(MAKE) $(MFLAGS) $$i || exit; done
	@echo "`wc -l < $(LOG)` tests passed"

manual-tests: manual

python: stress scale fuzz-parse scale-collisions

stress:
	@echo "stress seed: $(STRESS_SEED)"
	python3 random_stress.py --exe $(EXE) --runs $(STRESS_RUNS) --steps $(STRESS_STEPS) --seed $(STRESS_SEED)

scale:
	python3 scale_limits.py --exe $(EXE) --products $(SCALE_PRODUCTS) --invoices $(SCALE_INVOICES)

fuzz-parse:
	@echo "fuzz seed: $(FUZZ_SEED)"
	python3 fuzz_parse.py --exe $(EXE) --cases $(FUZZ_CASES) --max-lines $(FUZZ_LINES) --seed $(FUZZ_SEED)

scale-collisions:
	python3 scale_collisions.py --exe $(EXE) --count $(COLLISIONS_COUNT) --start $(COLLISIONS_START)

asan:
	gcc -fsanitize=address,undefined -fno-omit-frame-pointer -g -O1 -Wall -Wextra -Werror -Wno-unused-result -o $(ASAN_EXE) ../project.c
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 $(MAKE) EXE=$(ASAN_EXE) manual
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 fuzz_parse.py --exe $(ASAN_EXE) --cases 150 --max-lines 180 --seed $(FUZZ_SEED)
	ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 scale_collisions.py --exe $(ASAN_EXE) --count 120 --start $(COLLISIONS_START)

.in.diff:
	@-if [ -f $*.arg ]; then $(EXE) `cat $*.arg` < $< > $*.myout; else $(EXE) < $< > $*.myout; fi
	@-diff $*.myout $*.out > $@ ||:
	@if [ `wc -l < $@` -eq 0 ]; then echo -e $(OK); echo $* >> $(LOG); else echo -e $(KO); if [ $(FAIL) -eq 1 ]; then false; fi; fi;

clean::
	rm -rf *.diff *.myout $(LOG)
