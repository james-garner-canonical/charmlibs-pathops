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

import errno
import operator
import os
import pathlib
import typing

import ops
import pytest
from ops import pebble

import utils
from charmlibs.pathops import ContainerPath, LocalPath, RelativePathError

if typing.TYPE_CHECKING:
    from typing import Any, Callable


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


@pytest.mark.parametrize('method', ('read_bytes', 'read_text'))
class TestReadCommon:
    @pytest.mark.parametrize(
        ('file', 'error'),
        (
            (utils.EMPTY_DIR_NAME, IsADirectoryError),
            (utils.BROKEN_SYMLINK_NAME, FileNotFoundError),
            (utils.MISSING_FILE_NAME, FileNotFoundError),
            (utils.SOCKET_NAME, OSError),  # ContainerPath will raise FileNotFoundError
        ),
    )
    def test_filetype_errors(
        self,
        container: ops.Container,
        session_dir: pathlib.Path,
        method: str,
        file: str,
        error: type[Exception],
    ):
        pathlib_method = getattr(pathlib.Path, method)
        with pytest.raises(error):
            pathlib_method(session_dir / file)
        containerpath_method = getattr(ContainerPath, method)
        container_path = ContainerPath(session_dir, file, container=container)
        with pytest.raises(error):
            containerpath_method(container_path)

    @pytest.mark.parametrize(
        ('mock', 'error'),
        (
            (utils.Mocks.raises_connection_error, pebble.ConnectionError),
            (utils.Mocks.raises_unknown_path_error, pebble.PathError),
        ),
    )
    def test_unhandled_pebble_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        container: ops.Container,
        mock: Callable[[Any], None],
        error: type[Exception],
        method: str,
    ):
        containerpath_method = getattr(ContainerPath, method)
        with monkeypatch.context() as m:
            m.setattr(container, 'pull', mock)
            with pytest.raises(error):
                containerpath_method(ContainerPath('/', container=container))


class TestReadText:
    @pytest.mark.parametrize('newline', (None, ''))
    @pytest.mark.parametrize('filename', utils.TEXT_FILES)
    def test_ok(
        self,
        container: ops.Container,
        session_dir: pathlib.Path,
        filename: str,
        newline: str | None,
    ):
        path = session_dir / filename
        container_path = ContainerPath(path, container=container)
        try:  # python 3.13+ only
            pathlib_result = path.read_text(newline=newline)  # pyright: ignore[reportCallIssue,reportUnknownVariableType]
        except TypeError:
            pathlib_result = path.read_text()
            container_result = container_path.read_text()
        else:
            container_result = container_path.read_text(newline=newline)
        assert container_result == pathlib_result

    @pytest.mark.parametrize('filename', [next(iter(utils.UTF16_BINARY_FILES))])
    def test_when_file_is_not_utf8_then_raises_unicode_error(
        self,
        container: ops.Container,
        session_dir: pathlib.Path,
        filename: str,
    ):
        path = session_dir / filename
        with pytest.raises(UnicodeError):
            path.read_text()
        container_path = ContainerPath(path, container=container)
        with pytest.raises(UnicodeError):
            container_path.read_text()


class TestReadBytes:
    @pytest.mark.parametrize('filename', [*utils.TEXT_FILES, *utils.BINARY_FILES])
    def test_ok(
        self,
        container: ops.Container,
        session_dir: pathlib.Path,
        filename: str,
    ):
        path = session_dir / filename
        pathlib_result = path.read_bytes()
        container_result = ContainerPath(path, container=container).read_bytes()
        assert container_result == pathlib_result


class TestRmDir:
    def test_ok(self, container: ops.Container, tmp_path: pathlib.Path):
        directory = tmp_path / 'dir'
        # setup
        directory.mkdir()
        assert directory.is_dir()
        # pathlib
        directory.rmdir()
        assert not directory.exists()
        # setup
        directory.mkdir()
        assert directory.is_dir()
        # container
        ContainerPath(directory, container=container).rmdir()
        assert not directory.exists()

    @pytest.mark.parametrize('filename', [utils.MISSING_FILE_NAME, utils.BROKEN_SYMLINK_NAME])
    def test_when_target_doesnt_exist_then_raises_file_not_found_error(
        self, container: ops.Container, tmp_path: pathlib.Path, filename: str
    ):
        directory = tmp_path / filename
        # pathlib
        assert not directory.exists()
        with pytest.raises(FileNotFoundError):
            directory.rmdir()
        # container
        assert not directory.exists()
        with pytest.raises(FileNotFoundError):
            ContainerPath(directory, container=container).rmdir()

    @pytest.mark.parametrize('filename', [utils.TEXT_FILE_NAME, utils.SOCKET_NAME])
    def test_when_target_isnt_a_directory_then_raises_not_a_directory_error(
        self, container: ops.Container, session_dir: pathlib.Path, filename: str
    ):
        path = session_dir / filename
        # pathlib
        assert not path.is_dir()
        with pytest.raises(NotADirectoryError):
            path.rmdir()
        # container
        assert not path.is_dir()
        with pytest.raises(NotADirectoryError):
            ContainerPath(path, container=container).rmdir()

    @pytest.mark.parametrize(
        'filename', (utils.EMPTY_DIR_SYMLINK_NAME, utils.RECURSIVE_SYMLINK_NAME)
    )
    def test_when_target_is_a_symlink_to_a_directory_then_raises_not_a_directory_error(
        self, container: ops.Container, session_dir: pathlib.Path, filename: str
    ):
        path = session_dir / filename
        # pathlib
        assert path.is_dir()
        assert path.is_symlink()
        with pytest.raises(NotADirectoryError):
            path.rmdir()
        # container
        with pytest.raises(NotADirectoryError):
            ContainerPath(path, container=container).rmdir()

    def test_when_directory_isnt_empty_then_raises_directory_not_empty_error(
        self, container: ops.Container, session_dir: pathlib.Path
    ):
        with pytest.raises(OSError) as pathlib_ctx:
            session_dir.rmdir()
        assert pathlib_ctx.value.errno == errno.ENOTEMPTY
        with pytest.raises(OSError) as container_ctx:
            ContainerPath(session_dir, container=container).rmdir()
        assert container_ctx.value.errno == errno.ENOTEMPTY

    @pytest.mark.parametrize(
        ('mock', 'error'),
        (
            (utils.Mocks.raises_connection_error, pebble.ConnectionError),
            (utils.Mocks.raises_unknown_path_error, pebble.PathError),
        ),
    )
    def test_unhandled_pebble_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        container: ops.Container,
        mock: Callable[[Any], None],
        error: type[Exception],
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'remove_path', mock)
            with pytest.raises(error):
                ContainerPath('/', container=container).rmdir()


class TestUnlink:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, class_tmp_dirs: pathlib.Path, filename: str):
        pathlib_dir = class_tmp_dirs / '1'
        container_dir = class_tmp_dirs / '2'
        pathlib_path = pathlib_dir / filename
        container_path = ContainerPath(container_dir / filename, container=container)
        try:
            pathlib_path.unlink()
            assert not pathlib_path.exists()
        except OSError as e:
            with pytest.raises(type(e)):
                container_path.unlink()
            return
        container_path.unlink()

    def test_unlink_symlink_then_unlink_target(
        self, container: ops.Container, tmp_path: pathlib.Path
    ):
        # pathlib
        pathlib_target = tmp_path / 'target'
        pathlib_target.touch()
        pathlib_symlink = tmp_path / 'link'
        pathlib_symlink.symlink_to(pathlib_target)
        pathlib_symlink.unlink()
        assert not pathlib_symlink.exists()
        assert pathlib_target.exists()
        pathlib_target.unlink()
        assert not pathlib_target.exists()
        # container
        container_target = tmp_path / 'target'
        container_target.touch()
        container_symlink = tmp_path / 'link'
        container_symlink.symlink_to(container_target)
        ContainerPath(container_symlink, container=container).unlink()
        assert not container_symlink.exists()
        assert container_target.exists()
        ContainerPath(container_target, container=container).unlink()
        assert not container_target.exists()

    def test_unlink_target_then_unlink_symlink(
        self, container: ops.Container, tmp_path: pathlib.Path
    ):
        # pathlib
        pathlib_target = tmp_path / 'target'
        pathlib_target.touch()
        pathlib_symlink = tmp_path / 'link'
        pathlib_symlink.symlink_to(pathlib_target)
        pathlib_target.unlink()
        assert not pathlib_target.exists()
        assert not pathlib_symlink.exists()  # because it's a broken symlink and exists follows it
        pathlib_symlink.unlink()  # ok because there is actually a target, the broken symlink
        # container
        container_target = tmp_path / 'target'
        container_target.touch()
        container_symlink = tmp_path / 'link'
        container_symlink.symlink_to(container_target)
        ContainerPath(container_target, container=container).unlink()
        assert not container_target.exists()
        assert not pathlib_symlink.exists()  # because it's a broken symlink and exists follows it
        ContainerPath(container_symlink, container=container).unlink()

    def test_when_missing_ok_then_remove_missing_file_ok(
        self, container: ops.Container, session_dir: pathlib.Path
    ):
        path = session_dir / utils.MISSING_FILE_NAME
        path.unlink(missing_ok=True)
        ContainerPath(path, container=container).unlink(missing_ok=True)


class TestIterDir:
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path):
        pathlib_list = list(session_dir.iterdir())
        pathlib_set = {str(p) for p in pathlib_list}
        assert len(pathlib_list) == len(pathlib_set)
        container_path = ContainerPath(session_dir, container=container)
        container_list = list(container_path.iterdir())
        container_set = {str(p) for p in container_list}
        assert len(container_list) == len(container_set)
        assert container_set == pathlib_set

    @pytest.mark.parametrize(
        ('file', 'error'),
        (
            (utils.BINARY_FILE_NAME, NotADirectoryError),
            (utils.TEXT_FILE_NAME, NotADirectoryError),
            (utils.BROKEN_SYMLINK_NAME, FileNotFoundError),
            (utils.MISSING_FILE_NAME, FileNotFoundError),
            (utils.SOCKET_NAME, NotADirectoryError),  # ContainerPath raises NotADirectory
        ),
    )
    def test_filetype_errors(
        self,
        container: ops.Container,
        session_dir: pathlib.Path,
        file: str,
        error: type[Exception],
    ):
        path = session_dir / file
        with pytest.raises(error):
            next(path.iterdir())
        container_path = ContainerPath(path, container=container)
        with pytest.raises(error):
            next(container_path.iterdir())


class TestGlob:
    @pytest.mark.parametrize(
        'pattern',
        (
            '*',
            '*.txt',
            'foo*',
            'ba*.txt',
            f'{utils.NESTED_DIR_NAME}/*.txt',
            '*/*.txt',
        ),
    )
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, pattern: str):
        pathlib_result = sorted(str(p) for p in session_dir.glob(pattern))
        container_path = ContainerPath(session_dir, container=container)
        container_result = sorted(str(p) for p in container_path.glob(pattern))
        assert container_result == pathlib_result

    @pytest.mark.parametrize('pattern', [f'{utils.NESTED_DIR_NAME}/**/*.txt', '**/*.txt'])
    def test_when_recursive_glob_then_raises_not_implemented_error(
        self, container: ops.Container, session_dir: pathlib.Path, pattern: str
    ):
        list(session_dir.glob(pattern))  # pattern is fine
        container_path = ContainerPath(session_dir, container=container)
        with pytest.raises(NotImplementedError):
            list(container_path.glob(pattern))

    @pytest.mark.parametrize('pattern', ['**.txt', '***/*.txt'])
    def test_when_bad_pattern_then_raises_not_implemented_error(
        self, container: ops.Container, session_dir: pathlib.Path, pattern: str
    ):
        with pytest.raises(ValueError):
            list(session_dir.glob(pattern))
        container_path = ContainerPath(session_dir, container=container)
        with pytest.raises(ValueError):
            list(container_path.glob(pattern))


@pytest.mark.parametrize('method', ['owner', 'group'])
class TestOwnerAndGroup:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(
        self, container: ops.Container, session_dir: pathlib.Path, method: str, filename: str
    ):
        path = session_dir / filename
        pathlib_method = getattr(path, method)
        container_path = ContainerPath(path, container=container)
        container_method = getattr(container_path, method)
        try:
            pathlib_result = pathlib_method()
        except Exception as e:
            with pytest.raises(type(e)):
                container_result = container_method()
        else:
            container_result = container_method()
            assert container_result == pathlib_result


class TestExists:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, filename: str):
        pathlib_path = session_dir / filename
        container_path = ContainerPath(session_dir, filename, container=container)
        pathlib_result = pathlib_path.exists()
        container_result = container_path.exists()
        assert container_result == pathlib_result


class TestIsDir:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, filename: str):
        pathlib_path = session_dir / filename
        container_path = ContainerPath(session_dir, filename, container=container)
        pathlib_result = pathlib_path.is_dir()
        container_result = container_path.is_dir()
        assert container_result == pathlib_result


class TestIsFile:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, filename: str):
        pathlib_path = session_dir / filename
        container_path = ContainerPath(session_dir, filename, container=container)
        pathlib_result = pathlib_path.is_file()
        container_result = container_path.is_file()
        assert container_result == pathlib_result


class TestIsFifo:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, filename: str):
        pathlib_path = session_dir / filename
        container_path = ContainerPath(session_dir, filename, container=container)
        pathlib_result = pathlib_path.is_fifo()
        container_result = container_path.is_fifo()
        assert container_result == pathlib_result


class TestIsSocket:
    @pytest.mark.parametrize('filename', utils.FILENAMES_PLUS)
    def test_ok(self, container: ops.Container, session_dir: pathlib.Path, filename: str):
        pathlib_path = session_dir / filename
        container_path = ContainerPath(session_dir, filename, container=container)
        pathlib_result = pathlib_path.is_socket()
        container_result = container_path.is_socket()
        assert container_result == pathlib_result


class TestWriteBytes:
    @pytest.mark.parametrize(('filename', 'contents'), tuple(utils.BINARY_FILES.items()))
    def test_ok(
        self, container: ops.Container, tmp_path: pathlib.Path, filename: str, contents: bytes
    ):
        path = tmp_path / filename
        path.write_bytes(contents)
        assert path.read_bytes() == contents
        ContainerPath(path, container=container).write_bytes(contents)
        assert path.read_bytes() == contents


@pytest.mark.parametrize(
    'attr',
    (
        '__rtruediv__',
        '__fspath__',
        '__bytes__',
        'as_uri',
        'relative_to',
        'rglob',
        'stat',
        'lstat',
        'is_mount',
        'is_symlink',
        'is_block_device',
        'is_char_device',
        'chmod',
        'lchmod',
        'symlink_to',
        'resolve',
        'samefile',
        'open',
        'touch',
    ),
)
def test_not_provided(attr: str):
    assert hasattr(pathlib.Path, attr)
    assert not hasattr(ContainerPath, attr)
