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

"""Common code for the kubernetes and machine test charms.

The contents of kubernetes/src/common.py and machine/src/common.py should be identical.
"""

from __future__ import annotations

import ops

# TODO: switch to recommended form `from charmlibs import pathops`
#       after next pyright release fixes:
#       https://github.com/microsoft/pyright/issues/10203
import charmlibs.pathops as pathops


class Charm(ops.CharmBase):
    root: pathops.PathProtocol

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on['ensure-contents'].action, self._on_ensure_contents)
        framework.observe(self.on['iterdir'].action, self._on_iterdir)

    def remove_path(self, path: pathops.PathProtocol) -> None:
        raise NotImplementedError()

    def _on_ensure_contents(self, event: ops.ActionEvent) -> None:
        path = self.root / event.params['path']
        pathops.ensure_contents(path=path, source=event.params['contents'])
        contents = path.read_text()
        self.remove_path(path)
        event.set_results({'contents': contents})

    def _on_iterdir(self, event: ops.ActionEvent) -> None:
        path = self.root / event.params['path']
        result = [str(p) for p in path.iterdir()]
        event.set_results({'iterdir': str(result)})
