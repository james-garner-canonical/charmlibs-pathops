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

import pathlib

import jubilant


def get_packed_charm_path(charm_name: str) -> pathlib.Path:
    packed_dir = pathlib.Path(__file__).parent / 'charms' / '.packed'
    (charm_path,) = packed_dir.glob(f'{charm_name}*.charm')
    ret = charm_path.absolute()
    assert ret.is_file()
    return ret


def deploy(juju: jubilant.Juju, substrate: str) -> str:
    charm_name = f'test-{substrate}'
    if substrate == 'kubernetes':
        juju.deploy(
            get_packed_charm_path(charm_name),
            resources={'workload': 'ubuntu:latest'},
        )
    elif substrate == 'machine':
        juju.deploy(get_packed_charm_path(charm_name))
    else:
        raise ValueError(f'Unknown substrate: {substrate!r}')
    return charm_name
