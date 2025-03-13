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
import os
import pathlib
import pwd
import re
import shutil

import ops
import pytest

from charmlibs.pathops import ContainerPath, LocalPath, _constants, _fileinfo
from charmlibs.pathops._functions import get_fileinfo

os.umask(0o000)  # Pebble seems to operate with umask=0; this makes it easy to compare permissions


GOOD_PARENT_DIRECTORY_MODES = (
    '0o777',
    '0o766',
    '0o755',  # pebble default for mkdir
    '0o700',
)
BAD_PARENT_DIRECTORY_MODES_CREATE = (
    '0o344',
    '0o333',
    '0o300',
)
BAD_PARENT_DIRECTORY_MODES_NO_CREATE = (
    '0o666',
    '0o644',  # pebble default for file push
    '0o600',
    '0o544',
    '0o500',
    '0o444',
    '0o400',
    '0o200',
    '0o100',
    '0o010',
    '0o007',
    '0o000',
)
_MODES = (
    *GOOD_PARENT_DIRECTORY_MODES,
    *BAD_PARENT_DIRECTORY_MODES_NO_CREATE,
    *BAD_PARENT_DIRECTORY_MODES_CREATE,
)
ALL_MODES = tuple(sorted(_MODES, reverse=True))


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

    @pytest.mark.pebble
    def test_unknown_user_raises_before_other_errors(
        self,
        container: ops.Container,
        tmp_path: pathlib.Path,
        method: str,
        content: bytes | str | None,
    ):
        args = [content] if content is not None else ()
        unknown_user = 'unknown_user'
        with pytest.raises(LookupError):
            pwd.getpwnam(unknown_user)
        parent = tmp_path / 'dirname'
        assert not parent.exists()
        path = parent / 'subdirname'
        assert not path.exists()
        container_path = ContainerPath(path, container=container)
        local_path = LocalPath(path)
        container_path_method = getattr(container_path, method)
        local_path_method = getattr(local_path, method)
        with pytest.raises(LookupError) as ctx:
            container_path_method(*args, user=unknown_user)
        print(ctx.value)
        assert not path.exists()
        with pytest.raises(LookupError) as ctx:
            local_path_method(*args, user=unknown_user)
        print(ctx.value)
        assert not path.exists()

    @pytest.mark.pebble
    def test_unknown_group_raises_before_other_errors(
        self,
        container: ops.Container,
        tmp_path: pathlib.Path,
        method: str,
        content: bytes | str | None,
    ):
        args = [content] if content is not None else ()
        unknown_group = 'unknown_group'
        with pytest.raises(LookupError):
            grp.getgrnam(unknown_group)
        parent = tmp_path / 'dirname'
        assert not parent.exists()
        path = parent / 'subdirname'
        assert not path.exists()
        container_path = ContainerPath(path, container=container)
        local_path = LocalPath(path)
        container_path_method = getattr(container_path, method)
        local_path_method = getattr(local_path, method)
        with pytest.raises(LookupError) as ctx:
            container_path_method(*args, group=unknown_group)
        print(ctx.value)
        assert not path.exists()
        with pytest.raises(LookupError) as ctx:
            local_path_method(*args, group=unknown_group)
        print(ctx.value)
        assert not path.exists()


@pytest.mark.pebble
class TestMkdirChmod:
    @pytest.mark.parametrize('mode_str', [None, *ALL_MODES])
    def test_ok(self, container: ops.Container, tmp_path: pathlib.Path, mode_str: str | None):
        print(mode_str)
        mode = int(mode_str, base=8) if mode_str is not None else None
        path = tmp_path / 'directory'
        # container
        container_path = ContainerPath(path, container=container)
        assert not path.exists()
        if mode is not None:
            container_path.mkdir(mode=mode)
        else:
            container_path.mkdir()
        assert path.exists()
        assert path.is_dir()
        container_info = get_fileinfo(container_path)
        # cleanup
        _rmdirs(path)
        # local
        local_path = LocalPath(path)
        assert not path.exists()
        if mode is not None:
            local_path.mkdir(mode=mode)
        else:
            local_path.mkdir()
        assert path.exists()
        assert path.is_dir()
        local_info = get_fileinfo(local_path)
        # cleanup -- pytest is bad at cleaning up when permissions are funky
        _rmdirs(path)
        # comparison
        exclude = ('last_modified', 'permissions')
        container_dict = _fileinfo.to_dict(container_info, exclude=exclude)
        local_dict = _fileinfo.to_dict(local_info, exclude=exclude)
        assert local_dict == container_dict
        assert _oct(local_info.permissions) == _oct(container_info.permissions)

    @pytest.mark.parametrize('mode_str', [None, *GOOD_PARENT_DIRECTORY_MODES])
    def test_when_parent_missing_and_parents_flag_then_ok(
        self, container: ops.Container, tmp_path: pathlib.Path, mode_str: str | None
    ):
        print(mode_str)
        mode = int(mode_str, base=8) if mode_str is not None else None
        parent = tmp_path / 'directory'
        path = parent / 'subdirectory'
        # container
        container_path = ContainerPath(path, container=container)
        assert not path.exists()
        assert not parent.exists()
        if mode is not None:
            container_path.mkdir(parents=True, mode=mode)
        else:
            container_path.mkdir(parents=True)
        assert parent.exists()
        assert parent.is_dir()
        assert path.exists()
        assert path.is_dir()
        container_parent_info = get_fileinfo(container_path.parent)
        container_info = get_fileinfo(container_path)
        # cleanup
        _rmdirs(path, parent)
        # local
        local_path = LocalPath(path)
        assert not path.exists()
        assert not parent.exists()
        if mode is not None:
            local_path.mkdir(parents=True, mode=mode)
        else:
            local_path.mkdir(parents=True)
        assert parent.exists()
        assert parent.is_dir()
        assert path.exists()
        assert path.is_dir()
        local_parent_info = get_fileinfo(local_path.parent)
        local_info = get_fileinfo(local_path)
        # cleanup -- pytest is bad at cleaning up when permissions are funky
        _rmdirs(path, parent)
        # comparison
        exclude = ('last_modified', 'permissions')
        container_dict = _fileinfo.to_dict(container_info, exclude=exclude)
        local_dict = _fileinfo.to_dict(local_info, exclude=exclude)
        assert local_dict == container_dict
        assert _oct(local_info.permissions) == _oct(container_info.permissions)
        container_parent_dict = _fileinfo.to_dict(container_parent_info, exclude=exclude)
        local_parent_dict = _fileinfo.to_dict(local_parent_info, exclude=exclude)
        assert local_parent_dict == container_parent_dict
        try:
            assert _oct(local_parent_info.permissions) == _oct(container_parent_info.permissions)
        except AssertionError:  # TODO: resolve this difference in behaviour
            assert _oct(local_parent_info.permissions) == _oct(_constants.DEFAULT_MKDIR_MODE)
            assert _oct(container_parent_info.permissions) == mode_str

    @pytest.mark.parametrize('mode_str', BAD_PARENT_DIRECTORY_MODES_NO_CREATE)
    def test_when_parent_missing_and_parents_flag_and_no_execute_perm_then_pebble_errors(
        self, container: ops.Container, tmp_path: pathlib.Path, mode_str: str
    ):
        """The permissions are bad because they lack the execute permission.

        This means that pebble creates the parent directory without the ability to write to it,
        and subdirectory creation then fails with a permission error.

        This does not apply to pathlib, because it creates the parent directory using its default
        permission (determined by the mode argument default), rather than the requested mode.
        """
        mode = int(mode_str, base=8)
        parent = tmp_path / 'directory'
        path = parent / 'subdirectory'
        # container
        container_path = ContainerPath(path, container=container)
        assert not path.exists()
        assert not parent.exists()
        with pytest.raises(PermissionError):  # TODO: resolve this difference in behaviour
            container_path.mkdir(parents=True, mode=mode)
        assert parent.exists()
        container_parent_info = get_fileinfo(container_path.parent)
        assert _oct(container_parent_info.permissions) == mode_str
        os.chmod(parent, 0o755)  # so that we can check if path exists!
        assert not path.exists()
        # cleanup
        _rmdirs(parent)
        # no container
        local_path = LocalPath(path)
        assert not path.exists()
        assert not parent.exists()
        local_path.mkdir(parents=True, mode=mode)
        assert parent.exists()
        local_parent_info = get_fileinfo(local_path.parent)
        assert _oct(local_parent_info.permissions) == _oct(_constants.DEFAULT_MKDIR_MODE)
        assert path.exists()
        local_info = get_fileinfo(local_path)
        assert _oct(local_info.permissions) == mode_str
        # cleanup -- pytest is bad at cleaning up when permissions are funky
        _rmdirs(path, parent)
        # comparison -- none since the results are different

    @pytest.mark.parametrize('mode_str', BAD_PARENT_DIRECTORY_MODES_CREATE)
    def test_subdirectory_make_parents_bad_permissions_create(
        self, container: ops.Container, tmp_path: pathlib.Path, mode_str: str
    ):
        """The permissions are bad because they lack the read permission.

        Pebble must try some operation that requires read permissions on the parent directory
        after creating the file inside it. Pathlib doesn't, so it has no problems here.
        """
        mode = int(mode_str, base=8)
        parent = tmp_path / 'directory'
        path = parent / 'subdirectory'
        # container
        assert not path.exists()
        assert not parent.exists()
        container_path = ContainerPath(path, container=container)
        with pytest.raises(PermissionError):
            container_path.mkdir(parents=True, mode=mode)
        assert parent.exists()
        assert path.exists()
        container_parent_info = get_fileinfo(container_path.parent)
        container_info = get_fileinfo(container_path)
        # cleanup
        _rmdirs(path, parent)
        # local
        assert not path.exists()
        assert not parent.exists()
        local_path = LocalPath(path)
        local_path.mkdir(parents=True, mode=mode)
        assert parent.exists()
        assert path.exists()
        local_parent_info = get_fileinfo(local_path.parent)
        local_info = get_fileinfo(local_path)
        # cleanup -- pytest is bad at cleaning up when permissions are funky
        _rmdirs(path, parent)
        # comparison -- let's see
        exclude = 'last_modified'
        container_dict = _fileinfo.to_dict(container_info, exclude=exclude)
        local_dict = _fileinfo.to_dict(local_info, exclude=exclude)
        assert local_dict == container_dict
        exclude = ('last_modified', 'permissions')
        container_parent_dict = _fileinfo.to_dict(container_parent_info, exclude=exclude)
        local_parent_dict = _fileinfo.to_dict(local_parent_info, exclude=exclude)
        assert local_parent_dict == container_parent_dict
        assert _oct(container_parent_info.permissions) == mode_str
        assert _oct(local_parent_info.permissions) == _oct(_constants.DEFAULT_MKDIR_MODE)


def test_write_bytes_chmod(): ...
def test_write_text_chmod(): ...


def _oct(i: int) -> str:
    return f'0o{i:03o}'


def _rmdirs(path: pathlib.Path, *paths: pathlib.Path):
    for p in (path, *paths):
        os.chmod(p, 0o755)
        p.rmdir()
