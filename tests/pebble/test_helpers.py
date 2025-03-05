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
import typing

import pytest

from charmlibs.pathops import ContainerPath
from charmlibs.pathops._helpers import get_fileinfo

if typing.TYPE_CHECKING:
    import ops
    from ops import pebble


@pytest.mark.skipif(
    os.getenv('RUN_REAL_PEBBLE_TESTS') != '1',
    reason='RUN_REAL_PEBBLE_TESTS not set',
)
class TestGetFileInfo:
    def test_ok(self, container: ops.Container, interesting_dir: pathlib.Path):
        paths = list(interesting_dir.iterdir())
        fileinfos_synthetic: list[pebble.FileInfo] = []
        fileinfos_pebble: list[pebble.FileInfo] = []
        for path in paths:
            try:
                fileinfos_pebble.append(get_fileinfo(ContainerPath(path, container=container)))
            except FileNotFoundError:  # noqa: PERF203 (try-except in a loop)
                with pytest.raises(FileNotFoundError):
                    get_fileinfo(path)
            else:
                fileinfos_synthetic.append(get_fileinfo(path))
        synthetic_result = [_fileinfo_to_dict(fileinfo) for fileinfo in fileinfos_synthetic]
        pebble_result = [_fileinfo_to_dict(fileinfo) for fileinfo in fileinfos_pebble]
        assert synthetic_result == pebble_result


def _fileinfo_to_dict(info: ops.pebble.FileInfo) -> dict[str, object] | None:
    return {
        name: getattr(info, name)
        for name in dir(info)
        if (not name.startswith('_')) and (name != 'from_dict')
    }
