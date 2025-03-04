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

"""Implementation of ContainerPath class."""

from __future__ import annotations

import pathlib
import typing

from ops import pebble

from . import _errors

if typing.TYPE_CHECKING:
    import os

    import ops
    from typing_extensions import Self, TypeAlias


_StrPathLike: TypeAlias = 'str | os.PathLike[str]'


class ContainerPath:
    def __init__(self, *parts: _StrPathLike, container: ops.Container) -> None:
        self._path = pathlib.PurePath(*parts)
        self._container = container

    def _str(self) -> str:
        return f"'{self._path}' in ops.Container {self._container.name}"

    #############################
    # protocol PurePath methods #
    #############################

    def __str__(self) -> str:
        return self._path.__str__()

    #########################
    # protocol Path methods #
    #########################

    def iterdir(self) -> typing.Generator[Self]:
        # python < 3.13 defers NotADirectoryError to iteration time, but python 3.13 raises on call
        if not self.is_dir():
            raise _errors.NotADirectory.exception(self._str())
        file_infos = self._container.list_files(self._path)
        for f in file_infos:
            yield self.with_segments(f.path)

    # protocol requires only 3.8 signature, but we provide the 3.12 follow_symlinks kwarg
    def exists(self, follow_symlinks: bool = True) -> bool:
        return self._filetype_matches(filetype=None, follow_symlinks=follow_symlinks)

    # protocol requires only 3.8 signature, but we provide the 3.13 follow_symlinks kwarg
    def is_dir(self, follow_symlinks: bool = True) -> bool:
        return self._filetype_matches(pebble.FileType.DIRECTORY, follow_symlinks=follow_symlinks)

    # protocol requires only 3.8 signature, but we provide the 3.13 follow_symlinks kwarg
    def is_file(self, follow_symlinks: bool = True) -> bool:
        return self._filetype_matches(pebble.FileType.FILE, follow_symlinks=follow_symlinks)

    def _filetype_matches(self, filetype: pebble.FileType | None, follow_symlinks: bool) -> bool:
        info = self._get_fileinfo()
        if info is None:
            return False
        if follow_symlinks and info.type is pebble.FileType.SYMLINK:
            raise NotImplementedError()
        if filetype is None:  # we only care if the file exists
            return True
        return info.type is filetype

    def _get_fileinfo(self) -> pebble.FileInfo | None:
        try:
            [info] = self._container.list_files(self._path, itself=True)
        except pebble.APIError as e:
            if _errors.FileNotFound.matches(e):
                return None
            raise
        return info

    ##################################################
    # protocol Path methods with extended signatures #
    ##################################################

    def write_bytes(
        self,
        data: bytes,
        # extended with chmod + chown args
        *,
        mode: int | None = None,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> int: ...

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: typing.Literal['strict', 'ignore'] | None = None,
        # extended with chmod + chown args
        *,
        mode: int | None = None,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> int: ...

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
        # extended with chown args
        *,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> None: ...

    #############################
    # non-protocol Path methods #
    #############################

    def with_segments(self, *pathsegments: _StrPathLike) -> Self:
        return type(self)(*pathsegments, container=self._container)
