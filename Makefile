.DEFAULT_GOAL := help
MDMAN_VENV_DIR ?= $(CURDIR)/.venv
PYTHON := $(MDMAN_VENV_DIR)/bin/python
export MDMAN_VENV_DIR

.PHONY: help setup dev-install check editor

help:
	@echo "mdman – verfügbare Ziele:"
	@echo "  make setup        CLI und Browser-Editor gemeinsam einrichten"
	@echo "  make dev-install  Zusätzlich Python-Prüfwerkzeuge installieren"
	@echo "  make check        Python- und Node-Prüfungen ausführen"
	@echo "  make editor       README.md im lokalen Editor öffnen"
	@echo ""
	@echo "Datei öffnen: mdman edit /pfad/zur/datei.md"

setup:
	./scripts/setup.sh

dev-install: setup
	$(PYTHON) -m pip install -e '.[dev]'

check:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src tests
	$(PYTHON) -m pytest -q
	npm --prefix editor run check
	npm --prefix editor test
	npm --prefix editor run build

editor:
	$(PYTHON) -m mdman edit README.md
