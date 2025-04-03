# Copyright 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    parser.add_argument('git_base_ref')
    args = parser.parse_args()
    return args.git_base_ref


def _main(project_root: pathlib.Path, git_base_ref: str) -> None:
    git_diff_cmd = ['git', 'diff', '--name-only', f'origin/{git_base_ref}']
    git_diff = subprocess.run(git_diff_cmd, capture_output=True, text=True)
    changes = git_diff.stdout.split('\n')
    # record which packages have changed, or all if global config files have changed
    if any(change.startswith(_GLOBAL_FILES) for change in changes):
        changed_packages = sorted(
            path.name
            for path in project_root.iterdir()
            if path.is_dir() and path.name.startswith(_ALPHABET)
        )
    else:
        names = {change.split('/')[0] for change in changes}
        changed_packages = sorted(
            n for n in names if (project_root / n).is_dir() and n.startswith(_ALPHABET)
        )
    # record the test suites provided by each package
    tests = ('unit', 'integration/pebble', 'integration/juju')
    output: dict[str, list[str]] = {test: [] for test in tests}
    output['changed'] = changed_packages
    for name in tests:
        for package in changed_packages:
            if (project_root / package / 'tests' / name).is_dir():
                output[name].append(package)
    # set output
    with pathlib.Path(os.environ['GITHUB_OUTPUT']).open('a') as f:
        for name, packages in output.items():
            line = f'{pathlib.PurePath(name).name}={json.dumps(packages)}'
            print(line)
            print(line, file=f)


if __name__ == '__main__':
    _main(project_root=pathlib.Path(), git_base_ref=_parse_args())
