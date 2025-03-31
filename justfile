set ignore-comments  # don't print comment lines in recipes

# set on the commandline as needed, e.g. `just package=pathops python=3.8 unit`
package := 'pathops'
python := '3.12'

# this is the first recipe in the file, so it will run if just is called without a recipe
[doc('Describe usage and list the available recipes.')]
_help:
    @echo 'Execute one of the following recipes with {{CYAN}}`just {{BLUE}}$recipe-name{{CYAN}}`{{NORMAL}}.'
    @echo 'All recipes require {{CYAN}}`uv`{{NORMAL}} to be available.'
    @echo 'Set the {{BOLD}}package{{NORMAL}} and {{BOLD}}python{{NORMAL}} version before the recipe name if needed.'
    @echo 'For example, {{CYAN}}`just {{BOLD}}package{{NORMAL}}{{CYAN}}={{package}} {{BOLD}}python{{NORMAL}}{{CYAN}}={{python}} unit`{{NORMAL}}.'
    @just --list --unsorted

[doc('Run `ruff` and `codespell`, failing afterwards if any errors are found.')]
lint:
    #!/usr/bin/env bash
    set -xueo pipefail
    FAILURES=0
    uv run ruff check --preview --diff || ((FAILURES+=1))
    uv run ruff format --preview --diff || ((FAILURES+=1))
    uv run codespell --toml=pyproject.toml || ((FAILURES+=1))
    : "$FAILURES command(s) failed."
    exit $FAILURES

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format:
    uv run --python='{{python}}' ruff check --preview --fix
    uv run --python='{{python}}' ruff format --preview

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *pyright_args:
    uv run --python='{{python}}' --group='{{package}}' \
        pyright --pythonversion='{{python}}' {{pyright_args}} '{{package}}'

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'unit' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    export PEBBLE=/tmp/pebble-test
    umask 0
    pebble run --create-dirs &>/dev/null &
    PEBBLE_PID=$!
    set +e  # don't exit if the tests fail
    just --justfile='{{justfile()}}' package='{{package}}' python='{{python}}' _coverage 'integration/pebble' {{flags}}
    EXITCODE=$?
    set -e  # do exit if anything goes wrong now
    kill $PEBBLE_PID
    exit $EXITCODE


[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'integration/juju' flags)

[doc("Use uv to install and run coverage for the specified package's tests.")]
_coverage test_subdir +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    uv sync --python='{{python}}' --group='{{package}}'
    source .venv/bin/activate
    cd '{{package}}'
    export COVERAGE_RCFILE=../pyproject.toml
    DATA_FILE=".report/coverage-$(basename {{test_subdir}})-{{python}}.db"
    uv run --active coverage run --data-file="$DATA_FILE" --source='src' \
        -m pytest --tb=native -vv '{{flags}}' 'tests/{{test_subdir}}'
    uv run --active coverage report --data-file="$DATA_FILE"

[doc("Combine `coverage` reports for the specified package and python version.")]
combine-coverage:
    #!/usr/bin/env bash
    set -xueo pipefail
    : 'Collect the coverage data files that exist for this package.'
    data_files=()
    for test_id in unit pebble juju; do
        data_file="{{package}}/.report/coverage-$test_id-{{python}}.db"
        if [ -e "$data_file" ]; then
            data_files+=("$data_file")
        fi
    done
    : 'Combine coverage.'
    export COVERAGE_RCFILE=pyproject.toml
    DATA_FILE='{{package}}/.report/coverage-all-{{python}}.db'
    HTML_DIR='{{package}}/.report/htmlcov-all-{{python}}'
    uv run coverage combine --keep --data-file="$DATA_FILE" "${data_files[@]}"
    uv run coverage xml --data-file="$DATA_FILE" -o '{{package}}/.report/coverage-all-{{python}}.xml'
    rm -rf "$HTML_DIR"  # let coverage create html directory from scratch
    uv run coverage html --data-file="$DATA_FILE" --show-contexts --directory="$HTML_DIR"
    uv run coverage report --data-file="$DATA_FILE"
