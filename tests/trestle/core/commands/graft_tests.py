# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2020 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for graft command."""
import pathlib
import sys
from unittest import mock

from trestle.cli import Trestle


def test_graft_from_cli(tmp_trestle_dir: pathlib.Path) -> None:
    """Run graft as a CLI."""
    cmd_str = 'trestle graft -r results_name -p plan_name'
    with mock.patch.object(sys, 'argv', cmd_str.split()):
        rc = Trestle().run()
        # FIXME: Need to change this before being merged to develop.
        rc == 1
