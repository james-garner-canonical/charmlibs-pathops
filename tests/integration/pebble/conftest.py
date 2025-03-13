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

import os
import typing

import ops
import pytest

import utils

if typing.TYPE_CHECKING:
    import pathlib
    from typing import Iterator


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
    with utils.populate_interesting_dir(one), utils.populate_interesting_dir(two):
        yield tmp_path


@pytest.fixture(scope='session')
def container() -> ops.Container:
    return _make_container('test1')


@pytest.fixture(scope='session')
def another_container() -> ops.Container:
    return _make_container('test2')


def _make_container(name: str) -> ops.Container:
    class dummy_backend:  # noqa: N801 (CapWords convention)
        class _juju_context:  # noqa: N801 (CapWords convention)
            version = '9000'

    return ops.Container(
        name=name,
        backend=dummy_backend,  # pyright: ignore[reportArgumentType]
        pebble_client=ops.pebble.Client(socket_path=_get_socket_path()),
    )


def _get_socket_path() -> str:
    socket_path = os.getenv('PEBBLE_SOCKET')
    pebble_path = os.getenv('PEBBLE')
    if not socket_path and pebble_path:
        assert isinstance(pebble_path, str)
        socket_path = os.path.join(pebble_path, '.pebble.socket')
    assert socket_path, 'PEBBLE or PEBBLE_SOCKET must be set if RUN_REAL_PEBBLE_TESTS set'
    return socket_path
