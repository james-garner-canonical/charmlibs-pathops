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

from . import _constants, _errors, _fileinfo
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
    mode: int = _constants.DEFAULT_WRITE_MODE,
    user: str | None = None,
    group: str | None = None,
) -> bool:
    """Ensure source can be read from path. Return True if any changes were made.

    Ensure that path exists, and contains source, and has the correct permissions,
    and has the correct file ownership.

    Returns:
        True if any changes were made, including chown or chmod, otherwise False.
    """
    if not isinstance(path, ContainerPath):  # most likely str or pathlib.Path
        path = LocalPath(path)
    source = _as_bytes(source)
    try:
        info = get_fileinfo(path)
    except FileNotFoundError:
        pass  # file doesn't exist, so writing is required
    else:  # check if metadata and contents already match
        if (
            (info.permissions == mode)
            and (user is None or info.user == user)
            and (group is None or info.group == group)
            and (path.read_bytes() == source)
        ):
            return False  # everything matches, so writing is not required
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source, mode=mode, user=user, group=group)
    return True


def _as_bytes(source: bytes | str | BinaryIO | TextIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return source.encode()
    return _as_bytes(source.read())


def rm(path: pathlib.Path | ContainerPath, *, recursive: bool = False) -> None:
    if isinstance(path, ContainerPath):
        _rm_container_path(path)
    else:
        _rm_pathlib_path(path)


def _rm_container_path(path: ContainerPath, *, recursive: bool = False) -> None:
    try:
        path._container.remove_path(path._path, recursive=recursive)
    except pebble.PathError as e:
        if _errors.DirectoryNotEmpty.matches(e):
            assert not recursive
            raise _errors.DirectoryNotEmpty.exception(path._description()) from e
        raise


def _rm_pathlib_path(path: pathlib.Path, *, recursive: bool = False) -> None:
    if recursive:
        shutil.rmtree(path)
        return
    # non-recursive case
    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:  # not a symlink, is a directory
        path.rmdir()  # error if not empty
    return
