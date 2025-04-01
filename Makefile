
SHELL := /bin/bash
PY ?= 3.12

.ONESHELL:
.SILENT:

.PHONY: help
help:  # Print this message.
	echo 'Usage: make PKG=<package> [PY=<python version>] target [ARGS=<additional args>]'
	echo 'Targets:'
	awk -F':' '/^[a-z-]+:.*/ {print "   ", $$1, $$2}' Makefile | column -t -s '#'

.PHONY: lint
lint:  # Run `ruff` and `codespell`, failing afterwards if any errors are found.
	set -xueo pipefail
	FAILURES=0
	uv run ruff check --preview || ((FAILURES+=1))
	uv run ruff check --preview --diff || ((FAILURES+=1))
	uv run ruff format --preview --diff || ((FAILURES+=1))
	uv run codespell --toml=pyproject.toml || ((FAILURES+=1))
	: "$$FAILURES command(s) failed."
	exit $$FAILURES

.PHONY: format
format:  # Run `ruff check --fix` and `ruff --format`, modifying files in place.
	set -xueo pipefail
	uv run ruff check --preview --fix
	uv run ruff format --preview

.PHONY: static
static:  # Run `pyright`, e.g. `make PY=3.8 PKG=pathops static`.
ifeq ($(strip $(PKG)),)
	echo "PKG must be set"
	exit 1
else
	uv run --group='$(PKG)' pyright --pythonversion='$(PY)' $(ARGS) '$(PKG)'
endif

.PHONY: unit
unit:  # Run unit tests with `coverage`, e.g. `just python=3.8 unit pathops`.
	$(MAKE) PKG=$(PKG) PY=$(PY) _coverage TESTS='unit' ARGS='$(ARGS)'

.PHONY: pebble
pebble:  # Run pebble integration tests with `coverage`. Requires `pebble`.
	set -xueo pipefail
	export PEBBLE=/tmp/pebble-test
	umask 0
	pebble run --create-dirs &>/dev/null &
	PEBBLE_PID=$$!
	set +e  # don't exit if the tests fail
	$(MAKE) PKG=$(PKG) PY=$(PY) _coverage TESTS='integration/pebble' ARGS='$(ARGS)'
	EXITCODE=$$?
	set -e  # do exit if anything goes wrong now
	kill $$PEBBLE_PID
	exit $$EXITCODE

.PHONY: juju
juju:  # Run juju integration tests. Requires `juju`.
	$(MAKE) PKG=$(PKG) PY=$(PY) _coverage TESTS='integration/juju' ARGS='$(ARGS)'

.PHONY: _coverage
_coverage:  # Use uv to install and run coverage for the specified package's tests.
ifeq ($(strip $(PKG)),)
	echo "PKG must be set"
	exit 1
else ifeq ($(strip $(TESTS)),)
	echo "TESTS must be set"
	exit 1
else
	set -xueo pipefail
	uv sync --python='$(PY)' --group='$(PKG)'
	source .venv/bin/activate
	cd '$(PKG)'
	export COVERAGE_RCFILE=../pyproject.toml
	DATA_FILE=".report/coverage-$$(basename $(TESTS))-$(PY).db"
	uv run --active coverage run --data-file="$$DATA_FILE" --source='src' \
	    -m pytest --tb=native -vv $(ARGS) tests/$(TESTS)
	uv run --active coverage report --data-file="$$DATA_FILE"
endif

.PHONY: combine-coverage
combine-coverage:  # Combine `coverage` reports, e.g. `just python=3.8 combine-coverage pathops`.
ifeq ($(strip $(PKG)),)
	echo "PKG must be set"
	exit 1
else
	set -xueo pipefail
	: 'Collect the coverage data files that exist for this package.'
	data_files=()
	for test_id in unit pebble juju; do
	    data_file="$(PKG)/.report/coverage-$$test_id-$(PY).db"
	    if [ -e "$$data_file" ]; then
	        data_files+=("$$data_file")
	    fi
	done
	: 'Combine coverage.'
	export COVERAGE_RCFILE=pyproject.toml
	DATA_FILE='$(PKG)/.report/coverage-all-$(PY).db'
	HTML_DIR='$(PKG)/.report/htmlcov-all-$(PY)'
	uv run coverage combine --keep --data-file="$$DATA_FILE" "$${data_files[@]}"
	uv run coverage xml --data-file="$$DATA_FILE" -o '$(PKG)/.report/coverage-all-$(PY).xml'
	rm -rf "$$HTML_DIR"  # let coverage create html directory from scratch
	uv run coverage html --data-file="$$DATA_FILE" --show-contexts --directory="$$HTML_DIR"
	uv run coverage report --data-file="$$DATA_FILE"
endif
