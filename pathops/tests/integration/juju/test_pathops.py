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

"""Integration tests using a real Juju and charm to test ContainerPath."""

from __future__ import annotations

import traceback

import jubilant
import pytest

import utils


def test_deploy(juju: jubilant.Juju, substrate: str):
    try:
        utils.deploy(juju, substrate)
        juju.wait(jubilant.all_active)
    except BaseException as e:
        tb = traceback.format_exc()
        pytest.exit(f'Deployment failed due to {e!r}\nTraceback:\n{tb}', returncode=1)


def test_ensure_contents(juju: jubilant.Juju, substrate: str):
    _run(juju, substrate, 'ensure_contents')


def test_iterdir(juju: jubilant.Juju, substrate: str):
    _run(juju, substrate, 'iterdir')


def _run(juju: jubilant.Juju, substrate: str, test_case: str):
    name = utils.charm_name(substrate)
    result = juju.run(f'{name}/0', 'test', params={'case': test_case})
    assert result.success
    return result
