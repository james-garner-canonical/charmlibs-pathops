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
import pathlib
import socket
import string
from typing import Iterator

import ops
import pytest


def _get_socket_path() -> str:
    socket_path = os.getenv('PEBBLE_SOCKET')
    pebble_path = os.getenv('PEBBLE')
    if not socket_path and pebble_path:
        assert isinstance(pebble_path, str)
        socket_path = os.path.join(pebble_path, '.pebble.socket')
    assert socket_path, 'PEBBLE or PEBBLE_SOCKET must be set if RUN_REAL_PEBBLE_TESTS set'
    return socket_path


@pytest.fixture
def container() -> ops.Container:
    class dummy_backend:  # noqa: N801 (CapWords convention)
        class _juju_context:  # noqa: N801 (CapWords convention)
            version = '9000'

    return ops.Container(
        name='test',
        backend=dummy_backend,  # pyright: ignore[reportArgumentType]
        pebble_client=ops.pebble.Client(socket_path=_get_socket_path()),
    )


@pytest.fixture
def text_files() -> dict[str, str]:
    return {
        'foo.txt': string.ascii_lowercase,
        'bar.txt': string.ascii_uppercase * 2,
        'baz.txt': '',
    }


@pytest.fixture
def interesting_dir(tmp_path: pathlib.Path, text_files: dict[str, str]) -> Iterator[pathlib.Path]:
    (tmp_path / 'empty_dir').mkdir()
    empty_file = tmp_path / 'empty_file.bin'
    empty_file.touch()
    (tmp_path / 'symlink.bin').symlink_to(empty_file)
    (tmp_path / 'symlink_dir').symlink_to(tmp_path / 'empty_dir')
    (tmp_path / 'symlink_rec').symlink_to(tmp_path)
    (tmp_path / 'symlink_broken').symlink_to(tmp_path / 'does_not_exist')
    (tmp_path / 'binary_file.bin').write_bytes(bytearray(range(256)))
    for filename, contents in text_files.items():
        (tmp_path / filename).write_text(contents)
    sock = socket.socket(socket.AddressFamily.AF_UNIX)
    sock.bind(str(tmp_path / 'socket.socket'))
    # TODO: make block device?
    try:
        yield tmp_path
    finally:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
