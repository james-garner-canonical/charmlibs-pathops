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

"""Type-checking exclusive definitions."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import os
    from typing import Generator, Sequence

    from typing_extensions import Self, TypeAlias


Bytes: TypeAlias = 'bytes | bytearray | memoryview'
StrPathLike: TypeAlias = 'str | os.PathLike[str]'


# based on typeshed.stdlib.pathlib.PurePath
# https://github.com/python/typeshed/blob/main/stdlib/pathlib.pyi#L29
class PathProtocol(typing.Protocol):
    #############################
    # protocol PurePath methods #
    #############################

    # constructors
    # ContainerPath constructor will differ from pathlib.Path constructor
    # not part of the protocol
    # def __new__(cls, *args: _StrPath, **kwargs: object) -> Self: ...
    # NOTE: __new__ signature is version dependent
    # def __init__(self, *args): ...

    def __hash__(self) -> int: ...

    # def __reduce__(self): ...
    # ops.Container isn't pickleable itself, but we can provide a custom constructor
    # for ContainerPath that works with the unpickling protocol, and will attempt to
    # make a Container object connected to the appropriate pebble socket
    # for simplicity this will be omitted from v1 unless requested

    # comparison methods
    def __lt__(self, other: Self) -> bool: ...
    def __le__(self, other: Self) -> bool: ...
    def __gt__(self, other: Self) -> bool: ...
    def __ge__(self, other: Self) -> bool: ...
    def __eq__(self, other: object, /) -> bool: ...

    # '/' operator
    def __truediv__(self, key: StrPathLike) -> Self: ...

    # def __rtruediv__(self, key: StrPathLike) -> Self: ...
    # omitted from v1 protocol
    # doesn't seem worth supporting until (if) ContainerPath gets relative paths
    #
    # when we have relative paths, it will be meaningful to support the following:
    # def __truediv__(self, key: StrPathLike | Self) -> Self: ...
    # def __rtruediv__(self, key: StrPathLike | Self) -> Self: ...
    # `ContainerPath / (str or pathlib.Path)`, or `(str or pathlib.Path) / containerPath`
    # will result in a new ContainerPath with the same container.
    # `ContainerPath / ContainerPath` is an error if the containers are not the same,
    # otherwise it too results in a new ContainerPath with the same container.

    # def __fspath__(self) -> str: ...
    # we don't want ContainerPath to be os.PathLike

    # def __bytes__(self) -> bytes: ...
    # we don't want ContainerPath to be mistakenly used like a pathlib.Path

    # we follow the pathlib convention here and guarantee that str is a representation of
    # the path in its local filesystem
    def __str__(self) -> str: ...

    # like __str__
    def as_posix(self) -> str: ...

    # URIs
    # this doesn't seem useful and is potentially confusing,so it won't be implemented
    # likewise, the constructor (added in 3.13) won't be implemented
    # def as_uri(self) -> str: ...
    # @classmethod
    # def from_uri(uri: str) -> Self: ...

    def is_absolute(self) -> bool: ...

    # def is_reserved(self) -> bool: ...
    # this will always return False with a PosixPath. Since we assume a Linux container
    # so let's just drop it from the protocol for now

    # signature extended further in 3.12+
    # def match(self, pattern: str, * case_sensitive: bool = False) -> bool: ...
    # extended signature is not part of the protocol but may eventually be provided on
    # ContainerPath to ease compatibility with pathlib.Path on 3.12+
    def match(self, path_pattern: str) -> bool: ...

    # def full_match(self, pattern: str, * case_sensitive: bool = False) -> bool: ...
    # 3.13+
    # not part of the protocol but may eventually be provided on ContainerPath
    # to ease compatibility with pathlib.Path on 3.13+

    # def relative_to(self, other: _StrPath, /) -> Self: ...
    # this produces relative paths, which we shouldn't be using in any code designed to
    # be compatible with both machines and containers, since pebble will error on any
    # relative paths at runtime -- if users want to work with relative paths, I think
    # they should explicitly work with a PurePath rather than a ContainerPath, and then
    # construct the ContainerPath when they have the absolute path they need
    #
    # Python 3.12 deprecates the below signature, to be dropped in 3.14
    # def relative_to(self, *other: _StrPath) -> Self: ...
    # to ease future compatibility, we'd just drop support for the old signature
    # from the protocol now if it was included
    #
    # Python 3.12 further modifies the signature with an additional keyword argument
    # def relative_to(self, other: _StrPath, walk_up: bool = False) -> Self: ...
    # this would not part of the protocol but could eventually be provided on
    # ContainerPath to ease compatibility with pathlib.Path on 3.12+ if we someday
    # support relative paths

    # def is_relative_to(self, other: _StrPath) -> Self: ...  # 3.9+
    # not part of protocol but can be provided on ContainerPath implementation
    # to ease compatibility with pathlib.Path on 3.9+

    def with_name(self, name: str) -> Self: ...

    def with_suffix(self, suffix: str) -> Self: ...

    # def with_stem(self, stem: str) -> Self: ...  # 3.9+
    # not part of protocol but can be provided on ContainerPath implementation
    # to ease compatibility with pathlib.Path on 3.9+
    # could be added to the protocol if we're happy for LocalPath to double as backports

    # def with_segments(self, *pathsegments: _StrPath) -> Self: ...
    # required for 3.12+ subclassing machinery
    # not part of the protocol (otherwise LocalPath would have to backport it)
    # but it is a useful method -- given a ContainerPath with some container,
    # you can make another path with the same container cleanly, so it'll be implemented
    # on ContainerPath

    # *other cannot be a ContainerPath
    def joinpath(self, *other: StrPathLike) -> Self: ...

    @property
    def parents(self) -> Sequence[Self]: ...

    @property
    def parent(self) -> Self: ...

    @property
    def parts(self) -> tuple[str, ...]: ...

    # @property
    # def drive(self) -> str: ...
    # will always be '' for Posix -- maybe drop it from the protocol
    # so users get more useful autocompletions?

    # @property
    # def root(self) -> str: ...
    # potentially error prone -- ContainerPath.root / Path('foo') is not a ContainerPath

    # @property
    # def anchor(self) -> str: ...
    # this is drive + root

    @property
    def name(self) -> str: ...

    @property
    def suffix(self) -> str: ...

    @property
    def suffixes(self) -> list[str]: ...

    @property
    def stem(self) -> str: ...

    #########################
    # protocol Path methods #
    #########################

    # pull
    def read_text(
        self,
        # # we drop encoding and errors for a simpler API
        # encoding: str | None = None,
        # errors: typing.Literal['strict', 'ignore'] | None = None,
        # # newline is not part of the protocol since we support Python 3.8+
        # newline: typing.Literal['', '\n', '\r', '\r\n'] | None = None,  # 3.13+
    ) -> str: ...

    def read_bytes(self) -> bytes: ...

    # remove
    # these methods are problematic because Pebble
    # 1. doesn't let us distinguish in advance between dirs and symlinks to them
    # 2. doesn't provide a way not to remove an empty directory
    #
    # If provided, would have to also remove symlinks to directories
    # def rmdir(self) -> None: ...
    #
    # If provided, would either have to also remove empty directories
    # or be unable to remove symlinks to directories
    # def unlink(self, missing_ok: bool = False) -> None: ...

    # list_files
    def iterdir(self) -> typing.Iterable[Self]: ...

    def glob(
        self,
        pattern: str,  # support for _StrPath added in 3.13
        # *,
        # case_sensitive: bool = False,  # added in 3.12
        # recurse_symlinks: bool = False,  # added in 3.13
    ) -> Generator[Self]: ...

    # recursive glob is problematic because Pebble doesn't tell us whether something is a symlink
    # so we can easily recurse until we hit Pebble's api limit
    # def rglob(
    #     self,
    #     pattern: str,  # support for _StrPath added in 3.13
    #     # *,
    #     # case_sensitive: bool = False,  # added in 3.12
    #     # recurse_symlinks: bool = False,  # added in 3.13
    # ) -> Generator[Self]: ...

    # walk was only added in 3.12 -- let's not support this for now, as we'd need to
    # implement the walk logic for LocalPath as well as whatever we do for ContainerPath
    # (which will also be a bit trickier being unable to distinguish symlinks as dirs)
    # While Path.walk wraps os.walk, there are still ~30 lines of pathlib code we'd need
    # to vendor for LocalPath.walk
    # def walk(
    #     self,
    #     top_down: bool = True,
    #     on_error: typing.Callable[[OSError], None] | None = None,
    #     follow_symlinks: bool = False,  # NOTE: ContainerPath runtime error if True
    # ) -> typing.Iterator[tuple[Self, list[str], list[str]]]:
    #     # TODO: if we add a follow_symlinks option to Pebble's list_files API, we can
    #     #       then support follow_symlinks=True on supported Pebble (Juju) versions
    #     ...

    # def stat(self) -> os.stat_result: ...
    # stat follows symlinks to return information about the target
    # this may not be in v1, because we can only provide best effort completion on the
    # pebble side -- for example, we can't distinguish block and char devices, and we can't
    # detect if something is a symlink. Maybe we can provide a top-level fileinfo helper

    # def lstat(self) -> os.stat_result: ...
    # lstat tells you about the symlink rather than its target
    # pebble only tells you about the target
    # TODO: support if we add follow_symlinks to Pebble's list_files API

    def owner(self) -> str: ...

    def group(self) -> str: ...

    def exists(self) -> bool: ...  # follow_symlinks=True added in 3.12

    def is_dir(self) -> bool: ...  # follow_symlinks=True added in 3.13

    def is_file(self) -> bool: ...  # follow_symlinks=True added in 3.13

    # def is_mount(self) -> bool: ...
    # pebble doesn't support this

    # def is_symlink(self) -> bool: ...
    # pebble doesn't support this

    # def is_junction(self) -> bool: ...
    # 3.12
    # this will always be False in ContainerPath since we assume a Linux container
    # so let's just drop it from the protocol for now

    def is_fifo(self) -> bool: ...

    def is_socket(self) -> bool: ...

    # is_block_device and is_char_device are problematic because pebble only tells us if
    # it's a device at all. We can provide an is_device module level helper if needed.
    # def is_block_device(self) -> bool: ...
    # def is_char_device(self) -> bool: ...

    ################################################################################
    # these concrete methods are currently ruled out due to lack of Pebble support #
    ################################################################################

    # def chmod
    # pebble sets mode on creation
    # can't provide a separate method
    # needs to be argument for other functions
    # (same treatment needed for chown)

    # link creation, modification, target retrieval
    # pebble doesn't support link manipulation
    # def hardlink_to
    # def symlink_to
    # def lchmod
    # def readlink
    # def resolve

    # def samefile
    # pebble doesn't return device and i-node number
    # can't provide the same semantics

    # def open
    # the semantics would be different due to needing to make a local copy

    # def touch
    # would have to pull down the existing file and push it back up just to set mtime

    ##################
    # relative paths #
    ##################

    # OPINION: we shouldn't support relative paths in v1 (if ever)
    #
    # if we support relative paths, we'd need to implicitly call absolute before every
    # call that goes to pebble, and it's not clear whether it's a good idea to implement
    # cwd, which absolute would depend on -- we'd have to pebble exec cwd, which wouldn't
    # work in certain images (bare rocks)
    #
    # I think it would be fine for v1 to only support absolute paths, raising an error
    # on file operations with relative paths

    # the following methods would require us to either hardcode cwd or use a pebble.exec
    # def cwd
    # typically /root in container
    # do we need to query this each time? can we hardcode it?
    # def absolute
    # interpret relative to cwd

    # the following methods would require us to either hardcode home or use a pebble.exec
    # def home
    # typically /root in container
    # do we need to query this each time? can we hardcode it?
    # def expanduser
    # '~' in parts becomes self.home

    ##################################################
    # protocol Path methods with extended signatures #
    ##################################################

    # push
    def write_bytes(
        self,
        data: bytes,
        # extended with chmod + chown args:
        *,
        mode: int | None = None,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> int: ...

    def write_text(
        self,
        data: str,
        # # we drop encoding and errors for a simpler API
        # encoding: str | None = None,
        # errors: typing.Literal['strict', 'ignore'] | None = None,
        # # newline is not part of the protocol since we support Python 3.8+
        # newline: typing.Literal['', '\n', '\r', '\r\n'] | None = None,  # 3.10+
        # extended with chmod + chown args:
        *,
        mode: int | None = None,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> int: ...

    # make_dir
    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
        # extended with chown args:
        *,
        user: str | int | None = None,
        group: str | int | None = None,
    ) -> None: ...
