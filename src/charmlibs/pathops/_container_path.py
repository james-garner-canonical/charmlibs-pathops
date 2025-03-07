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

import os
import pathlib
import typing

from ops import pebble

from . import _errors, _fileinfo
from ._types import StrPathLike

if typing.TYPE_CHECKING:
    from typing import Generator

    import ops
    from typing_extensions import Self


class RelativePathError(ValueError):
    """ContainerPath only supports absolute paths.

    This is because Pebble only works with absolute paths. Relative path support
    will likely remain unavailable at least until Pebble supports relative paths.
    In the meantime, use absolute paths.
    """


class ContainerPath:
    def __init__(self, *parts: StrPathLike, container: ops.Container) -> None:
        self._container = container
        self._path = pathlib.PurePosixPath(*parts)
        if not self._path.is_absolute():
            raise RelativePathError(
                f'ContainerPath arguments resolve to relative path: {self._path}'
            )

    def _description(self) -> str:
        return f"'{self._path}' in ops.Container {self._container.name!r}"

    #############################
    # protocol PurePath methods #
    #############################

    def __hash__(self) -> int:
        return hash((self._container.name, self._path))

    def __str__(self) -> str:
        return self._path.__str__()

    def as_posix(self) -> str:
        return self._path.__str__()

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return NotImplemented
        return self._path < other._path

    def __le__(self, other: Self) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return NotImplemented
        return self._path <= other._path

    def __gt__(self, other: Self) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return NotImplemented
        return self._path > other._path

    def __ge__(self, other: Self) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return NotImplemented
        return self._path >= other._path

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return False
        return self._path == other._path

    def __truediv__(self, key: StrPathLike) -> Self:
        """Return a new ContainerPath with the same container and the joined path.

        The joined path is equivalent to str(self) / pathlib.PurePath(key).

        Note that the right hand operand here cannot be a ContainerPath.
        This is because ContainerPath objects only support absolute paths currently,
        so using one as the right hand side is likely to be an error.
        For the same reason, __rtruediv__ is undefined, meaning a ContainerPath cannot
        be the right hand side operand for arbitrary string or PathLike objects either.
        """
        return self.with_segments(self._path, key)

    def is_absolute(self) -> bool:
        return self._path.is_absolute()

    def match(self, path_pattern: str) -> bool:
        return self._path.match(path_pattern)

    def with_name(self, name: str) -> Self:
        return self.with_segments(self._path.with_name(name))

    def with_suffix(self, suffix: str) -> Self:
        return self.with_segments(self._path.with_suffix(suffix))

    def joinpath(self, *other: StrPathLike) -> Self:
        return self.with_segments(self._path, *other)

    @property
    def parents(self) -> tuple[Self, ...]:
        return tuple(self.with_segments(p) for p in self._path.parents)

    @property
    def parent(self) -> Self:
        return self.with_segments(self._path.parent)

    @property
    def parts(self) -> tuple[str, ...]:
        return self._path.parts

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suffix(self) -> str:
        return self._path.suffix

    @property
    def suffixes(self) -> list[str]:
        return self._path.suffixes

    @property
    def stem(self) -> str:
        return self._path.stem

    #########################
    # protocol Path methods #
    #########################

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
        newline: typing.Literal['', '\n', '\r', '\r\n'] | None = None,  # 3.13+
    ) -> str:
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        # # TODO: update ops so this works
        # try:
        #     with self._container.pull(
        #         self._path, encoding=encoding, errors=errors, newline=newline
        #     ) as f:
        #         return f.read()
        # except pebble.PathError as e:
        #     for error in (...):
        #         if error.matches(e):
        #             raise error.exception(self._description()) from e
        #     raise
        #
        # ## operate on bytes in memory since pull doesn't expose all the args we need
        data = self.read_bytes()
        # # efficient but doesn't error correctly on encoding mismatch
        # # also can't handle newlines
        # return data.decode(encoding=encoding, errors=errors)
        #
        # # tempfile because open somehow detects encoding mismatch
        # import tempfile
        # with tempfile.NamedTemporaryFile('wb', delete=False) as f:
        #     f.write(data)
        # with open(f.name, encoding=encoding, errors=errors, newline=newline) as f:
        #     return f.read()
        #
        # # pipe so it stays in memory -- probably (silently?) breaks for big files
        r, w = os.pipe()
        with open(w, 'wb') as f:
            f.write(data)
        with open(r, encoding=encoding, errors=errors, newline=newline) as f:
            return f.read()

    def read_bytes(self) -> bytes:
        try:
            with self._container.pull(self._path, encoding=None) as f:
                return f.read()
        except pebble.PathError as e:
            for error in (_errors.FileNotFound, _errors.IsADirectory, _errors.Permission):
                if error.matches(e):
                    raise error.exception(self._description()) from e
            raise

    def rmdir(self) -> None:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        if info.type != pebble.FileType.DIRECTORY:
            raise _errors.NotADirectory.exception(self._description())
        try:
            self._container.remove_path(self._path, recursive=False)
        except pebble.PathError as e:
            for error in (_errors.Permission, _errors.DirectoryNotEmpty):
                if error.matches(e):
                    raise error.exception(self._description()) from e
            raise

    def unlink(self, missing_ok: bool = False) -> None:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        if info.type == pebble.FileType.DIRECTORY:
            raise _errors.IsADirectory.exception(self._description())
        try:
            self._container.remove_path(self._path, recursive=False)
        except pebble.PathError as e:
            for error in (_errors.Permission,):
                if error.matches(e):
                    raise error.exception(self._description()) from e
            raise

    def iterdir(self) -> typing.Generator[Self]:
        # python < 3.13 defers NotADirectoryError to iteration time, but python 3.13 raises on call
        # for future proofing we will check on call
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        if info.type != pebble.FileType.DIRECTORY:
            raise _errors.NotADirectory.exception(self._description())
        file_infos = self._container.list_files(self._path)
        for f in file_infos:
            yield self.with_segments(f.path)

    def glob(
        self,
        pattern: StrPathLike,  # support for _StrPath added in 3.13 (was str only before)
        # *,
        # case_sensitive: bool = False,  # added in 3.12
        # recurse_symlinks: bool = False,  # added in 3.13
    ) -> Generator[Self]:
        if not isinstance(pattern, str):
            pattern = str(pattern)
        file_infos = self._container.list_files(self._path, pattern=pattern)
        for f in file_infos:
            yield self.with_segments(f.path)

    def rglob(
        self,
        pattern: StrPathLike,  # support for _StrPath added in 3.13
        # *,
        # case_sensitive: bool = False,  # added in 3.12
        # recurse_symlinks: bool = False,  # added in 3.13
    ) -> Generator[Self]:
        # NOTE: to ease implementation, this could be dropped from the v1 release
        if not isinstance(pattern, str):
            pattern = str(pattern)
        return self.rglob(f'**/{pattern}')

    def owner(self) -> str:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.user or ''

    def group(self) -> str:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.group or ''

    def exists(self) -> bool:
        return self._exists_and_matches(filetype=None)

    def is_dir(self) -> bool:
        return self._exists_and_matches(pebble.FileType.DIRECTORY)

    def is_file(self) -> bool:
        return self._exists_and_matches(pebble.FileType.FILE)

    def is_fifo(self) -> bool:
        return self._exists_and_matches(pebble.FileType.NAMED_PIPE)

    def is_socket(self) -> bool:
        return self._exists_and_matches(pebble.FileType.SOCKET)

    def _exists_and_matches(self, filetype: pebble.FileType | None) -> bool:
        try:
            info = _fileinfo.from_container_path(self)
        except FileNotFoundError:
            return False
        if filetype is None:  # we only care if the file exists
            return True
        return info.type is filetype

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
    ) -> int:
        self._container.push(
            path=self._path,
            source=data,
            make_dirs=False,
            permissions=mode,
            user=user if isinstance(user, str) else None,
            user_id=user if isinstance(user, int) else None,
            group=group if isinstance(group, str) else None,
            group_id=group if isinstance(group, int) else None,
        )
        return 0

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: typing.Literal['strict', 'ignore'] | None = None,
        # newline: typing.Literal['', '\n', '\r', '\r\n'] | None = None,  # 3.10+
        # extended with chmod + chown args
        *,
        mode: int | None = None,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> int:
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        self._container.push(
            path=self._path,
            source=bytes(data, encoding=encoding, errors=errors),
            # source=io.StringIO(data, newline=newline),  # 3.10+?
            encoding=encoding if encoding is not None else 'utf-8',
            make_dirs=False,
            permissions=mode,
            user=user if isinstance(user, str) else None,
            user_id=user if isinstance(user, int) else None,
            group=group if isinstance(group, str) else None,
            group_id=group if isinstance(group, int) else None,
        )
        return 0

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
        # extended with chown args
        *,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> None:
        if parents and not exist_ok and self.is_dir():
            raise _errors.FileExists.exception(self._description())
        elif exist_ok and not parents and not self.parent.is_dir():
            raise _errors.FileNotFound.exception(self.parent._description())
        self._container.make_dir(
            path=self._path,
            make_parents=parents or exist_ok,  # see validation above
            permissions=mode,
            user=user if isinstance(user, str) else None,
            user_id=user if isinstance(user, int) else None,
            group=group if isinstance(group, str) else None,
            group_id=group if isinstance(group, int) else None,
        )

    #############################
    # non-protocol Path methods #
    #############################

    def with_segments(self, *pathsegments: StrPathLike) -> Self:
        return type(self)(*pathsegments, container=self._container)
