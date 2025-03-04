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

"""Unit tests for methods of LocalPath."""

from __future__ import annotations

import pathlib
import shutil

import pytest

from charmlibs.pathops import LocalPath


@pytest.mark.parametrize(
    ('user', 'group'),
    [
        ('user', 'group'),
        ('user', 2),
        ('user', None),
        (1, 'group'),
        (None, 'group'),
        (1, 2),
        (1, None),
        (None, 2),
        (None, None),
    ],
)
def test_mkdir_chown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    user: int | str | None,
    group: int | str | None,
):
    calls: list[tuple[pathlib.Path, str | int | None, str | int | None]] = []

    def mock_chown(
        path: pathlib.Path, user: str | int | None = None, group: str | int | None = None
    ) -> None:
        calls.append((path, user, group))
        return

    monkeypatch.setattr(shutil, 'chown', mock_chown)
    path = LocalPath(tmp_path, 'subdirectory')
    assert not path.exists()
    path.mkdir(user=user, group=group)
    assert path.exists()
    assert path.is_dir()
    if (user, group) == (None, None):
        assert not calls
    else:
        assert len(calls) == 1
        [call] = calls
        assert call == (path, user, group)


def test_write_bytes_chmod(): ...
def test_write_bytes_chown(): ...
def test_write_text_chmod(): ...
def test_write_text_chown(): ...
