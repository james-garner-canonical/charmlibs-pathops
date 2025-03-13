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

"""Public helper functions exported by this package."""

from __future__ import annotations

import pathlib
import shutil
import typing

from ops import pebble

from . import _constants, _fileinfo
from ._container_path import ContainerPath
from ._local_path import LocalPath

if typing.TYPE_CHECKING:
    from typing import BinaryIO, TextIO

    from ._types import StrPathLike


def get_fileinfo(path: StrPathLike | ContainerPath) -> pebble.FileInfo:
    if isinstance(path, ContainerPath):
        return _fileinfo.from_container_path(path)
    return _fileinfo.from_pathlib_path(pathlib.Path(path))


def ensure_contents(
    path: StrPathLike | ContainerPath,
    source: bytes | str | BinaryIO | TextIO,
    *,
    parents: bool = True,
    mode: int = _constants.DEFAULT_WRITE_MODE,
    user: str | None = None,
    group: str | None = None,
) -> bool:
    """Ensure source can be read from path. Return True if any changes were made.

    Ensure that path exists, and contains source, and has the correct permissions,
    and has the correct file ownership.
    Return True if any changes were made, including chown or chmod, otherwise
    return False.
    """
    if not isinstance(path, ContainerPath):  # most likely str or pathlib.Path
        path = LocalPath(path)
    # check if file already exists and has the correct metadata
    try:
        info = get_fileinfo(path)
    except FileNotFoundError:
        info = None
    write_required = (
        info is None
        or (mode is not None and info.permissions != mode)
        or (isinstance(user, str) and info.user != user)
        or (isinstance(group, str) and info.group != group)
    )
    source = _as_bytes(source)
    if not write_required:
        # check if file already has the correct contents (since it exists and has correct metadata)
        contents = path.read_bytes()
        if source != contents:
            write_required = True
    if not write_required:
        return False
    # actually write contents to target
    if parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source, mode=mode, user=user, group=group)
    return True


def _as_bytes(source: bytes | str | BinaryIO | TextIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return bytes(source, encoding='utf-8')
    return _as_bytes(source.read())


def rm(path: pathlib.Path | ContainerPath, *, recursive: bool = False) -> None:
    if isinstance(path, ContainerPath):
        path._container.remove_path(path._path, recursive=recursive)
        return
    if recursive:
        shutil.rmtree(path)
        return
    # non-recursive case
    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:  # not a symlink, is a directory
        path.rmdir()  # error if not empty
    return
