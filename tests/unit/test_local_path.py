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
import re
import shutil

import pytest

from charmlibs.pathops import LocalPath

USER_AND_GROUP_COMBINATIONS = [
    ('user', 'group'),
    ('user', 2),
    ('user', None),
    (1, 'group'),
    (None, 'group'),
    (1, 2),
    (1, None),
    (None, 2),
    (None, None),
]


class MockChown:
    calls: list[tuple[pathlib.Path, str | int | None, str | int | None]]

    def __init__(self):
        self.calls = []

    def __call__(
        self, path: pathlib.Path, user: str | int | None = None, group: str | int | None = None
    ) -> None:
        self.calls.append((path, user, group))
        return


@pytest.fixture
def mock_chown():
    return MockChown()


@pytest.mark.parametrize(('user', 'group'), USER_AND_GROUP_COMBINATIONS)
def test_mkdir_calls_chown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    mock_chown: MockChown,
    user: int | str | None,
    group: int | str | None,
):
    monkeypatch.setattr(shutil, 'chown', mock_chown)
    path = LocalPath(tmp_path, 'subdirectory')
    assert not path.exists()
    path.mkdir(user=user, group=group)
    assert path.exists()
    assert path.is_dir()
    if (user, group) == (None, None):
        assert not mock_chown.calls
    else:
        [call] = mock_chown.calls
        assert call == (path, user, group)


@pytest.mark.parametrize(('user', 'group'), USER_AND_GROUP_COMBINATIONS)
def test_write_bytes_calls_chown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    mock_chown: MockChown,
    user: int | str | None,
    group: int | str | None,
):
    monkeypatch.setattr(shutil, 'chown', mock_chown)
    path = LocalPath(tmp_path, 'file.txt')
    assert not path.exists()
    content = b'hell\r\no\r'
    path.write_bytes(content, user=user, group=group)
    assert path.exists()
    assert path.is_file()
    assert path.read_bytes() == content
    if (user, group) == (None, None):
        assert not mock_chown.calls
    else:
        [call] = mock_chown.calls
        assert call == (path, user, group)


@pytest.mark.parametrize(('user', 'group'), USER_AND_GROUP_COMBINATIONS)
def test_write_text_calls_chown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    mock_chown: MockChown,
    user: int | str | None,
    group: int | str | None,
):
    monkeypatch.setattr(shutil, 'chown', mock_chown)
    path = LocalPath(tmp_path, 'file.txt')
    assert not path.exists()
    content = 'hell\r\no\r'
    path.write_text(content, user=user, group=group)
    assert path.exists()
    assert path.is_file()
    assert path.read_text() == re.sub('\r\n|\r', '\n', content)
    if (user, group) == (None, None):
        assert not mock_chown.calls
    else:
        [call] = mock_chown.calls
        assert call == (path, user, group)


def test_write_bytes_chmod(): ...
def test_write_text_chmod(): ...
