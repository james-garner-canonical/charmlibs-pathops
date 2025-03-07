# Copyright 2025 Canonical Ltd.
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

from __future__ import annotations

import typing

import pytest

import stuff

if typing.TYPE_CHECKING:
    import pathlib
    from typing import Iterator

    import ops


@pytest.fixture(scope='session')
def container() -> ops.Container:
    return stuff.make_container('test1')


@pytest.fixture(scope='session')
def another_container() -> ops.Container:
    return stuff.make_container('test2')


@pytest.fixture(scope='session')
def readable_interesting_dir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[pathlib.Path]:
    tmp_path = tmp_path_factory.mktemp('readable_interesting_dir')
    with stuff.populate_interesting_dir(tmp_path):
        yield tmp_path


@pytest.fixture(scope='function')
def writeable_interesting_dir(tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    with stuff.populate_interesting_dir(tmp_path):
        yield tmp_path
