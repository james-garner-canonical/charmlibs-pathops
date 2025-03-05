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

"""Methods for matching Python Exceptions to Pebble Errors and creating Exception objects."""

from __future__ import annotations

import errno
import os

from ops import pebble


class FileNotFound:
    @staticmethod
    def matches(error: pebble.Error) -> bool:
        return (isinstance(error, pebble.APIError) and error.code == 404) or (
            isinstance(error, pebble.PathError) and error.kind == 'not-found'
        )

    @staticmethod
    def exception(msg: str) -> FileNotFoundError:
        return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), msg)


class NotADirectory:
    @staticmethod
    def exception(msg: str) -> NotADirectoryError:
        return NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), msg)


class Permission:
    @classmethod
    def matches(cls, error: pebble.Error) -> bool:
        return isinstance(error, pebble.PathError) and error.kind == 'permission-denied'

    @staticmethod
    def exception(msg: str) -> PermissionError:
        return PermissionError(errno.EPERM, os.strerror(errno.EPERM), msg)
