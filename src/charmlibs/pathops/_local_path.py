# Copyright 2024 Canonical Ltd.
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

"""Implementation of LocalPath class."""

from __future__ import annotations

import grp
import pathlib
import pwd
import shutil
import typing

from . import _constants

if typing.TYPE_CHECKING:
    from typing_extensions import Buffer


class LocalPath(pathlib.PosixPath):
    def write_bytes(
        self,
        data: Buffer,
        # extended with chmod + chown args
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        _validate_user_and_group(user=user, group=group)
        bytes_written = super().write_bytes(data)
        _chown_if_needed(self, user=user, group=group)
        self.chmod(mode)
        return bytes_written

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        # extended with chmod + chown args
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        _validate_user_and_group(user=user, group=group)
        bytes_written = super().write_text(data, encoding=encoding, errors=errors)
        _chown_if_needed(self, user=user, group=group)
        self.chmod(mode)
        return bytes_written

    def mkdir(
        self,
        mode: int = _constants.DEFAULT_MKDIR_MODE,
        parents: bool = False,
        exist_ok: bool = False,
        # extended with chown args
        *,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        _validate_user_and_group(user=user, group=group)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        _chown_if_needed(self, user=user, group=group)


def _validate_user_and_group(user: str | None, group: str | None):
    if user is not None:
        pwd.getpwnam(user)
    if group is not None:
        grp.getgrnam(group)


def _chown_if_needed(path: pathlib.Path, user: str | int | None, group: str | int | None) -> None:
    # shutil.chown is happy as long as either user or group is not None
    # but the type checker doesn't like that, so we have to be more explicit
    if user is not None and group is not None:
        shutil.chown(path, user=user, group=group)
    elif user is not None:
        shutil.chown(path, user=user)
    elif group is not None:
        shutil.chown(path, group=group)
