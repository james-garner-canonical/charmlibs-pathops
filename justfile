set ignore-comments  # don't print comment lines in recipes

# prefix explanations
# @ don't print line before execution
# - continue even if the line fails

# shell options explanation
# e.g. set -xueo pipefail
# x: print lines, exit on u: undefined var, e: cmd failure, o pipefail: even in a pipeline

# set on the commandline as needed, e.g. `just package=pathops python=3.8 unit`
package := 'pathops'
python := '3.12'

# dependency versions
# don't set these on the commandline, they may not be forwarded to other processes
_codespell_version := '2.3.0'
_coverage_version := '7.6.1'
_pyright_version := '1.1.397'
_pytest_version := '8.3.5'
_ruff_version := '0.11.0'

# constants for recipes
_coverage_dir := '.report'
_pebble_dir := '/tmp/pebble-test'

# this is the first recipe in the file, so it will run if just is called without a recipe
[doc('Describe usage and list the available recipes.')]
help:
    @echo 'Execute one of the following recipes with {{CYAN}}`just {{BLUE}}$recipe-name{{CYAN}}`{{NORMAL}}.'
    @echo 'Most recipes require {{CYAN}}`uvx`{{NORMAL}} and {{CYAN}}`bash`{{NORMAL}} to be available.'
    @echo 'Set the {{BOLD}}package{{NORMAL}} and {{BOLD}}python{{NORMAL}} version before the recipe name if needed.'
    @echo 'For example, {{CYAN}}`just {{BOLD}}package{{NORMAL}}{{CYAN}}={{package}} {{BOLD}}python{{NORMAL}}{{CYAN}}={{python}} {{BLUE}}$recipe-name{{CYAN}}`{{NORMAL}}.'
    @just --list --unsorted

[doc('Run `ruff` and `codespell`, failing if any errors are found.')]
lint:
    # Run ruff and suppress failures so output isn\'t truncated:
    -uvx --python={{python}} ruff@{{_ruff_version}} check --preview --diff
    -uvx --python={{python}} ruff@{{_ruff_version}} format --preview --diff
    # Codespell may fail linting but will tell us all the spelling errors first.
    uvx --python={{python}} codespell@{{_codespell_version}} \
        '{{justfile_directory()}}' \
        --toml='{{justfile_directory()}}/pyproject.toml'
    # Run ruff again, allowing errors to fail linting:
    uvx --python={{python}} ruff@{{_ruff_version}} check --preview
    uvx --python={{python}} ruff@{{_ruff_version}} format --preview --check

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format *args:
    uvx --python={{python}} ruff@{{_ruff_version}} check --preview --fix {{args}}
    uvx --python={{python}} ruff@{{_ruff_version}} format --preview {{args}}

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *args:
    #!/usr/bin/env bash
    set -xueo pipefail
    cd packages/{{package}}
    uvx --with=pytest=={{_pytest_version}} --with-editable='.' \
        pyright@{{_pyright_version}} --pythonversion={{python}} {{args}}

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'unit' 'unit' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA': (_coverage 'pebble' 'integration/pebble' flags)

[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'juju' 'integration/juju' flags)

[doc("Use uvx to install and run coverage for the specified package's tests.")]
_coverage test_id test_subdir +flags='-rA':
    #!/usr/bin/env bash
    DATA_FILE={{_coverage_dir}}/coverage-{{test_id}}-{{python}}.db
    XML_FILE={{_coverage_dir}}/coverage-{{test_id}}-{{python}}.xml
    HTML_DIR={{_coverage_dir}}/htmlcov-{{test_id}}-{{python}}
    function coverage_cmd {
        uvx \
            --python={{python}} \
            --with=pytest=={{_pytest_version}} \
            --with-editable='.' \
            coverage[toml]@{{_coverage_version}} \
            "$@"
    }
    set -xueo pipefail
    cd packages/{{package}}
    mkdir --parents {{_coverage_dir}}  # parents also means it's ok if it exists
    coverage_cmd run \
        --data-file=$DATA_FILE \
        --rcfile=../../pyproject.toml \
        --source=src \
        -m pytest \
        -vv \
        {{flags}} \
        --tb=native \
        tests/{{test_subdir}}
    coverage_cmd xml --data-file=$DATA_FILE -o $XML_FILE
    rm -rf $HTML_DIR  # coverage html doesn't overwrite explicitly passed --directory
    coverage_cmd html --data-file=$DATA_FILE --show-contexts --directory=$HTML_DIR
    coverage_cmd report --data-file=$DATA_FILE

[doc("Start `pebble`, run pebble integration tests, and shutdown `pebble` cleanly afterwards.")]
pebble-local +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    mkdir --parents {{_pebble_dir}}  # parents also means it's ok if it exists
    # start pebble
    if [ ! -e '{{_pebble_dir}}/pebble.pid' ]; then
        # run pebble in background, redirecting its output to /dev/null, and write its pid to a file
        bash -c 'PEBBLE={{_pebble_dir}} pebble run --create-dirs &>/dev/null & echo -n $! > {{_pebble_dir}}/pebble.pid'
        sleep 1
        cleanup=true
    else
        cleanup=false
        echo 'Skipped running pebble as {{_pebble_dir}}/pebble.pid already exists.'
    fi
    # run tests
    set +e  # disable exiting if a command fails, so we don't exit if the tests fail
    env PEBBLE={{_pebble_dir}} just \
        --justfile '{{justfile()}}' \
        package='{{package}}' \
        python='{{python}}' \
        pebble {{flags}}
    exit_code=$?
    # cleanup pebble
    set -e  # re-enable exiting if a command fails
    if $cleanup; then
        sleep 1
        bash -c 'kill $(<{{_pebble_dir}}/pebble.pid)'  # kill the pebble that we started
        rm {{_pebble_dir}}/pebble.pid
    fi
    exit $exit_code

[doc("Combine `coverage` reports for the specified package and python version.")]
combine-coverage:
    #!/usr/bin/env bash
    DATA_FILE={{_coverage_dir}}/coverage-all-{{python}}.db
    XML_FILE={{_coverage_dir}}/coverage-all-{{python}}.xml
    HTML_DIR={{_coverage_dir}}/htmlcov-all-{{python}}
    function coverage_cmd {
        uvx \
            --python={{python}} \
            --with=pytest=={{_pytest_version}} \
            --with-editable='.' \
            coverage[toml]@{{_coverage_version}} \
            "$@"
    }
    set -xueo pipefail
    cd packages/{{package}}
    # make an array of the coverage data files that exist for this package
    data_files=()
    for test_id in unit pebble juju; do
        data_file={{_coverage_dir}}/coverage-$test_id-{{python}}.db
        if [ -e "$data_file" ]; then
            data_files+=("$data_file")
        fi
    done
    # combine coverage
    coverage_cmd combine --keep --data-file=$DATA_FILE "${data_files[@]}"
    coverage_cmd xml --data-file=$DATA_FILE -o $XML_FILE
    coverage_cmd html --data-file=$DATA_FILE --show-contexts  --directory=$HTML_DIR
    coverage_cmd report  --data-file=$DATA_FILE
