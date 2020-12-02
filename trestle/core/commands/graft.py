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
"""
Trestle graft command.

Graft was initially concieved as an independent project to trestle, however, has
been folded into trestle. This will be evaluated over successive releases.
"""
import argparse
import logging

from ilcli import Command  # type: ignore

logger = logging.getLogger(__name__)


class GraftCommand(Command):
    """CLI class for graft. Laden with comments for @degenaro."""

    name = 'graft'

    def _init_arguments(self) -> None:
        """
        Initialise argparse arguments.

        Refer to 'argparse' documents to understand what to do here.
        """
        # These arguments are up to you to define.
        self.add_argument('-r', '--sar', help='Name of the system assesment results', required=True)
        self.add_argument(
            '-p',
            '--system-assesssment-plan',
            help='Name of the system assessment plan inside the trestle project',
            required=True
        )
        self.add_argument('-o', '--observations', help='Directory or file with observations')

    def _run(self, args: argparse.Namespace) -> int:
        """
        Run is the entry point to trestle graft.

        Run should return the appropriate return code. e.g. 0 for success, > 0 for failure.
        This function should never throw an exception and should be able to produce clean logs.
        By default logger.info is printed to the cli if you need to print data.
        """
        logger.error('Not Implemented.')

        return 1
