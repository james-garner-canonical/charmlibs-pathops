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

import utils

if typing.TYPE_CHECKING:
    import pathlib
    from typing import Iterator

    import ops


@pytest.fixture(scope='session')
def container() -> ops.Container:
    return utils.make_container('test1')


@pytest.fixture(scope='session')
def another_container() -> ops.Container:
    return utils.make_container('test2')


@pytest.fixture(scope='session')
def session_dir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[pathlib.Path]:
    tmp_path = tmp_path_factory.mktemp('session_dir')
    with utils.populate_interesting_dir(tmp_path):
        yield tmp_path


@pytest.fixture(scope='function')
def tmp_dir(tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    with utils.populate_interesting_dir(tmp_path):
        yield tmp_path


@pytest.fixture(scope='class')
def class_tmp_dirs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[pathlib.Path]:
    tmp_path = tmp_path_factory.mktemp('class_tmp_dirs')
    one = tmp_path / '1'
    two = tmp_path / '2'
    one.mkdir()
    two.mkdir()
    with utils.populate_interesting_dir(one):
        with utils.populate_interesting_dir(two):
            yield tmp_path
