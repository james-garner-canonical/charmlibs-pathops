"""Output changed packages and which test suites they have.

Assumes that the current working directory is the project root.
The git reference to diff with must be provided as a commandline argument.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import string
import subprocess

_ALPHABET = tuple(string.ascii_lowercase)
_GLOBAL_FILES = ('pyproject.toml', 'justfile', '.github')


def _parse_args() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument('git-base-ref')
    args = parser.parse_args()
    return args.git_base_ref


def _main(project_root: pathlib.Path, git_base_ref: str) -> None:
    git_diff_cmd = ['git', 'diff', '--name-only', f'origin/{git_base_ref}']
    git_diff = subprocess.run(git_diff_cmd, text=True)
    changes = git_diff.stdout.split('\n')
    # record which packages have changed, or all if global config files have changed
    if any(change.startswith(_GLOBAL_FILES) for change in changes):
        changed_packages = [
            path.name
            for path in project_root.iterdir()
            if path.is_dir() and path.name.startswith(_ALPHABET)
        ]
    else:
        changed_packages = [
            change.split('/')[0]
            for change in changes
            if (project_root / pathlib.Path(change)).is_dir() and change.startswith(_ALPHABET)
        ]
    # record the test suites provided by each package
    tests = ('unit', 'integration/pebble', 'integration/juju')
    tests_dict: dict[str, list[str]] = {test: [] for test in tests}
    for package in changed_packages:
        for test in tests:
            if (project_root / package / test).is_dir():
                tests_dict[test].append(package)
    # set output
    with pathlib.Path(os.environ['GITHUB_OUTPUT']).open('w') as f:
        print(f'changed={json.dumps(changed_packages)}', file=f)
        for test, packages in tests_dict.items():
            print(f'{pathlib.PurePath(test).name}={json.dumps(packages)}', file=f)


if __name__ == '__main__':
    _main(project_root=pathlib.Path(), git_base_ref=_parse_args())
