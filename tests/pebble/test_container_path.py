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

"""Tests that use a real Pebble to compare ContainerPath and LocalPath output."""

from __future__ import annotations

import operator
import os
import pathlib
import typing

import ops
import pytest

from charmlibs.pathops import ContainerPath, LocalPath, RelativePathError

if typing.TYPE_CHECKING:
    from typing import Callable

    import ops


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
    OPERATIONS = (operator.lt, operator.le, operator.gt, operator.ge, operator.eq)
    PATH_PAIRS = (('/foo', '/bar'), ('/foo', '/foo/bar'), ('/foo/bar', '/foo/bar/bartholemew'))

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize(('left', 'right'), PATH_PAIRS)
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


#########################
# concrete path methods #
#########################


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
        path = readable_interesting_dir / 'does-not-exist'
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


class TestExists:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        paths = [*readable_interesting_dir.iterdir(), readable_interesting_dir / 'does-not-exist']
        local_results = [(path, path.exists()) for path in paths]
        container_results = [
            (path, ContainerPath(path, container=container).exists()) for path in paths
        ]
        assert container_results == local_results


class TestIsDir:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        paths = [*readable_interesting_dir.iterdir(), readable_interesting_dir / 'does-not-exist']
        local_results = [(path, path.is_dir()) for path in paths]
        container_results = [
            (path, ContainerPath(path, container=container).is_dir()) for path in paths
        ]
        assert container_results == local_results


class TestIsFile:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        paths = [*readable_interesting_dir.iterdir(), readable_interesting_dir / 'does-not-exist']
        local_results = [(path, path.is_file()) for path in paths]
        container_results = [
            (path, ContainerPath(path, container=container).is_file()) for path in paths
        ]
        assert container_results == local_results


class TestIsFifo:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        paths = [*readable_interesting_dir.iterdir(), readable_interesting_dir / 'does-not-exist']
        local_results = [(path, path.is_fifo()) for path in paths]
        container_results = [
            (path, ContainerPath(path, container=container).is_fifo()) for path in paths
        ]
        assert container_results == local_results


class TestIsSocket:
    def test_ok(self, container: ops.Container, readable_interesting_dir: pathlib.Path):
        paths = [*readable_interesting_dir.iterdir(), readable_interesting_dir / 'does-not-exist']
        local_results = [(path, path.is_socket()) for path in paths]
        container_results = [
            (path, ContainerPath(path, container=container).is_socket()) for path in paths
        ]
        assert container_results == local_results


class TestIsSymlink:
    def test_not_provided(self):
        assert not hasattr(ContainerPath, 'is_symlink')
