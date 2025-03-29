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
format:
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies =['ruff=={{_ruff_version}}']
    # ///
    import sys
    import subprocess

    for cmd in (
        ['ruff', 'check', '--preview', '--fix'],
        ['ruff', 'format', '--preview'],
    ):
        print(cmd)
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *args:
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies =[
    #     'pyright=={{_pyright_version}}',
    #     'pytest=={{_pytest_version}}',
    #     'charmlibs-{{package}} @ {{justfile_directory()}}/{{package}}',
    # ]
    # ///
    import sys
    import shlex
    import subprocess

    cmd = ['pyright', '--pythonversion={{python}}', *shlex.split('{{args}}')]
    print(cmd)
    try:
        subprocess.run(cmd, check=True, cwd='{{package}}')
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'unit' '.' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA': (_coverage 'pebble' 'integration' flags)

[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'juju' 'integration' flags)

[doc("Use uv to install and run coverage for the specified package's tests.")]
_coverage test_id test_subdir='.' +flags='-rA':
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies = [
    #     'pytest=={{_pytest_version}}',
    #     'coverage[toml]=={{_coverage_version}}',
    #     'charmlibs-{{package}} @ {{justfile_directory()}}/{{package}}',
    # ]
    # ///
    import pathlib
    import shlex
    import shutil
    import subprocess
    import sys

    CWD = pathlib.Path('{{justfile_directory()}}/{{package}}')

    def coverage(command: str, *args: str) -> None:
        cmd = [
            'uv',
            'run',
            '--active',
            'coverage',
            command,
            f'--data-file={{_coverage_dir}}/coverage-{{test_id}}-{{python}}.db',
            '--rcfile={{justfile_directory()}}/pyproject.toml',
            *args,
        ]
        print(cmd)
        try:
            subprocess.run(cmd, check=True, cwd=CWD)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

    (CWD / '{{_coverage_dir}}').mkdir(exist_ok=True)
    coverage(
        'run',
        '--source=src',
        '-m',
        'pytest',
        '-vv',
        *shlex.split('{{flags}}'),
        '--tb=native',
        'tests/{{test_subdir}}/{{test_id}}',
    )
    coverage('xml', '-o', '{{_coverage_dir}}/coverage-{{test_id}}-{{python}}.xml')
    html_dir = '{{_coverage_dir}}/htmlcov-{{test_id}}-{{python}}'
    if (CWD / html_dir).is_dir():
        shutil.rmtree(CWD / html_dir)
    coverage('html', '--show-contexts', f'--directory={html_dir}')
    coverage('report')

[doc("Start `pebble`, run pebble integration tests, and shutdown `pebble` cleanly afterwards.")]
pebble-local +flags='-rA':
    #!/usr/bin/env -S uv run --python={{python}} --no-project --script
    import os
    import pathlib
    import subprocess
    import sys
    import time
    from subprocess import DEVNULL

    ENV = {**os.environ, 'PEBBLE': '{{_pebble_dir}}'}
    pathlib.Path('{{_pebble_dir}}').mkdir(exist_ok=True)

    print('Run pebble in background, redirecting its output to /dev/null, and write its pid to a file.')
    pebble_cmd = ['pebble', 'run', '--create-dirs']
    print(pebble_cmd)
    pebble_result = subprocess.Popen(pebble_cmd, stdout=DEVNULL, stderr=DEVNULL, env=ENV)
    pid = pebble_result.pid
    print(f'Pebble PID: {pid}')
    time.sleep(1)

    just_cmd = [
        'just',
        '--justfile={{justfile()}}',
        'package={{package}}',
        'python={{python}}',
        'pebble',
        '{{flags}}',
    ]
    print(just_cmd)
    result = subprocess.run(just_cmd, env=ENV, cwd='{{justfile_directory()}}')

    print('Cleanup pebble.')
    time.sleep(1)
    cleanup_cmd = ['kill', str(pid)]
    print(cleanup_cmd)
    subprocess.run(cleanup_cmd)

    sys.exit(result.returncode)

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
