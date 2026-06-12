PYTHON ?= python3

.PHONY: all verify patch disc clean

all: verify patch disc

verify:
	$(PYTHON) scripts/verify_assets.py

patch:
	$(PYTHON) scripts/build_patch.py

disc:
	$(PYTHON) scripts/build_disc.py

clean:
	rm -rf build
