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

import pytest

from charmlibs.pathops import LocalPath


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


@pytest.mark.parametrize(
    ('method', 'content'),
    [('write_bytes', b'hell\r\no\r'), ('write_text', 'hell\r\no\r'), ('mkdir', None)],
)
class TestChown:
    @pytest.mark.parametrize(
        ('user', 'group'),
        (
            ('user-name', 'group-name'),
            ('user-name', None),
            (None, 'group-name'),
            (None, None),
        ),
    )
    def test_calls_chown(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        mock_chown: MockChown,
        method: str,
        content: bytes | str | None,
        user: str | None,
        group: str | None,
    ):
        args = [content] if content is not None else ()
        path = LocalPath(tmp_path, 'subdirectory')
        assert not path.exists()
        path_method = getattr(path, method)
        with monkeypatch.context() as m:
            m.setattr(shutil, 'chown', mock_chown)
            m.setattr(pwd, 'getpwnam', mock_pass)
            m.setattr(grp, 'getgrnam', mock_pass)
            path_method(*args, user=user, group=group)
        assert path.exists()
        if method == 'read_bytes':
            assert isinstance(content, bytes)
            assert path.read_bytes() == content
        elif method == 'read_text':
            assert isinstance(content, str)
            expected_result = re.sub('\r\n|\r', '\n', content)
            assert path.read_text == expected_result
        elif method == 'mkdir':
            assert path.is_dir()
        if (user, group) == (None, None):
            assert not mock_chown.calls
        else:
            [call] = mock_chown.calls
            assert call == (path, user, group)
