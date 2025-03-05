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

import os
import pathlib

import ops
import pytest

from charmlibs.pathops import ContainerPath, LocalPath


@pytest.mark.skipif(
    os.getenv('RUN_REAL_PEBBLE_TESTS') != '1',
    reason='RUN_REAL_PEBBLE_TESTS not set',
)
class TestIterDir:
    def test_ok(self, container: ops.Container, interesting_dir: pathlib.Path):
        local_path = LocalPath(interesting_dir)
        local_list = list(local_path.iterdir())
        local_set = {str(p) for p in local_list}
        assert len(local_list) == len(local_set)
        container_path = ContainerPath(interesting_dir, container=container)
        container_list = list(container_path.iterdir())
        container_set = {str(p) for p in container_list}
        assert len(container_list) == len(container_set)
        assert local_set == container_set

    def test_given_not_a_directory_when_iterdir_then_raises(
        self, container: ops.Container, interesting_dir: pathlib.Path
    ):
        path = interesting_dir / 'empty_file.bin'
        local_path = LocalPath(path)
        with pytest.raises(NotADirectoryError) as ctx:
            next(local_path.iterdir())
        print(ctx.value)
        container_path = ContainerPath(path, container=container)
        with pytest.raises(NotADirectoryError) as ctx:
            next(container_path.iterdir())
        print(ctx.value)
