PYTHON ?= python3

# Optional local settings (gitignored). Set DEPLOY_DIR there to have builds
# copy the ROM/cue/bin set somewhere (e.g. an SD-card staging folder).
-include local.mk

.PHONY: all verify patch disc deploy clean

all: verify patch disc deploy

verify:
	$(PYTHON) scripts/verify_assets.py

patch:
	$(PYTHON) scripts/build_patch.py

disc:
	$(PYTHON) scripts/build_disc.py

deploy:
ifdef DEPLOY_DIR
	mkdir -p "$(DEPLOY_DIR)"
	cp build/GhoulsnGhostsCD.md build/GhoulsnGhostsCD.cue \
	   build/GhoulsnGhostsCD.bin "$(DEPLOY_DIR)/"
	@echo "deployed to $(DEPLOY_DIR)"
else
	@echo "DEPLOY_DIR not set (see local.mk.example); skipping deploy"
endif

clean:
	rm -rf build
