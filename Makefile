# Команды разработки. На Windows используйте `make` из MSYS2 / Git Bash
# или замените на эквивалентные команды PowerShell (см. README).

.PHONY: install run console test lint format check clean

PYTHON ?= python

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

run:
	$(PYTHON) -m jarvis.main

console:
	$(PYTHON) -m jarvis.console

test:
	$(PYTHON) -m pytest --cov=src/jarvis --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m mypy src

format:
	$(PYTHON) -m black src tests
	$(PYTHON) -m ruff check --fix src tests

check: lint test

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
