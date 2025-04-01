
SHELL := /bin/bash
PYTHON ?= 3.12

.ONESHELL:

.PHONY: help
help:
	@echo 'Usage: make PACKAGE=<package> [PYTHON=<python version>] target [ARGS=<additional args>]'
	@echo 'Targets:'
	@awk -F: '/^[a-z-]+:.*/ { print "   ", $$1 }' Makefile

.PHONY: lint
lint:  # Run `ruff` and `codespell`, failing afterwards if any errors are found.
	@set -xueo pipefail
	@FAILURES=0
	@uv run ruff check --preview || ((FAILURES+=1))
	@uv run ruff check --preview --diff || ((FAILURES+=1))
	@uv run ruff format --preview --diff || ((FAILURES+=1))
	@uv run codespell --toml=pyproject.toml || ((FAILURES+=1))
	@: "$$FAILURES command(s) failed."
	@exit $$FAILURES

.PHONY: format
format:  # Run `ruff check --fix` and `ruff --format`, modifying files in place.
	uv run ruff check --preview --fix
	uv run ruff format --preview

.PHONY: static
static:  # Run `pyright`, e.g. `make PYTHON=3.8 PACKAGE=pathops static`.
ifeq ($(strip $(PACKAGE)),)
	@echo "PACKAGE must be set"
	@exit 1
else
	uv run --group='$(PACKAGE)' pyright --pythonversion='$(PYTHON)' $(ARGS) '$(PACKAGE)'
endif

.PHONY: unit
unit:  # Run unit tests with `coverage`, e.g. `just python=3.8 unit pathops`.
	$(MAKE) PACKAGE=$(PACKAGE) PYTHON=$(PYTHON) _coverage TESTS='unit' ARGS='$(ARGS)'

.PHONY: pebble
pebble:  # Run pebble integration tests with `coverage`. Requires `pebble`.
	@set -xueo pipefail
	@export PEBBLE=/tmp/pebble-test
	@umask 0
	@pebble run --create-dirs &>/dev/null &
	@PEBBLE_PID=$$!
	@set +e  # don't exit if the tests fail
	@$(MAKE) PACKAGE=$(PACKAGE) PYTHON=$(PYTHON) _coverage TESTS='integration/pebble' ARGS='$(ARGS)'
	@EXITCODE=$$?
	@set -e  # do exit if anything goes wrong now
	@kill $$PEBBLE_PID
	@exit $$EXITCODE

.PHONY: juju
juju:  # Run juju integration tests. Requires `juju`.
	$(MAKE) PACKAGE=$(PACKAGE) PYTHON=$(PYTHON) _coverage TESTS='integration/juju' ARGS='$(ARGS)'

.PHONY: _coverage
_coverage:  # Use uv to install and run coverage for the specified package's tests.
ifeq ($(strip $(PACKAGE)),)
	@echo "PACKAGE must be set"
	@exit 1
else ifeq ($(strip $(TESTS)),)
	@echo "TESTS must be set"
	@exit 1
else
	@set -xueo pipefail
	@uv sync --python='$(PYTHON)' --group='$(PACKAGE)'
	@source .venv/bin/activate
	@cd '$(PACKAGE)'
	@export COVERAGE_RCFILE=../pyproject.toml
	@DATA_FILE=".report/coverage-$$(basename $(TESTS))-$(PYTHON).db"
	@uv run --active coverage run --data-file="$$DATA_FILE" --source='src' \
		-m pytest --tb=native -vv $(ARGS) tests/$(TESTS)
	@uv run --active coverage report --data-file="$$DATA_FILE"
endif

.PHONY: combine-coverage
combine-coverage:  # Combine `coverage` reports, e.g. `just python=3.8 combine-coverage pathops`.
ifeq ($(strip $(PACKAGE)),)
	@echo "PACKAGE must be set"
	@exit 1
else
	@set -xueo pipefail
	@: 'Collect the coverage data files that exist for this package.'
	@data_files=()
	@for test_id in unit pebble juju; do
	@    data_file="$(PACKAGE)/.report/coverage-$$test_id-$(PYTHON).db"
	@    if [ -e "$$data_file" ]; then
	@        data_files+=("$$data_file")
	@    fi
	@done
	@: 'Combine coverage.'
	@export COVERAGE_RCFILE=pyproject.toml
	@DATA_FILE='$(PACKAGE)/.report/coverage-all-$(PYTHON).db'
	@HTML_DIR='$(PACKAGE)/.report/htmlcov-all-$(PYTHON)'
	@uv run coverage combine --keep --data-file="$$DATA_FILE" "$${data_files[@]}"
	@uv run coverage xml --data-file="$$DATA_FILE" -o '$(PACKAGE)/.report/coverage-all-$(PYTHON).xml'
	@rm -rf "$$HTML_DIR"  # let coverage create html directory from scratch
	@uv run coverage html --data-file="$$DATA_FILE" --show-contexts --directory="$$HTML_DIR"
	@uv run coverage report --data-file="$$DATA_FILE"
endif
