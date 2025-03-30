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
    #!/usr/bin/env -S UV_PROJECT_ENVIRONMENT=.venv-{{python}} uv run --python={{python}} --script
    import subprocess, sys

    error_count = 0
    for cmd in (
        ['ruff', 'check', '--preview', '--diff'],
        ['ruff', 'format', '--preview', '--diff'],
        ['codespell', '--toml=pyproject.toml'],
    ):
        print(cmd)
        try:
            subprocess.run(cmd, check=True)
            print(f'Linting command {cmd[0]!r} succeeded!')
        except subprocess.CalledProcessError:
            print(f'Linting command {cmd[0]!r} failed.')
            error_count += 1
    print(f'Linting done! {error_count} process(es) found errors.')
    sys.exit(error_count)

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format:
    uv run --python={{python}} ruff check --preview --fix
    uv run --python={{python}} ruff format --preview

[doc('Run `pyright` for the specified `package` and `python` version.')]
static *args:
    uv run --python={{python}} --group={{package}} \
        pyright --pythonversion={{python}} {{args}} {{package}}

[doc("Run the specified package's unit tests with the specified python version with `coverage`.")]
unit +flags='-rA': (_coverage 'run' 'unit' flags)

[doc("Run the specified package's pebble integration tests with the specified python version with `coverage`.")]
pebble +flags='-rA': (_coverage 'run' 'integration/pebble' flags)

[doc("Run the specified package's juju integration tests with the specified python version with `coverage`.")]
juju +flags='-rA': (_coverage 'run' 'integration/juju' flags)

[doc("Combine `coverage` reports for the specified package and python version.")]
combine-coverage +flags='-rA': (_coverage 'combine' 'all' flags)

[doc("Use uv to install and run coverage for the specified package's tests.")]
_coverage coverage_cmd test_subdir +flags='-rA':
    #!/usr/bin/env -S UV_PROJECT_ENVIRONMENT=.venv-{{package}}-{{python}} uv run --python={{python}} --group={{package}} --script
    import pathlib, shlex, shutil, subprocess, sys

    CWD = pathlib.Path('{{package}}')
    PYTHON_VERSION = '{{python}}'
    COVERAGE_CMD = '{{coverage_cmd}}'
    TEST_SUBDIR = '{{test_subdir}}'
    FLAGS = shlex.split('{{flags}}')

    COVERAGE_DIR = '.report'
    TEST_ID = pathlib.PurePath(TEST_SUBDIR).name
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

    if COVERAGE_CMD == 'run':
        (CWD / COVERAGE_DIR).mkdir(exist_ok=True)
        pytest = ['pytest', '--tb=native', '-vv', *FLAGS, f'tests/{TEST_SUBDIR}']
        coverage('run', '--source=src', '-m', *pytest)
    elif COVERAGE_CMD == 'combine':
        data_files = []
        for test_id in ('unit', 'pebble', 'juju'):
            data_file = f'{COVERAGE_DIR}/coverage-{test_id}-{PYTHON_VERSION}.db'
            if (CWD / data_file).exists():
                data_files.append(data_file)
        coverage('combine', '--keep', *data_files)
    else:
        sys.exit(f'Bad value for coverage command: {COVERAGE_CMD}')

    # let coverage create html directory from scratch
    if (CWD / HTML_DIR).is_dir():
        shutil.rmtree(CWD / HTML_DIR)
    coverage('html', '--show-contexts', f'--directory={HTML_DIR}')
    coverage('xml', '-o', XML_FILE)
    coverage('report')

[doc("Start `pebble`, run pebble integration tests, and shutdown `pebble` cleanly afterwards.")]
pebble-local +flags='-rA':
    #!/usr/bin/env -S uv run --python={{python}} --no-project --script
    import os, pathlib, subprocess, sys
    from subprocess import DEVNULL

    ENV = {**os.environ, 'PEBBLE': '/tmp/pebble-test'}

    pebble_cmd = ['pebble', 'run', '--create-dirs']
    print('Start pebble:', pebble_cmd)
    pebble_process = subprocess.Popen(pebble_cmd, stdout=DEVNULL, stderr=DEVNULL, env=ENV)

    just_cmd = [
        'just',
        '--justfile={{justfile()}}',
        'package={{package}}',
        'python={{python}}',
        'pebble',
        '{{flags}}',
    ]
    print('Run pebble tests:', just_cmd)
    result = subprocess.run(just_cmd, env=ENV)

    pebble_process.kill()
    sys.exit(result.returncode)
