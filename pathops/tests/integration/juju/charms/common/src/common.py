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
        framework.observe(self.on['ensure-contents'].action, self._on_ensure_contents)
        framework.observe(self.on['iterdir'].action, self._on_iterdir)

    def _on_ensure_contents(self, event: ops.ActionEvent) -> None:
        file = self.root / 'file.txt'
        contents = 'Hello World!'
        pathops.ensure_contents(path=file, source=contents)
        assert file.read_text() == contents
        try:
            file.unlink()  # type: ignore
        except AttributeError:
            assert isinstance(file, pathops.ContainerPath)
            file._container.remove_path(str(file))
        results = {'file': repr(file), 'contents': contents}
        event.set_results(results)

    def _on_iterdir(self, event: ops.ActionEvent) -> None:
        files = list(self.root.iterdir())
        event.set_results({event.id: str(files)})
