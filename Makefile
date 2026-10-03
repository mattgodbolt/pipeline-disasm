# PIPELINE (Superior Software, 1988) - rebuilt from source with baron.
#
#   make          assemble build/pipeline.ssd
#   make verify   assemble, then check it against original/pipeline.ssd byte for byte
#   make test     verify, plus the tools' own tests
#   make clean

# Baron is looked for beside this checkout, or beside the main checkout when
# this is a git worktree, then on the PATH.
MAIN     = $(dir $(shell git rev-parse --path-format=absolute --git-common-dir 2>/dev/null))
BARON   ?= $(firstword $(wildcard ../baron/build/src/baron $(MAIN)../baron/build/src/baron) baron)
PYTHON  ?= python3
TARGET   = build/pipeline.ssd
ORIGINAL = original/pipeline.ssd
LAYOUT   = src/disc.toml
SOURCES  = $(wildcard src/*.6502)
INCLUDES = $(wildcard src/*.6502inc)
DATA     = $(wildcard data/*.bin)

.PHONY: all verify test clean

all: $(TARGET)

# Every source assembles on its own (baron gives each a fresh symbol table);
# each SECTION with a filename lands in build/files with a .inf sidecar, and
# mkssd places them as src/disc.toml says. The files directory is wiped first
# so a renamed section can't leave a stale binary behind.
$(TARGET): $(SOURCES) $(INCLUDES) $(DATA) $(LAYOUT) tools/mkssd.py tools/dfs.py
	rm -rf build/files
	mkdir -p build/files
	$(BARON) -p build/files --inf --symbols build/symbols.json -v -log0 build/listing.txt $(SOURCES) > /dev/null
	$(PYTHON) tools/mkssd.py $(LAYOUT) build/files $@

verify: $(TARGET)
	$(PYTHON) tools/ssdcmp.py $(ORIGINAL) $(TARGET) $(LAYOUT)

test: verify
	BARON=$(BARON) $(PYTHON) -m unittest discover -s tests

clean:
	rm -rf build
