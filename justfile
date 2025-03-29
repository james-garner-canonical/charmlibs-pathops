set ignore-comments  # don't print comment lines in recipes

# prefix explanations:
# @ don't print line before execution
# - continue even if the line fails

# shell options explanation:
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
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies =[
    #     'ruff=={{_ruff_version}}',
    #     'codespell[toml]=={{_codespell_version}}',
    # ]
    # ///
    import subprocess
    import sys
    error_count = 0
    for cmd in (
        ['ruff', 'check', '--preview', '--diff'],
        ['ruff', 'format', '--preview', '--diff'],
        ['codespell', '{{justfile_directory()}}', '--toml={{justfile_directory()}}/pyproject.toml'],
    ):
        print(cmd)
        try:
            subprocess.run(cmd, check=True)
            print(f'Linting command {cmd[0]!r} succeeded!')
        except subprocess.CalledProcessError:
            print(f'Linting command {cmd[0]!r} failed.')
            error_count += 1
    print(f'Linting done! There were {error_count} error(s).')
    sys.exit(error_count)

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format *args:
    uvx --python={{python}} ruff@{{_ruff_version}} check --preview --fix {{args}}
    uvx --python={{python}} ruff@{{_ruff_version}} format --preview {{args}}

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *args:
    #!/usr/bin/env bash
    set -xueo pipefail
    cd {{package}}
    uvx --with=pytest=={{_pytest_version}} --with-editable='.' \
        pyright@{{_pyright_version}} --pythonversion={{python}} {{args}}

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'unit' '.' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA': (_coverage 'pebble' 'integration' flags)

[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'juju' 'integration' flags)

[doc("Use uvx to install and run coverage for the specified package's tests.")]
_coverage test_id test_subdir='.' +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    function coverage_cmd {
        CMD="$1"
        shift 1
        uvx \
            --python={{python}} \
            --with=pytest=={{_pytest_version}} \
            --with-editable='.' \
            coverage[toml]@{{_coverage_version}} \
            "$CMD" \
            --data-file='{{_coverage_dir}}/coverage-{{test_id}}-{{python}}.db' \
            --rcfile='{{justfile_directory()}}/pyproject.toml' \
            "$@"
    }
    cd {{package}}
    mkdir --parents {{_coverage_dir}}  # parents also means it's ok if it exists
    coverage_cmd run \
        --source=src \
        -m pytest \
        -vv \
        {{flags}} \
        --tb=native \
        tests/{{test_subdir}}/{{test_id}}
    coverage_cmd xml -o '{{_coverage_dir}}/coverage-{{test_id}}-{{python}}.xml'
    HTML_DIR='{{_coverage_dir}}/htmlcov-{{test_id}}-{{python}}'
    rm -rf "$HTML_DIR"  # let coverage create html directory from scratch
    coverage_cmd html --show-contexts --directory="$HTML_DIR"
    coverage_cmd report

[doc("Start `pebble`, run pebble integration tests, and shutdown `pebble` cleanly afterwards.")]
pebble-local +flags='-rA':
    #!/usr/bin/env bash
    set -xueo pipefail
    mkdir --parents {{_pebble_dir}}  # parents also means it's ok if it exists
    if [ ! -e '{{_pebble_dir}}/pebble.pid' ]; then
        : 'Run pebble in background, redirecting its output to /dev/null, and write its pid to a file.'
        bash -c 'PEBBLE={{_pebble_dir}} pebble run --create-dirs &>/dev/null & echo -n $! > {{_pebble_dir}}/pebble.pid'
        sleep 1
        CLEANUP=true
    else
        : 'Skipped running pebble as {{_pebble_dir}}/pebble.pid already exists.'
        CLEANUP=false
    fi
    : 'Run pebble integration tests.'
    set +e  # disable exiting if a command fails, so we don't exit if the tests fail
    env PEBBLE={{_pebble_dir}} just \
        --justfile '{{justfile()}}' \
        package='{{package}}' \
        python='{{python}}' \
        pebble {{flags}}
    EXIT=$?
    set -e  # re-enable exiting if a command fails
    if $CLEANUP; then
        : 'Cleanup pebble.'
        sleep 1
        bash -c 'kill $(<{{_pebble_dir}}/pebble.pid)'  # kill the pebble that we started
        rm {{_pebble_dir}}/pebble.pid
    fi
    exit $EXIT

[doc("Combine `coverage` reports for the specified package and python version.")]
combine-coverage:
    #!/usr/bin/env bash
    set -xueo pipefail
    function coverage_cmd {
        CMD="$1"
        shift 1
        uvx \
            --python={{python}} \
            --with=pytest=={{_pytest_version}} \
            --with-editable='.' \
            coverage[toml]@{{_coverage_version}} \
            "$CMD" \
            --data-file='{{_coverage_dir}}/coverage-all-{{python}}.db' \
            --rcfile='{{justfile_directory()}}/pyproject.toml' \
            "$@"
    }
    cd {{package}}
    : 'Collect the coverage data files that exist for this package.'
    data_files=()
    for test_id in unit pebble juju; do
        data_file={{_coverage_dir}}/coverage-$test_id-{{python}}.db
        if [ -e "$data_file" ]; then
            data_files+=("$data_file")
        fi
    done
    # combine coverage
    coverage_cmd combine --keep "${data_files[@]}"
    coverage_cmd xml -o '{{_coverage_dir}}/coverage-all-{{python}}.xml'
    HTML_DIR='{{_coverage_dir}}/htmlcov-all-{{python}}'
    rm -rf "$HTML_DIR"  # let coverage create html directory from scratch
    coverage_cmd html --show-contexts  --directory=$HTML_DIR
    coverage_cmd report
