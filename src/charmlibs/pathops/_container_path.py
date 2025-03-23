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

import errno
import pathlib
import re
import typing

import ops
from ops import pebble

from . import _constants, _errors, _fileinfo

if typing.TYPE_CHECKING:
    from typing import Generator, Literal

    from typing_extensions import Self

    from ._types import Bytes, StrPathLike


class RelativePathError(ValueError):
    """ContainerPath only supports absolute paths.

    This is because Pebble only works with absolute paths. Relative path support
    will likely remain unavailable at least until Pebble supports relative paths.
    In the meantime, use absolute paths.
    """


class ContainerPath:
    r"""Implementation of :class:`PathProtocol` for Juju Charm workload containers.

    Args:
        \*parts: :class:`str` or :class:`os.PathLike`.
        container: :class:`ops.Container` used to communicate with workload container.
            Required, keyword only argument.

    Raises:
        RelativePathError: If instantiated with a relative path.

    ::

        ContainerPath(pathlib.Path('/foo'), container=self.unit.get_container('c'))
        ContainerPath('/', 'foo', container=self.unit.get_container('c'))
    """

    def __init__(self, *parts: StrPathLike, container: ops.Container) -> None:
        self._container = container
        self._path = pathlib.PurePosixPath(*parts)
        if not self._path.is_absolute():
            raise RelativePathError(
                f'ContainerPath arguments resolve to relative path: {self._path}'
            )

    #############################
    # protocol PurePath methods #
    #############################

    def __hash__(self) -> int:
        """Hash on (container-name, path) for efficiency."""
        return hash((self._container.name, self._path))

    def __repr__(self) -> str:
        """Return a string representation including the class, path string, and container name.

        ::
            repr(ContainerPath('/', 'foo', 'bar', container=self.unit.get_container('c')))
            # "ContainerPath('/foo/bar', container=<ops.Container 'c'>)"
        """
        container_repr = f'<ops.Container {self._container.name!r}>'
        return f"{type(self).__name__}('{self._path}', container={container_repr})"

    def __str__(self) -> str:
        """Return the string representation of the path in the container.

        This is equivalent to the string representation of the :class:`pathlib.PurePath` this
        :class:`ContainerPath` was instatiated with.
        """
        return self._path.__str__()

    def as_posix(self) -> str:
        """Return the string representation of the path in the container."""
        return self._path.__str__()

    def __lt__(self, other: Self) -> bool:
        """Compare paths only if other is a ContainerPath on the same container.

        To sort collections of mixed paths, consider using the :func:`str` as the key to sort
        purely by the path, or :func:`repr` to sort primarily by path class, secondarily by path,
        and thirdly by container name.
        """
        if not self._can_compare(other):
            return NotImplemented
        return self._path < other._path

    def __le__(self, other: Self) -> bool:
        """Compare paths only if other is a ContainerPath on the same container.

        To sort collections of mixed paths, consider using the :func:`str` as the key to sort
        purely by the path, or :func:`repr` to sort primarily by path class, secondarily by path,
        and thirdly by container name.
        """
        if not self._can_compare(other):
            return NotImplemented
        return self._path <= other._path

    def __gt__(self, other: Self) -> bool:
        """Compare paths only if other is a ContainerPath on the same container.

        To sort collections of mixed paths, consider using the :func:`str` as the key to sort
        purely by the path, or :func:`repr` to sort primarily by path class, secondarily by path,
        and thirdly by container name.
        """
        if not self._can_compare(other):
            return NotImplemented
        return self._path > other._path

    def __ge__(self, other: Self) -> bool:
        """Compare paths only if other is a ContainerPath on the same container.

        To sort collections of mixed paths, consider using the :func:`str` as the key to sort
        purely by the path, or :func:`repr` to sort primarily by path class, secondarily by path,
        and thirdly by container name.
        """
        if not self._can_compare(other):
            return NotImplemented
        return self._path >= other._path

    def _can_compare(self, other: object) -> bool:
        return isinstance(other, ContainerPath) and other._container.name == self._container.name

    def __eq__(self, other: object, /) -> bool:
        """Compare paths if other is a ContainerPath on the same container, else return False.

        To explicitly compare paths, consider using :func:``str`` to get the canonical path string,
        or create a :class:`ContainerPath` with the same container using :meth:`with_segments`.
        """
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return False
        return self._path == other._path

    def __truediv__(self, key: StrPathLike) -> Self:
        """Return a new ContainerPath with the same container and the joined path.

        The joined path is equivalent to ``str(self) / pathlib.PurePath(key)``.

        .. warning::
            ``__rtruediv__`` is not supported, as :class:`ContainerPath` only supports absolute
            paths. Since an absolute path as the right hand operand will completely replace the
            left hand path, this is mostly likely to be a user error, so it isn't supported.
        """
        return self.with_segments(self._path, key)

    def is_absolute(self) -> bool:
        """Return True if the path is absolute (has a root), which is always the case.

        .. note::
            Always ``True``, since initialising a :class:`ContainerPath` with a non-absolute
            path will result in a :class:`RelativePathError`.
        """
        return self._path.is_absolute()

    def match(self, path_pattern: str) -> bool:
        """Return true if this path matches the given pattern.

        If the pattern is relative, matching is done from the right; otherwise, the entire
        path is matched. The recursive wildcard ``'**'`` is **not** supported by this method.

        .. warning::
            Only the path is matched against, the container is not considered.
        """
        return self._path.match(path_pattern)

    def with_name(self, name: str) -> Self:
        """Return a new ContainerPath, with the same container, but with the path name replaced.

        The name is the last component of the path, including any suffixes.

        ::
            path = ContainerPath('/', 'foo', 'bar.txt', container=self.unit.get_container('c'))
            repr(path.with_name('baz.bin'))
            # ContainerPath('/foo/baz.bin', container=<ops.Container 'c'>)"
        """
        return self.with_segments(self._path.with_name(name))

    def with_suffix(self, suffix: str) -> Self:
        """Return a new ContainerPath with the same container and the suffix changed.

        If the original path had no suffix, the new suffix is added.
        The new suffix must start with '.', unless the new suffix is an empty string,
        in which case the original suffix (if there was one) is removed ('.' included).

        ::
            path = ContainerPath('/', 'foo', 'bar.txt.zip', container=self.unit.get_container('c'))
            repr(path.with_suffix('.tar.gz'))
            # ContainerPath('/foo/bar.txt.tar.gz', container=<ops.Container 'c'>)"
            repr(path.with_suffix(''))
            # ContainerPath('/foo/bar.txt', container=<ops.Container 'c'>)"
        """
        return self.with_segments(self._path.with_suffix(suffix))

    def joinpath(self, *other: StrPathLike) -> Self:
        r"""Return a new ContainerPath with the same container and the new args joined to its path.

        Args:
            other: Any number of :class:`str` or :class:`os.PathLike` objects.
                If zero are provided, an effective copy of this :class:`ContainerPath` object is
                returned. \*other is joined to this object's path as with :func:`os.path.join`.
                This means that if any member of other is an absolute path, all the previous
                components, including this object's path, are dropped entirely.

        Returns:
            A new :class:`ContainerPath` with the same :class:`ops.Container` object, with its path
            updated with \*other as follows. For each item in other, if it is a relative path, it
            is appended to the current path. If it is an absolute path, it replaces the current
            path.

        .. warning::
            :class:`ContainerPath` is not :class:`os.PathLike`. A :class:`ContainerPath` instance
            is not a valid value for ``other``, and will result in an error.
        """
        return self.with_segments(self._path, *other)

    @property
    def parents(self) -> tuple[Self, ...]:
        """A sequence of this path's logical parents. Each parent is a :class:`ContainerPath`."""
        return tuple(self.with_segments(p) for p in self._path.parents)

    @property
    def parent(self) -> Self:
        """The logical parent of this path, as a :class:`ContainerPath`."""
        return self.with_segments(self._path.parent)

    @property
    def parts(self) -> tuple[str, ...]:
        """A sequence of the components in the filesystem path. The components are strings."""
        return self._path.parts

    @property
    def name(self) -> str:
        """The final path component, or an empty string if this is the root path."""
        return self._path.name

    @property
    def suffix(self) -> str:
        """The path name's last suffix (if it has any) including the leading ``'.'``.

        If the path name doesn't have a suffix, the result is an empty string.
        """
        return self._path.suffix

    @property
    def suffixes(self) -> list[str]:
        r"""A list of the path name's suffixes, or an empty list if it doesn't have any.

        Each suffix includes the leading ``'.'``.
        """
        return self._path.suffixes

    @property
    def stem(self) -> str:
        """The path name, minus its last suffix.

        :meth:`name` == :meth:`stem` + :meth:`suffix`
        """
        return self._path.stem

    #########################
    # protocol Path methods #
    #########################

    def read_text(self, *, newline: str | None = None) -> str:
        r"""Read a remote file as text and return the contents as a string.

        .. note::
            Compared to pathlib.Path.read_text, this method drops the encoding and errors args.
            The encoding is assumed to be utf-8, and any errors encountered will be raised.

        Args:
            newline: if ``None`` (default), all newlines ``('\r\n', '\r', '\n')`` are replaced
                with ``'\n'``. Otherwise the file contents are returned unmodified.

        Returns:
            The contents of the the path as a string.

        Raises:
            FileNotFoundError: if the parent directory does not exist.
            IsADirectoryError: if the target is a directory.
            PermissionError: if the Pebble user does not have permissions for the operation.
            ops.pebble.ConnectionError: if the remote Pebble client cannot be reached.
        """
        text = self._pull(text=True)
        if newline is None:
            return re.sub(r'\r\n|\r', '\n', text)
        return text

    def read_bytes(self) -> bytes:
        """Read a remote file as bytes and return the contents.

        Returns:
            The contents of the the path as byes.

        Raises:
            FileNotFoundError: if the parent directory does not exist.
            IsADirectoryError: if the target is a directory.
            PermissionError: if the Pebble user does not have permissions for the operation.
            ops.pebble.ConnectionError: if the remote Pebble client cannot be reached.
        """
        return self._pull(text=False)

    @typing.overload
    def _pull(self, *, text: Literal[True]) -> str: ...
    @typing.overload
    def _pull(self, *, text: Literal[False] = False) -> bytes: ...
    def _pull(self, *, text: bool = False):
        encoding = 'utf-8' if text else None
        try:
            with self._container.pull(self._path, encoding=encoding) as f:
                return f.read()
        except pebble.PathError as e:
            msg = repr(self)
            _errors.raise_if_matches_file_not_found(e, msg=msg)
            _errors.raise_if_matches_is_a_directory(e, msg=msg)
            _errors.raise_if_matches_permission(e, msg=msg)
            raise

    def iterdir(self) -> typing.Generator[Self]:
        """Yield :class:`ContainerPath` objects corresponding to the directory's contents.

        There are no guarantees about the order of the children. The special entries
        ``'.'`` and ``'..'`` are not included.

        .. note::
            :class:`NotADirectoryError` is raised (if appropriate) when ``iterdir()`` is called.
            This follows the behaviour of :meth:`pathlib.Path.iterdir` in Python 3.13+.
            Previous versions deferred the error until the generator was consumed.

        Raises:
            FileNotFoundError: If this path does not exist.
            NotADirectoryError: If this path is not a directory.
            PermissionError: If the local or remote user does not have appropriate permissions.
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """

        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        if info.type != pebble.FileType.DIRECTORY:
            _errors.raise_not_a_directory(repr(self))
        file_infos = self._container.list_files(self._path)
        for f in file_infos:
            yield self.with_segments(f.path)

    def glob(self, pattern: StrPathLike) -> Generator[Self]:
        r"""Iterate over this directory and yield all paths matching the provided pattern.

        For example, ``path.glob('*.txt')``, ``path.glob('*/foo.txt')``.

        .. warning::
            Recursive matching using the ``'**'`` pattern is not supported.

        Args:
            pattern: The :class:`str` or :class:`os.PathLike` pattern to match against. It must be
                a relative pattern, that is it cannot begin with ``'/'``.

        Returns:
            A generator yielding :class:`ContainerPath` objects, corresponding to those of its
            children which match the pattern. If this path is not a directory, there will be no
            matches.

        Raises:
            FileNotFoundError: If this path does not exist.
            NotImplementedError: If pattern is an absolute path, or if it uses the ``'**'`` pattern.
            PermissionError: If the remote user does not have appropriate permissions.
            ValueError: If the pattern is invalid.
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._glob(pattern)

    def _glob(self, pattern: StrPathLike, skip_is_dir: bool = False) -> Generator[Self]:
        pattern_path = pathlib.PurePosixPath(pattern)
        if pattern_path.is_absolute():
            raise NotImplementedError('Non-relative paths are unsupported.')
        elif pattern_path == pathlib.PurePosixPath('.'):
            raise ValueError(f'Unacceptable pettern: {pattern!r}')
        *pattern_parents, pattern_itself = pattern_path.parts
        if '**' in pattern_parents:
            raise NotImplementedError('Recursive glob is not supported.')
        if '**' in str(pattern):
            raise ValueError("Invalid pattern: '**' can only be an entire path component")
        if not skip_is_dir and not self.is_dir():
            yield from ()
            return
        if not pattern_parents:
            file_infos = self._container.list_files(self._path, pattern=pattern_itself)
            for f in file_infos:
                yield self.with_segments(f.path)
            return
        first, *rest = pattern_parents
        next_pattern = pathlib.PurePosixPath(*rest, pattern_itself)
        if first == '*':
            for container_path in self.iterdir():
                if container_path.is_dir():
                    yield from container_path._glob(next_pattern, skip_is_dir=True)
        elif '*' in first:
            for container_path in self._glob(first):
                if container_path.is_dir():
                    yield from container_path._glob(next_pattern, skip_is_dir=True)
        else:
            yield from (self / first)._glob(next_pattern)

    def owner(self) -> str:
        """Return the user name of the file owner.

        Raises:
            FileNotFoundError: If the path does not exist.
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.user or ''

    def group(self) -> str:
        """Return the group name of the file.

        Raises:
            FileNotFoundError: If the path does not exist.
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.group or ''

    def exists(self) -> bool:
        """Whether this path exists.

        Will follow symlinks to determine if the symlink target exists. This means that exists
        will return False for a broken symlink.

        Raises:
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._exists_and_matches(filetype=None)

    def is_dir(self) -> bool:
        """Whether this path exists and is a directory.

        Will follow symlinks to determine if the symlink target exists and is a directory.

        Raises:
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._exists_and_matches(pebble.FileType.DIRECTORY)

    def is_file(self) -> bool:
        """Whether this path exists and is a regular file.

        Will follow symlinks to determine if the symlink target exists and is a regular file.

        Raises:
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._exists_and_matches(pebble.FileType.FILE)

    def is_fifo(self) -> bool:
        """Whether this path exists and is a named pipe (aka FIFO).

        Will follow symlinks to determine if the symlink target exists and is a named pipe.

        Raises:
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._exists_and_matches(pebble.FileType.NAMED_PIPE)

    def is_socket(self) -> bool:
        """Whether this path exists and is a socket.

        Will follow symlinks to determine if the symlink target exists and is a socket.

        Raises:
            ops.pebble.ConnectionError: If the remote container cannot be reached.
        """
        return self._exists_and_matches(pebble.FileType.SOCKET)

    def _exists_and_matches(self, filetype: pebble.FileType | None) -> bool:
        info = self._try_get_fileinfo()
        if info is None:
            return False
        if filetype is None:  # we only care if the file exists
            return True
        return info.type is filetype

    def _try_get_fileinfo(self) -> pebble.FileInfo | None:
        try:
            return _fileinfo.from_container_path(self)
        except FileNotFoundError:
            pass
        except OSError as e:
            if e.errno != errno.ELOOP:
                raise
            # else: too many levels of symbolic links
        return None

    ##################################################
    # protocol Path methods with extended signatures #
    ##################################################

    def write_bytes(
        self,
        data: Bytes,
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        """Write the provided data to the corresponding path in the remote container.

        .. note::
            Compared to :meth:`pathlib.Path.write_bytes`, this method adds ``mode``, ``user``
            and ``group`` args. These are forwarded to Pebble, which sets these on file creation.

        Args:
            data: The bytes to write. If data is a bytearray or memoryview, it will be converted
                to bytes in memory first.
            mode: The permissions to set on the file.
            user: The name of the user to set for the file.
            group: The name of the group to set for the file.

        Returns: The number of bytes written.

        Raises:
            FileNotFoundError: if the parent directory does not exist.
            LookupError: if the user or group is unknown.
            NotADirectoryError: if the parent exists as a non-directory file.
            PermissionError: if the Pebble user does not have permissions for the operation.
            ops.pebble.ConnectionError: if the remote Pebble client cannot be reached.
        """
        if isinstance(data, (bytearray, memoryview)):
            # TODO: update ops to correctly test for bytearray and memoryview in push
            data = bytes(data)
        try:
            self._container.push(
                path=self._path,
                source=data,
                make_dirs=False,
                permissions=mode,
                user=user if isinstance(user, str) else None,
                group=group if isinstance(group, str) else None,
            )
        except pebble.PathError as e:
            _errors.raise_if_matches_lookup(e, msg=e.message)
            msg = repr(self)
            _errors.raise_if_matches_file_not_found(e, msg=msg)
            _errors.raise_if_matches_not_a_directory(e, msg=msg)
            _errors.raise_if_matches_permission(e, msg=msg)
            raise
        return len(data)

    def write_text(
        self,
        data: str,
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        """Write the provided string to the corresponding path in the remote container.

        .. note::
            Compared to :meth:`pathlib.Path.write_text`, this method drops the ``encoding`` and
            ``errors`` args to simplify the API. The Python 3.10+ ``newline`` argument is not
            implemented. The args ``mode``, ``user`` and ``group`` are added, and are forwarded
            to Pebble, which sets these on file creation.

        Args:
            data: The string to write. Will be encoded as utf-8, raising any errors.
                Newlines are not modified on writing.
            mode: The permissions to set on the file.
            user: The name of the user to set for the file.
            group: The name of the group to set for the file.

        Returns: The number of bytes written.

        Raises:
            LookupError: if the user or group is unknown.
            FileNotFoundError: if the parent directory does not exist.
            NotADirectoryError: if the parent exists as a non-directory file.
            PermissionError: if the Pebble user does not have permissions for the operation.
            ops.pebble.ConnectionError: if the remote Pebble client cannot be reached.
        """
        encoded_data = data.encode()
        return self.write_bytes(encoded_data, mode=mode, user=user, group=group)

    def mkdir(
        self,
        mode: int = _constants.DEFAULT_MKDIR_MODE,
        parents: bool = False,
        exist_ok: bool = False,
        *,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        if parents and not exist_ok and self.exists():
            raise _errors.raise_file_exists(repr(self))
        elif not parents and exist_ok and not self.parent.exists():
            _errors.raise_file_not_found(repr(self.parent))
        if parents:
            # create parents with default permissions, following pathlib
            self._container.make_dir(
                path=self._path.parent,
                make_parents=True,
                permissions=_constants.DEFAULT_MKDIR_MODE,
            )
        try:
            self._container.make_dir(
                path=self._path,
                make_parents=exist_ok,  # parents created separately above
                permissions=mode,
                user=user if isinstance(user, str) else None,
                group=group if isinstance(group, str) else None,
            )
        except pebble.PathError as e:
            _errors.raise_if_matches_lookup(e, msg=e.message)
            msg = repr(self)
            if _errors.matches_not_a_directory(e):
                # target exists and isn't a directory, or parent isn't a directory
                if not self.parent.is_dir():
                    _errors.raise_not_a_directory(msg=msg, from_=e)
                _errors.raise_file_exists(repr(self), from_=e)
            _errors.raise_if_matches_file_exists(e, msg=msg)
            _errors.raise_if_matches_file_not_found(e, msg=msg)
            _errors.raise_if_matches_permission(e, msg=msg)
            raise

    #############################
    # non-protocol Path methods #
    #############################

    def with_segments(self, *pathsegments: StrPathLike) -> Self:
        """Return a new ContainerPath with the same container, with its entire path replaced.

        All :class:`ContainerPath` methods returning new :class:`ContainerPath` instances do so by
        calling this method, including :meth:`parent` and :meth:`parents`. Subclasses can therefore
        customise the behaviour of all these methods by overriding only this method. The same is
        true of :class:`pathlib.Path` in Python 3.12+.
        """
        return type(self)(*pathsegments, container=self._container)
