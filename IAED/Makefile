.SUFFIXES: .in .out .diff
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
OK="\e[1;32mtest $< PASSED\e[0m"
KO="\e[1;31mtest $< FAILED\e[0m"
FAIL=0
EXE=../proj
LOG=tests.log

all:: clean
	@rm -f $(LOG)
	@for i in `ls test*.in | sed -e "s/in/diff/"`; do $(MAKE) $(MFLAGS) $$i || exit; done
	@echo "`wc -l < $(LOG)` tests passed"

.in.diff:
	@-if [ -f $*.arg ]; then $(EXE) `cat $*.arg` < $< > $*.myout; else $(EXE) < $< > $*.myout; fi
	@-diff $*.myout $*.out > $@ ||:
	@if [ `wc -l < $@` -eq 0 ]; then echo -e $(OK); echo $* >> $(LOG); else echo -e $(KO); if [ $(FAIL) -eq 1 ]; then false; fi; fi;

clean::
	rm -rf *.diff *.myout $(LOG)
