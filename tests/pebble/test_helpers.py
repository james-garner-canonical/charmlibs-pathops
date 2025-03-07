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

"""Tests that use a real Pebble to test helper functions."""

from __future__ import annotations

import os
import pathlib

import ops
import pytest
from ops import pebble

from charmlibs.pathops import ContainerPath
from charmlibs.pathops._helpers import get_fileinfo
from conftest import FILENAMES, Mocks

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_REAL_PEBBLE_TESTS') != '1', reason='RUN_REAL_PEBBLE_TESTS not set'
)


class TestGetFileInfo:
    @pytest.mark.parametrize('filename', FILENAMES)
    def test_ok(
        self, container: ops.Container, readable_interesting_dir: pathlib.Path, filename: str
    ):
        path = readable_interesting_dir / filename
        try:
            pebble_result = get_fileinfo(ContainerPath(path, container=container))
        except FileNotFoundError:
            with pytest.raises(FileNotFoundError):
                get_fileinfo(path)
            return
        else:
            synthetic_result = get_fileinfo(path)
            assert self._info_to_dict(synthetic_result) == self._info_to_dict(pebble_result)

    @staticmethod
    def _info_to_dict(info: ops.pebble.FileInfo) -> dict[str, object] | None:
        return {
            name: getattr(info, name)
            for name in dir(info)
            if (not name.startswith('_')) and (name != 'from_dict')
        }

    def test_when_pebble_connection_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'list_files', Mocks.raises_connection_error)
            with pytest.raises(pebble.ConnectionError):
                get_fileinfo(ContainerPath('/', container=container))

    def test_when_unknown_api_error_then_raises(
        self, monkeypatch: pytest.MonkeyPatch, container: ops.Container
    ):
        with monkeypatch.context() as m:
            m.setattr(container, 'list_files', Mocks.raises_unknown_api_error)
            with pytest.raises(pebble.APIError):
                get_fileinfo(ContainerPath('/', container=container))
