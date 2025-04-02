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

from __future__ import annotations

import ops

import charmlibs.pathops as pathops


class Charm(ops.CharmBase):
    root: pathops.PathProtocol

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on['test'].action, self._on_test)

    def _on_test(self, event: ops.ActionEvent) -> None:
        file = self.root / 'file.txt'
        contents = 'Hello World!'
        pathops.ensure_contents(path=file, contents=contents)
        assert file.read_text() == contents
        file.unlink()
        event.set_results({str(file): contents})
