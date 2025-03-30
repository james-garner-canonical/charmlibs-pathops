set ignore-comments  # don't print comment lines in recipes

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

# this is the first recipe in the file, so it will run if just is called without a recipe
[doc('Describe usage and list the available recipes.')]
help:
    @echo 'Execute one of the following recipes with {{CYAN}}`just {{BLUE}}$recipe-name{{CYAN}}`{{NORMAL}}.'
    @echo 'All recipes require {{CYAN}}`uv`{{NORMAL}} to be available.'
    @echo 'Set the {{BOLD}}package{{NORMAL}} and {{BOLD}}python{{NORMAL}} version before the recipe name if needed.'
    @echo 'For example, {{CYAN}}`just {{BOLD}}package{{NORMAL}}{{CYAN}}={{package}} {{BOLD}}python{{NORMAL}}{{CYAN}}={{python}} unit`{{NORMAL}}.'
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
    print(f'Linting done! There were {error_count} error(s).')
    sys.exit(error_count)

[doc('Run `ruff check --fix` and `ruff --format`, modifying files in place.')]
format:
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies =['ruff=={{_ruff_version}}']
    # ///
    import subprocess, sys

    for cmd in (['ruff', 'check', '--preview', '--fix'], ['ruff', 'format', '--preview']):
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
    import shlex, subprocess, sys

    cmd = ['pyright', '--pythonversion={{python}}', *shlex.split('{{args}}')]
    print(cmd)
    try:
        subprocess.run(cmd, check=True, cwd='{{package}}')
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

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
    #!/usr/bin/env -S uv run --python={{python}} --script
    # /// script
    # dependencies = [
    #     'pytest=={{_pytest_version}}',
    #     'coverage[toml]=={{_coverage_version}}',
    #     'charmlibs-{{package}} @ {{justfile_directory()}}/{{package}}',
    # ]
    # ///
    import pathlib, shlex, shutil, subprocess, sys

    CWD = pathlib.Path('{{justfile_directory()}}/{{package}}')
    RCFILE = '{{justfile_directory()}}/pyproject.toml'
    FLAGS = shlex.split('{{flags}}')
    PYTHON_VERSION = '{{python}}'
    COVERAGE_CMD = '{{coverage_cmd}}'
    COVERAGE_DIR = '{{_coverage_dir}}'
    TEST_SUBDIR = '{{test_subdir}}'
    TEST_ID = pathlib.PurePath(TEST_SUBDIR).name
    DATA_FILE = f'{COVERAGE_DIR}/coverage-{TEST_ID}-{PYTHON_VERSION}.db'
    XML_FILE = f'{COVERAGE_DIR}/coverage-{TEST_ID}-{PYTHON_VERSION}.xml'
    HTML_DIR = f'{COVERAGE_DIR}/htmlcov-{TEST_ID}-{PYTHON_VERSION}'

    def coverage(command: str, *args: str) -> None:
        uv = ['uv', 'run', '--active']
        coverage = ['coverage', command, f'--data-file={DATA_FILE}', f'--rcfile={RCFILE}', *args]
        cmd = [*uv, *coverage]
        print(cmd)
        try:
            subprocess.run(cmd, check=True, cwd=CWD)
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

    pebble_dir = '/tmp/pebble-test'
    pathlib.Path(pebble_dir).mkdir(exist_ok=True)
    ENV = {**os.environ, 'PEBBLE': pebble_dir}

    pebble_cmd = ['pebble', 'run', '--create-dirs']
    print('Start pebble:', pebble_cmd)
    pebble_result = subprocess.Popen(pebble_cmd, stdout=DEVNULL, stderr=DEVNULL, env=ENV)
    pid = pebble_result.pid
    print(f'Pebble PID: {pid}')

    just_cmd = [
        'just',
        '--justfile={{justfile()}}',
        'package={{package}}',
        'python={{python}}',
        'pebble',
        '{{flags}}',
    ]
    print('Run pebble tests:', just_cmd)
    just_result = subprocess.run(just_cmd, env=ENV)

    cleanup_cmd = ['kill', str(pid)]
    print('Cleanup pebble:', cleanup_cmd)
    subprocess.run(cleanup_cmd)

    sys.exit(just_result.returncode)
