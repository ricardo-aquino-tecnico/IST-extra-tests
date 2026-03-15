.SUFFIXES: .in .out .diff
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
OK="\e[1;32mtest $< PASSED\e[0m"
KO="\e[1;31mtest $< FAILED\e[0m"
FAIL=0
EXE=../proj
LOG=tests.log
STRESS_RUNS ?= 1000
STRESS_STEPS ?= 1250
STRESS_SEED ?= $(shell date +%s)

all:: clean
	@rm -f $(LOG)
	@for i in `ls test*.in | sed -e "s/in/diff/"`; do $(MAKE) $(MFLAGS) $$i || exit; done
	@echo "`wc -l < $(LOG)` tests passed"

stress:
	@echo "stress seed: $(STRESS_SEED)"
	python3 random_stress.py --exe $(EXE) --runs $(STRESS_RUNS) --steps $(STRESS_STEPS) --seed $(STRESS_SEED)

.in.diff:
	@-if [ -f $*.arg ]; then $(EXE) `cat $*.arg` < $< > $*.myout; else $(EXE) < $< > $*.myout; fi
	@-diff $*.myout $*.out > $@ ||:
	@if [ `wc -l < $@` -eq 0 ]; then echo -e $(OK); echo $* >> $(LOG); else echo -e $(KO); if [ $(FAIL) -eq 1 ]; then false; fi; fi;

clean::
	rm -rf *.diff *.myout $(LOG)
