PYTHON := .venv/bin/python

.PHONY: setup dev-install check

setup: $(PYTHON)

$(PYTHON):
	./scripts/setup.sh

dev-install: $(PYTHON)
	$(PYTHON) -m pip install -e '.[dev]'

check: $(PYTHON)
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src tests
	$(PYTHON) -m pytest -q
