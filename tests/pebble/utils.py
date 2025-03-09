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

"""Constants and helpers for use in conftest.py and tests."""

from __future__ import annotations

import contextlib
import os
import pathlib
import socket
import string
import tempfile
import typing

import ops
from ops import pebble

if typing.TYPE_CHECKING:
    from typing import Iterator, Mapping


BINARY_FILE_NAME = 'binary_file.bin'
BROKEN_SYMLINK_NAME = 'symlink_broken'
EMPTY_DIR_NAME = 'empty_dir'
EMPTY_FILE_NAME = 'empty_file.bin'
MISSING_FILE_NAME = 'does_not_exist'
SOCKET_NAME = 'socket.socket'
SYMLINK_NAME = 'symlink.bin'
TEXT_FILE_NAME = 'alphabet.txt'

TEXT_FILES: Mapping[str, str] = {
    TEXT_FILE_NAME: string.ascii_lowercase,
    # TODO: enable additional files if we figure out why the socket is timing out
    # 'bar.txt': string.ascii_uppercase * 2,
    # 'baz.txt': '',
    # 'bartholemew.txt': 'Bartholemew',
}
UTF8_BINARY_FILES: Mapping[str, bytes] = {
    str(pathlib.Path(k).with_suffix('.bin')): v.encode() for k, v in TEXT_FILES.items()
}
UTF16_BINARY_FILES: Mapping[str, bytes] = {
    str(pathlib.Path(k).with_suffix('.bin16')): v.encode('utf-16') for k, v in TEXT_FILES.items()
}
BINARY_FILES: Mapping[str, bytes | bytearray] = {
    BINARY_FILE_NAME: bytearray(range(256)),
    **UTF8_BINARY_FILES,
    **UTF16_BINARY_FILES,
}


class Mocks:
    @staticmethod
    def raises_unknown_api_error(*args: object, **kwargs: object):
        raise pebble.APIError(body={}, code=9000, status='', message='')

    @staticmethod
    def raises_connection_error(*args: object, **kwargs: object):
        raise pebble.ConnectionError()

    @staticmethod
    def raises_unknown_path_error(*args: object, **kwargs: object):
        raise pebble.PathError(kind='unknown-kind', message='unknown-message')


@contextlib.contextmanager
def populate_interesting_dir(directory: pathlib.Path) -> Iterator[None]:
    (directory / EMPTY_DIR_NAME).mkdir()
    empty_file = directory / EMPTY_FILE_NAME
    empty_file.touch()
    (directory / SYMLINK_NAME).symlink_to(empty_file)
    # (directory / 'symlink_dir').symlink_to(directory / 'empty_dir')
    # (directory / 'symlink_rec').symlink_to(directory)
    (directory / BROKEN_SYMLINK_NAME).symlink_to(directory / 'does_not_exist')
    for filename, contents in TEXT_FILES.items():
        (directory / filename).write_text(contents)
    for filename, contents in BINARY_FILES.items():
        (directory / filename).write_bytes(contents)
    sock = socket.socket(socket.AddressFamily.AF_UNIX)
    sock.bind(str(directory / SOCKET_NAME))
    # TODO: make block device?
    try:
        assert not (directory / MISSING_FILE_NAME).exists()
        yield
    finally:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()


# import time
# class SlowPebbleContainer(ops.Container):
#     @property
#     def _pebble(self):
#         time.sleep(0.1)
#         return self._real_pebble
#
#     @_pebble.setter
#     def _pebble(self, value):
#         self._real_pebble = value
# ops.Container = SlowPebbleContainer


def make_container(name: str) -> ops.Container:
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


with tempfile.TemporaryDirectory() as _dirname:
    _tempdir = pathlib.Path(_dirname)
    with populate_interesting_dir(_tempdir):
        FILENAMES = tuple(path.name for path in _tempdir.iterdir())
FILENAMES_PLUS = (*FILENAMES, MISSING_FILE_NAME)
