# PIPELINE (Superior Software, 1988) - rebuilt from source with baron.
#
#   make          assemble build/pipeline.ssd, and build/pipeline.hfe with the
#                 deleted data marks an .ssd can't hold
#   make verify   assemble, then check the .ssd against original/pipeline.ssd
#                 byte for byte and the .hfe against the original flux capture
#   make test     verify, plus the tools' own tests and the symbol sets'
#   make jsbeeb-symbols
#                 build/jsbeeb-symbols/*.json: the symbol sets jsbeeb's
#                 debugger shows names from (src/symbols.toml)
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
LISTINGS = build/listings
SYMBOL_SETS = build/jsbeeb-symbols

.PHONY: all verify test clean jsbeeb-symbols

all: $(TARGET) $(HFE)

# Every source assembles on its own (baron gives each a fresh symbol table);
# each SECTION with a filename lands in build/files with a .inf sidecar, and
# mkssd places them as src/disc.toml says. The files directory is wiped first
# so a renamed section can't leave a stale binary behind.
$(TARGET): $(SOURCES) $(INCLUDES) $(DATA) $(LAYOUT) tools/mkssd.py tools/dfs.py
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

# Each source again on its own, with -vv, which lists every byte each
# statement emits, so the symbol sets can find each section's bytes, labels
# and operands. (Its binaries, in files/, are build/files' again.)
$(LISTINGS)/%.txt: src/%.6502 $(INCLUDES) $(DATA)
	@mkdir -p $(LISTINGS)/files
	$(BARON) -p $(LISTINGS)/files -vv -log0 $@ $< > /dev/null

# A set's source is the commit built, so it's made every time.
jsbeeb-symbols: $(TARGET) $(patsubst src/%.6502,$(LISTINGS)/%.txt,$(SOURCES))
	$(PYTHON) tools/jsbeeb_symbols.py src/symbols.toml $(LISTINGS) build/symbols.json build/files \
		$(SYMBOL_SETS) --commit $(shell git rev-parse HEAD)

test: verify jsbeeb-symbols
	BARON=$(BARON) $(PYTHON) -m unittest discover -s tests

clean:
	rm -rf build
