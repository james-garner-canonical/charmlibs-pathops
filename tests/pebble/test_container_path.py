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

"""Tests that use a real Pebble to test ContainerPath."""

from __future__ import annotations

import operator
import os
import pathlib
import typing

import ops
import pytest
from ops import pebble

import stuff
from charmlibs.pathops import ContainerPath, LocalPath, RelativePathError

if typing.TYPE_CHECKING:
    from typing import Callable


pytestmark = pytest.mark.skipif(
    os.getenv('RUN_REAL_PEBBLE_TESTS') != '1', reason='RUN_REAL_PEBBLE_TESTS not set'
)


class TestInit:
    def test_ok(self, container: ops.Container):
        ContainerPath('/', container=container)
        ContainerPath(pathlib.Path('/'), container=container)
        ContainerPath(LocalPath('/'), container=container)

    def test_given_relative_path_then_raises(self, container: ops.Container):
        assert issubclass(RelativePathError, ValueError)
        with pytest.raises(RelativePathError):
            ContainerPath('.', container=container)
        with pytest.raises(RelativePathError):
            ContainerPath(pathlib.Path('.'), container=container)
        with pytest.raises(RelativePathError):
            ContainerPath(LocalPath('.'), container=container)

    def test_given_container_path_then_raises(self, container: ops.Container):
        container_path = ContainerPath('/', container=container)
        with pytest.raises(TypeError):
            ContainerPath(container_path, container=container)  # pyright: ignore[reportArgumentType]


#####################
# pure path methods #
#####################


class TestHash:
    def test_ok(self, container: ops.Container):
        paths = ('/foo', '/foo/bar', '/foo/bar/byte')
        di = {ContainerPath(path, container=container): path for path in paths}
        for path in paths:
            assert di[ContainerPath(path, container=container)] == path


class TestStr:
    def test_ok(self, container: ops.Container):
        path = pathlib.Path('/foo/bar')
        container_path = ContainerPath(path, container=container)
        assert pathlib.Path(str(container_path)) == path
        assert pathlib.Path(container_path.as_posix()) == path
        assert str(container_path) == str(path)
        assert container_path.as_posix() == path.as_posix()


class TestComparison:
    @pytest.mark.parametrize(
        ('left', 'right'),
        (
            ('/foo', '/bar'),
            ('/foo', '/foo/bar'),
            ('/foo/bar', '/foo/bartholemew'),
            ('/foo/bar', '/foob/ar'),
        ),
    )
    @pytest.mark.parametrize(
        'operation', (operator.lt, operator.le, operator.gt, operator.ge, operator.eq)
    )
    def test_ok(
        self,
        operation: Callable[[object, object], bool],
        left: str,
        right: str,
        container: ops.Container,
    ):
        container_path = ContainerPath(left, container=container)
        container_result = operation(container_path, container_path.with_segments(right))
        pathlib_result = operation(pathlib.PurePosixPath(left), pathlib.PurePosixPath(right))
        assert container_result == pathlib_result

    def test_when_other_isnt_container_path_then_equality_returns_false(
        self, container: ops.Container
    ):
        assert ContainerPath('/', container=container) != LocalPath('/')
        assert ContainerPath('/', container=container) != '/'

    def test_when_containers_are_different_then_equality_returns_false(
        self, container: ops.Container, another_container: ops.Container
    ):
        container_path = ContainerPath('/', container=container)
        another_container_path = ContainerPath('/', container=another_container)
        assert container_path != another_container_path

    @pytest.mark.parametrize('operation', (operator.lt, operator.le, operator.gt, operator.ge))
    def test_when_containers_are_different_then_inequality_raises_type_error(
        self,
        operation: Callable[[object, object], bool],
        container: ops.Container,
        another_container: ops.Container,
    ):
        with pytest.raises(TypeError):
            operation(
                ContainerPath('/', container=container),
                ContainerPath('/', container=another_container),
            )

    @pytest.mark.parametrize('operation', (operator.lt, operator.le, operator.gt, operator.ge))
    def test_when_other_isnt_container_path_then_inequality_raises_type_error(
        self, operation: Callable[[object, object], bool], container: ops.Container
    ):
        with pytest.raises(TypeError):
            operation(ContainerPath('/', container=container), LocalPath('/'))
        with pytest.raises(TypeError):
            operation(ContainerPath('/', container=container), '/')


class TestTrueDiv:
    @pytest.mark.parametrize(
        ('left', 'right'),
        (
            ('/', 'foo'),
            ('/foo', 'foo/bar'),
            ('/foo/bar', 'bartholemew'),
            ('/foo/bar', '/foo/bartholemew'),
        ),
    )
    def test_ok(self, left: str, right: str, container: ops.Container):
        pathlib_path = pathlib.Path(left)
        container_path = ContainerPath(left, container=container)
        assert str(container_path / right) == str(pathlib_path / right)
        assert str(container_path / pathlib.Path(right)) == str(pathlib_path / pathlib.Path(right))
        assert str(container_path / LocalPath(right)) == str(pathlib_path / LocalPath(right))

    def test_when_container_path_is_right_hand_side_then_truediv_raises_type_error(
        self, container: ops.Container
    ):
        container_path = ContainerPath('/foo', container=container)
        with pytest.raises(TypeError):
            '/foo' / container_path  # type: ignore
        with pytest.raises(TypeError):
            pathlib.Path('/foo') / container_path  # type: ignore
        with pytest.raises(TypeError):
            LocalPath('/foo') / container_path  # type: ignore
        with pytest.raises(TypeError):
            container_path / container_path  # type: ignore


class TestIsAbsolute:
    def test_ok(self, container: ops.Container):
        assert ContainerPath('/', container=container).is_absolute()
        # no further tests needed unless the case below fails
        # which will mean we've added relative path support
        with pytest.raises(RelativePathError):
            ContainerPath('.', container=container)


class TestMatch:
    @pytest.mark.parametrize('path_str', ('/', '/foo', '/foo/bar.txt', '/foo/bar_txt'))
    @pytest.mark.parametrize('pattern', ('', '*', '**/bar', '/foo/bar*', '*.txt'))
    def test_ok(self, path_str: str, pattern: str, container: ops.Container):
        container_path = ContainerPath(path_str, container=container)
        pathlib_path = pathlib.Path(path_str)
        try:
            pathlib_result = pathlib_path.match(pattern)
        except ValueError:
            with pytest.raises(ValueError):
                container_path.match(pattern)
        else:
            assert container_path.match(pattern) == pathlib_result

    def test_when_pattern_is_container_path_then_raises_type_error(self, container: ops.Container):
        container_path = ContainerPath('/', container=container)
        with pytest.raises(TypeError):
            container_path.match(container_path)  # type: ignore


# TODO: remaining pure path methods


#########################
# concrete path methods #
#########################


# TODO: remaining concrete path methods


class TestReadText:
    ERROR_SETTINGS = ('strict', 'ignore', 'replace')

    @pytest.mark.parametrize('filename', stuff.TEXT_FILES)
    @pytest.mark.parametrize('error_setting', ERROR_SETTINGS)
    def test_ok(
        self,
        container: ops.Container,
        readable_interesting_dir: pathlib.Path,
        filename: str,
        error_setting: str,
    ):
        pathlib_result = pathlib.Path(readable_interesting_dir, filename).read_text(
            errors=error_setting
        )
        container_result = ContainerPath(
            readable_interesting_dir, filename, container=container
        ).read_text(errors=error_setting)
        assert container_result == pathlib_result

    @pytest.mark.parametrize(
        ('encoding', 'filename'),
        (
            (None, next(iter(stuff.TEXT_FILES))),
            ('utf-8', next(iter(stuff.UTF8_BINARY_FILES))),
            ('utf-16', next(iter(stuff.UTF16_BINARY_FILES))),
        ),
    )
    def test_when_explicit_encoding_used_then_ok(
        self,
        container: ops.Container,
        readable_interesting_dir: pathlib.Path,
        encoding: str,
        filename: str,
    ):
        pathlib_result = pathlib.Path(readable_interesting_dir, filename).read_text(
            encoding=encoding
        )
        container_result = ContainerPath(
            readable_interesting_dir, filename, container=container
        ).read_text(encoding=encoding)
        assert container_result == pathlib_result

    @pytest.mark.parametrize(
        ('encoding', 'filename'),
        (
            (None, next(iter(stuff.UTF16_BINARY_FILES))),
            ('utf-8', next(iter(stuff.UTF16_BINARY_FILES))),
            ('utf-16', next(iter(stuff.UTF8_BINARY_FILES))),
        ),
    )
    def test_when_wrong_encoding_used_then_raises_unicode_error(
        self,
        container: ops.Container,
        readable_interesting_dir: pathlib.Path,
        encoding: str,
        filename: str,
    ):
        with pytest.raises(UnicodeError):
            pathlib.Path(readable_interesting_dir, filename).read_text(encoding=encoding)
        with pytest.raises(UnicodeError):
            ContainerPath(readable_interesting_dir, filename, container=container).read_text(
                encoding=encoding
            )

    def test_when_file_is_directory_then_raises_is_a_directory_error(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        with pytest.raises(IsADirectoryError):
            pathlib.Path(readable_interesting_dir).read_text()
        with pytest.raises(IsADirectoryError):
            ContainerPath(readable_interesting_dir, container=container).read_text()

    def test_when_file_doesnt_exist_then_raises_file_not_found_error(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        with pytest.raises(FileNotFoundError):
            pathlib.Path(readable_interesting_dir, stuff.MISSING_FILE_NAME).read_text()
        with pytest.raises(FileNotFoundError):
            ContainerPath(
                readable_interesting_dir, stuff.MISSING_FILE_NAME, container=container
            ).read_text()

    def test_when_pebble_connection_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'pull', stuff.Mocks.raises_connection_error)
            with pytest.raises(pebble.ConnectionError):
                ContainerPath('/', container=container).read_text()

    def test_when_unknown_path_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'pull', stuff.Mocks.raises_unknown_path_error)
            with pytest.raises(pebble.PathError):
                ContainerPath('/', container=container).read_text()


class TestReadBytes:
    @pytest.mark.parametrize('filename', [*stuff.TEXT_FILES, *stuff.BINARY_FILES])
    def test_ok(
        self,
        container: ops.Container,
        readable_interesting_dir: pathlib.Path,
        filename: str,
    ):
        pathlib_result = pathlib.Path(readable_interesting_dir, filename).read_bytes()
        container_result = ContainerPath(
            readable_interesting_dir, filename, container=container
        ).read_bytes()
        assert container_result == pathlib_result

    def test_when_file_is_directory_then_raises_is_a_directory_error(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        with pytest.raises(IsADirectoryError):
            pathlib.Path(readable_interesting_dir).read_bytes()
        with pytest.raises(IsADirectoryError):
            ContainerPath(readable_interesting_dir, container=container).read_bytes()

    def test_when_file_doesnt_exist_then_raises_file_not_found_error(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        with pytest.raises(FileNotFoundError):
            pathlib.Path(readable_interesting_dir, stuff.MISSING_FILE_NAME).read_bytes()
        with pytest.raises(FileNotFoundError):
            ContainerPath(
                readable_interesting_dir, stuff.MISSING_FILE_NAME, container=container
            ).read_bytes()

    def test_when_pebble_connection_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'pull', stuff.Mocks.raises_connection_error)
            with pytest.raises(pebble.ConnectionError):
                ContainerPath('/', container=container).read_bytes()

    def test_when_unknown_path_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'pull', stuff.Mocks.raises_unknown_path_error)
            with pytest.raises(pebble.PathError):
                ContainerPath('/', container=container).read_bytes()


class TestIterDir:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        local_path = LocalPath(readable_interesting_dir)
        local_list = list(local_path.iterdir())
        local_set = {str(p) for p in local_list}
        assert len(local_list) == len(local_set)
        container_path = ContainerPath(readable_interesting_dir, container=container)
        container_list = list(container_path.iterdir())
        container_set = {str(p) for p in container_list}
        assert len(container_list) == len(container_set)
        assert local_set == container_set

    def test_given_not_exists_when_iterdir_then_raises_file_not_found(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        path = readable_interesting_dir / stuff.MISSING_FILE_NAME
        local_path = LocalPath(path)
        with pytest.raises(FileNotFoundError) as ctx:
            next(local_path.iterdir())
        print(ctx.value)
        container_path = ContainerPath(path, container=container)
        with pytest.raises(FileNotFoundError) as ctx:
            next(container_path.iterdir())
        print(ctx.value)

    def test_given_not_a_directory_when_iterdir_then_raises_not_a_directory(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path
    ):
        path = readable_interesting_dir / 'empty_file.bin'
        local_path = LocalPath(path)
        with pytest.raises(NotADirectoryError) as ctx:
            next(local_path.iterdir())
        print(ctx.value)
        container_path = ContainerPath(path, container=container)
        with pytest.raises(NotADirectoryError) as ctx:
            next(container_path.iterdir())
        print(ctx.value)


# TODO: remaining concrete path methods (glob, rglob, container, group)


class TestExists:
    @pytest.mark.parametrize('filename', stuff.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        pathlib_path = readable_interesting_dir / filename
        container_path = ContainerPath(readable_interesting_dir, filename, container=container)
        pathlib_result = pathlib_path.exists()
        container_result = container_path.exists()
        assert container_result == pathlib_result


class TestIsDir:
    @pytest.mark.parametrize('filename', stuff.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        pathlib_path = readable_interesting_dir / filename
        container_path = ContainerPath(readable_interesting_dir, filename, container=container)
        pathlib_result = pathlib_path.is_dir()
        container_result = container_path.is_dir()
        assert container_result == pathlib_result


class TestIsFile:
    @pytest.mark.parametrize('filename', stuff.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        pathlib_path = readable_interesting_dir / filename
        container_path = ContainerPath(readable_interesting_dir, filename, container=container)
        pathlib_result = pathlib_path.is_file()
        container_result = container_path.is_file()
        assert container_result == pathlib_result


class TestIsFifo:
    @pytest.mark.parametrize('filename', stuff.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        pathlib_path = readable_interesting_dir / filename
        container_path = ContainerPath(readable_interesting_dir, filename, container=container)
        pathlib_result = pathlib_path.is_fifo()
        container_result = container_path.is_fifo()
        assert container_result == pathlib_result


class TestIsSocket:
    @pytest.mark.parametrize('filename', stuff.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        pathlib_path = readable_interesting_dir / filename
        container_path = ContainerPath(readable_interesting_dir, filename, container=container)
        pathlib_result = pathlib_path.is_socket()
        container_result = container_path.is_socket()
        assert container_result == pathlib_result


class TestIsSymlink:
    def test_not_provided(self):
        assert not hasattr(ContainerPath, 'is_symlink')


# TODO: extended signature methods
