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

import pathlib
import typing

import jubilant
import pytest

if typing.TYPE_CHECKING:
    from typing import Iterator


def pytest_addoption(parser: pytest.OptionGroup):
    parser.addoption(
        '--keep-models',
        action='store_true',
        default=False,
        help='keep temporarily-created models',
    )
    parser.addoption(
        '--substrate',
        action='store',
        default='kubernetes',
        choices=('machine', 'kubernetes'),
        help='whether to deploy the machine or kubernetes charm',
    )


@pytest.fixture(scope='session')
def charm(request: pytest.FixtureRequest) -> str:
    substrate = typing.cast('str', request.config.getoption('--substrate'))
    return substrate


@pytest.fixture(scope='module')
def juju(request: pytest.FixtureRequest) -> Iterator[jubilant.Juju]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`.

    This adds command line parameter ``--keep-models`` (see help for details).
    """
    keep_models = typing.cast('bool', request.config.getoption('--keep-models'))
    substrate = typing.cast('str', request.config.getoption('--substrate'))
    with jubilant.temp_model(keep=keep_models) as juju:
        _deploy(juju, substrate)
        yield juju
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end='')


def _deploy(juju: jubilant.Juju, substrate: str) -> None:
    if substrate == 'kubernetes':
        juju.deploy(
            _get_packed_charm_path(substrate),
            resources={'workload': 'hello-world'},
        )
    elif substrate == 'machine':
        juju.deploy(_get_packed_charm_path(substrate))
    else:
        raise ValueError(f'Unknown substrate: {substrate!r}')


def _get_packed_charm_path(substrate: str) -> pathlib.Path:
    packed_dir = pathlib.Path(__file__).parent / 'charms' / '.packed'
    assert packed_dir.is_dir()
    charm_path = packed_dir / f'{substrate}.charm'
    assert charm_path.is_file()
    return charm_path.absolute()
