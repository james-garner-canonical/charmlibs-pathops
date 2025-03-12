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

import grp
import pathlib
import pwd
import re
import shutil

import ops
import pytest

from charmlibs.pathops import ContainerPath, LocalPath

USER_AND_GROUP_COMBINATIONS = [
    ('user', 'group'),
    ('user', None),
    (None, 'group'),
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


def mock_pass(*args: object, **kwargs: object) -> None:
    pass


@pytest.fixture
def mock_chown():
    return MockChown()


class TestMkDir:
    @pytest.mark.parametrize(('user', 'group'), USER_AND_GROUP_COMBINATIONS)
    def test_calls_chown(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        mock_chown: MockChown,
        user: str | None,
        group: str | None,
    ):
        path = LocalPath(tmp_path, 'subdirectory')
        assert not path.exists()
        with monkeypatch.context() as m:
            m.setattr(shutil, 'chown', mock_chown)
            m.setattr(pwd, 'getpwnam', mock_pass)
            m.setattr(grp, 'getgrnam', mock_pass)
            path.mkdir(user=user, group=group)
        assert path.exists()
        assert path.is_dir()
        if (user, group) == (None, None):
            assert not mock_chown.calls
        else:
            [call] = mock_chown.calls
            assert call == (path, user, group)

    @pytest.mark.pebble
    def test_unknown_user_raises_before_other_errors(
        self, container: ops.Container, tmp_path: pathlib.Path
    ):
        unknown_user = 'unknown_user'
        with pytest.raises(LookupError):
            pwd.getpwnam(unknown_user)
        parent = tmp_path / 'dirname'
        assert not parent.exists()
        path = parent / 'subdirname'
        assert not path.exists()
        container_path = ContainerPath(path, container=container)
        local_path = LocalPath(path)
        with pytest.raises(LookupError) as ctx:
            container_path.mkdir(user=unknown_user)
        print(ctx.value)
        assert not path.exists()
        with pytest.raises(LookupError) as ctx:
            local_path.mkdir(user=unknown_user)
        print(ctx.value)
        assert not path.exists()

    @pytest.mark.pebble
    def test_unknown_group_raises_before_other_errors(
        self, container: ops.Container, tmp_path: pathlib.Path
    ):
        unknown_group = 'unknown_group'
        with pytest.raises(LookupError):
            grp.getgrnam(unknown_group)
        parent = tmp_path / 'dirname'
        assert not parent.exists()
        path = parent / 'subdirname'
        assert not path.exists()
        container_path = ContainerPath(path, container=container)
        local_path = LocalPath(path)
        with pytest.raises(LookupError) as ctx:
            container_path.mkdir(group=unknown_group)
        print(ctx.value)
        assert not path.exists()
        with pytest.raises(LookupError) as ctx:
            local_path.mkdir(group=unknown_group)
        print(ctx.value)
        assert not path.exists()


@pytest.mark.parametrize(('user', 'group'), USER_AND_GROUP_COMBINATIONS)
def test_write_bytes_calls_chown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    mock_chown: MockChown,
    user: str | None,
    group: str | None,
):
    path = LocalPath(tmp_path, 'file.txt')
    assert not path.exists()
    content = b'hell\r\no\r'
    with monkeypatch.context() as m:
        m.setattr(shutil, 'chown', mock_chown)
        m.setattr(pwd, 'getpwnam', mock_pass)
        m.setattr(grp, 'getgrnam', mock_pass)
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
    user: str | None,
    group: str | None,
):
    path = LocalPath(tmp_path, 'file.txt')
    assert not path.exists()
    content = 'hell\r\no\r'
    with monkeypatch.context() as m:
        m.setattr(shutil, 'chown', mock_chown)
        m.setattr(pwd, 'getpwnam', mock_pass)
        m.setattr(grp, 'getgrnam', mock_pass)
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
