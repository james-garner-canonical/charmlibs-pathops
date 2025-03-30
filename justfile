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
    EXITCODE=0
    uv run ruff check --preview --diff || $EXITCODE=$?
    uv run ruff format --preview --diff || $EXITCODE=$?
    codespell --toml=pyproject.toml || $EXITCODE=$?
    exit $EXITCODE

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format:
    uv run --python='{{python}}' ruff check --preview --fix
    uv run --python='{{python}}' ruff format --preview

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *args:
    uv run --python='{{python}}' --group='{{package}}' \
        pyright --pythonversion='{{python}}' {{args}} '{{package}}'

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'unit' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA': (_coverage 'integration/pebble' flags)

[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'integration/juju' flags)

[doc("Use uv to install and run coverage for the specified package's tests.")]
_coverage test_subdir +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    DATA_FILE="{{package}}/.report/coverage-$(basename {{test_subdir}})-{{python}}.db"
    uv run --python='{{python}}' --group='{{package}}' \
        coverage run --data-file="$DATA_FILE" --rcfile=pyproject.toml \
        -m pytest --tb=native -vv '{{flags}}' '{{package}}/tests/{{test_subdir}}'
    uv run --python='{{python}}' --group='{{package}}' \
        coverage report --data-file="$DATA_FILE" --rcfile=pyproject.toml

[doc("Combine `coverage` reports for the specified package and python version.")]
combine-coverage:
    #!/usr/bin/env -S uv run --script
    import pathlib, shutil, subprocess, sys

    CWD = pathlib.Path('{{package}}')
    PYTHON_VERSION = '{{python}}'

    COVERAGE_DIR = '.report'
    TEST_ID = 'all'
    DATA_FILE = f'{COVERAGE_DIR}/coverage-{TEST_ID}-{PYTHON_VERSION}.db'
    XML_FILE = f'{COVERAGE_DIR}/coverage-{TEST_ID}-{PYTHON_VERSION}.xml'
    HTML_DIR = f'{COVERAGE_DIR}/htmlcov-{TEST_ID}-{PYTHON_VERSION}'

    def coverage(cmd: str, *args: str) -> None:
        uv = ['uv', 'run', '--active']
        coverage = ['coverage', cmd, f'--data-file={DATA_FILE}', f'--rcfile=pyproject.toml', *args]
        command = [*uv, *coverage]
        print(command)
        try:
            subprocess.run(command, check=True, cwd=CWD)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

    data_files = []
    for test_id in ('unit', 'pebble', 'juju'):
        data_file = f'{COVERAGE_DIR}/coverage-{test_id}-{PYTHON_VERSION}.db'
        if (CWD / data_file).exists():
            data_files.append(data_file)
    coverage('combine', '--keep', *data_files)
    # let coverage create html directory from scratch
    if (CWD / HTML_DIR).is_dir():
        shutil.rmtree(CWD / HTML_DIR)
    coverage('html', '--show-contexts', f'--directory={HTML_DIR}')
    coverage('xml', '-o', XML_FILE)
    coverage('report')

[doc("Start `pebble`, run pebble integration tests, and shutdown `pebble` cleanly afterwards.")]
pebble-local +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    export PEBBLE=/tmp/pebble-test
    pebble run --create-dirs &>/dev/null &
    PEBBLE_PID=$!
    set +e  # don't exit if the tests fail
    just --justfile='{{justfile()}}' package='{{package}}' python='{{python}}' pebble {{flags}}
    EXITCODE=$?
    set -e  # do exit if anything goes wrong now
    kill $PEBBLE_PID
    exit $EXITCODE
