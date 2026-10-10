# PIPELINE (Superior Software, 1988) - rebuilt from source with baron.
#
#   make          assemble build/pipeline.ssd, and build/pipeline.hfe with the
#                 deleted data marks an .ssd can't hold
#   make verify   assemble, then check the .ssd against original/pipeline.ssd
#                 byte for byte and the .hfe against the original flux capture
#   make test     verify, plus the tools' own tests
#   make clean

# Baron is looked for beside this checkout, or beside the main checkout when
# this is a git worktree, then on the PATH.
MAIN     = $(dir $(shell git rev-parse --path-format=absolute --git-common-dir 2>/dev/null))
BARON   ?= $(firstword $(wildcard ../baron/build/src/baron $(MAIN)../baron/build/src/baron) baron)
PYTHON  ?= python3
TARGET   = build/pipeline.ssd
HFE      = build/pipeline.hfe
MARKS    = build/pipeline.marks.json
ORIGINAL = original/pipeline.ssd
ORIGINAL_HFE = original/E447ED5E.hfe
NODE    ?= node
LAYOUT   = src/disc.toml
SOURCES  = $(wildcard src/*.6502)
INCLUDES = $(wildcard src/*.6502inc)
DATA     = $(wildcard data/*.bin)

.PHONY: all verify test clean

all: $(TARGET) $(HFE)

# Every source assembles on its own (baron gives each a fresh symbol table);
# each SECTION with a filename lands in build/files with a .inf sidecar, and
# mkssd places them as src/disc.toml says. The files directory is wiped first
# so a renamed section can't leave a stale binary behind. A rebuilt baron
# rebuilds the disc too (the wildcard drops a bare `baron` from the PATH).
$(TARGET): $(SOURCES) $(INCLUDES) $(DATA) $(LAYOUT) tools/mkssd.py tools/dfs.py $(wildcard $(BARON))
	rm -rf build/files
	mkdir -p build/files
	$(BARON) -p build/files --inf --symbols build/symbols.json -v -log0 build/listing.txt $(SOURCES) > /dev/null
	$(PYTHON) tools/mkssd.py --marks $(MARKS) $(LAYOUT) build/files $@

# Needs `npm ci` once: the flux image is made with jsbeeb's disc code.
$(HFE): $(TARGET) tools/mkhfe.mjs
	$(NODE) tools/mkhfe.mjs $(TARGET) $(MARKS) $@

verify: $(TARGET) $(HFE)
	$(PYTHON) tools/ssdcmp.py $(ORIGINAL) $(TARGET) $(LAYOUT)
	$(NODE) tools/disccmp.mjs $(ORIGINAL_HFE) $(HFE)

test: verify
	BARON=$(BARON) $(PYTHON) -m unittest discover -s tests

clean:
	rm -rf build
