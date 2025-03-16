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

"""Tests that don't use a real Pebble to test helper functions."""

from __future__ import annotations

import typing

import ops
import pytest
from ops import pebble

import utils
from charmlibs.pathops import ContainerPath
from charmlibs.pathops._functions import _get_fileinfo

if typing.TYPE_CHECKING:
    from typing import Any, Callable


class TestGetFileInfo:
    @pytest.mark.parametrize(
        ('mock', 'error'),
        (
            (utils.raises_connection_error, pebble.ConnectionError),
            (utils.raises_unknown_api_error, pebble.APIError),
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
            m.setattr(container, 'list_files', mock)
            with pytest.raises(error):
                _get_fileinfo(ContainerPath('/', container=container))
