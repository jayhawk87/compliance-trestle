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
"""OSCAL transformation tasks."""

import configparser
import datetime
import logging
import json
import pathlib
import traceback
import uuid
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook

from trestle import __version__
from trestle.core import const
from trestle.oscal import OSCAL_VERSION
from trestle.oscal.profile import Import
from trestle.oscal.profile import Metadata
from trestle.oscal.profile import Modify
from trestle.oscal.profile import ParameterValue
from trestle.oscal.profile import Profile
from trestle.oscal.profile import SelectControlById
from trestle.oscal.profile import SetParameter
from trestle.tasks.base_task import TaskBase
from trestle.tasks.base_task import TaskOutcome

logger = logging.getLogger(__name__)


class XslxToOscalProfile(TaskBase):
    """
    Task to create OSCAL Profile json.

    Attributes:
        name: Name of the task.
    """

    name = 'xslx-to-oscal-profile'
 
    def __init__(self, config_object: Optional[configparser.SectionProxy]) -> None:
        """
        Initialize trestle task xslx-to-oscal-profile.

        Args:
            config_object: Config section associated with the task.
        """
        super().__init__(config_object)
        self._timestamp = datetime.datetime.utcnow().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat()
        
    def print_info(self) -> None:
        """Print the help string."""
        logger.info(f'Help information for {self.name} task.')
       
    def simulate(self) -> TaskOutcome:
        """Provide a simulated outcome."""
        return TaskOutcome('simulated-success')
        
    def execute(self) -> TaskOutcome:
        """Provide an executed outcome."""
        try:
            return self._execute()
        except Exception:
            logger.info(traceback.format_exc())
            return TaskOutcome('failure')
        
    def _execute(self) -> TaskOutcome:
        if not self._config:
            logger.error(f'config missing')
            return TaskOutcome('failure')
        # process config
        idir = self._config.get('input-dir')
        if idir is None:
            logger.error(f'config missing "input-dir"')
            return TaskOutcome('failure')
        ipth = pathlib.Path(idir)
        odir = self._config.get('output-dir')
        opth = pathlib.Path(odir)
        self._overwrite = self._config.getboolean('output-overwrite', True)
        quiet = self._config.get('quiet', False)
        self._verbose = not quiet
        # insure output dir exists
        opth.mkdir(exist_ok=True, parents=True)
        # process each .xlsx file in folder
        for ifile in sorted(ipth.iterdir()):
            if ifile.name.startswith('.'):
                continue
            if ifile.suffix != '.xlsx':
                continue
            if self._verbose:
                logger.info(f'input: {ifile}')
            # calculate output file name & check writability
            oname = ifile.stem + '.oscal' + '.json'
            ofile = opth / oname
            if not self._overwrite and pathlib.Path(ofile).exists():
                logger.error(f'output: {ofile} already exists')
                return TaskOutcome(mode + 'failure')
            # load the .xlsl contents
            wb = load_workbook(ifile)
            sheet_name = 'IBM Cloud Goals NIST'
            sheet_ranges = wb[sheet_name]
            row = 1
            set_parameters = {}
            controls = []
            while True:
                row = row+1
                # normalize control and add to list if not already present
                for col in ['h', 'i', 'j', 'k', 'l', 'm', 'n']:
                    control = sheet_ranges[col+str(row)].value
                    if control is not None:
                        control = ''.join(control.split())
                        if len(control) > 0:
                            if ':' in control:
                                control = control.split(':')[0]
                            for i in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o''p','q','r','s','t','u','v','w','x','y','z']:
                                needle = '('+i+')'
                                control = control.replace(needle,'')
                            control = control.lower()
                            # skip bogus control made up if dashes only
                            if len(control.replace('-','')) > 0:
                                if control not in controls:
                                    controls.append(control)
                # insure goal-id
                goal_id = sheet_ranges['b'+str(row)]
                # quit loop when row has no goal id's
                if goal_id.value is None:
                    logger.debug(f'no Goal ID in col[b], skip: {row}')
                    break
                goal_text = sheet_ranges['c'+str(row)].value.strip()
                # skip row if no Parameter
                parameter = sheet_ranges['v'+str(row)]
                if parameter.value is None:
                    logger.debug(f'no Parameter in col[v], skip: {row}')
                    continue
                # skip row if no separation between description and id
                parameter_parts = parameter.value.split('\n')
                if len(parameter_parts) != 2:
                    logger.warning(f'missing line end?:    {goal_id.value} {parameter.value}')
                    continue
                description = parameter_parts[0]
                id = parameter_parts[1]
                alternatives = sheet_ranges['w'+str(row)]
                # get values, only keep first one
                values = alternatives.value
                if values is None:
                    logger.warning(f'missing alternative?: {goal_id.value} {alternatives.value}')
                values = str(values)
                if ',' in values:
                    values = values.split(',')[0]
                # create set parameter and add to map
                parameter_value = ParameterValue(
                    __root__=values
                )
                set_parameter = SetParameter(
                    class_=description,
                    usage=goal_text,
                    values=[parameter_value]
                )
                set_parameters[id] = set_parameter
                logger.debug(f'{goal_id.value} {description} {id} {values}')
            # create OSCAL Profile
            metadata = Metadata(
                title='NIST IBM Goals',
                last_modified=self._timestamp,
                oscal_version=OSCAL_VERSION,
                version=__version__
            )
            select_control_by_id = SelectControlById(
                with_ids=sorted(controls)
            )
            import_ = Import(
                href='https://csrc.nist.gov/CSRC/media/Publications/sp/800-53/rev-5/final/documents/sp800-53r5-control-catalog.xlsx',
                include_controls=[select_control_by_id]
            )
            imports = [import_]
            modify = Modify(
                set_parameters=set_parameters)
            profile = Profile(
                uuid=str(uuid.uuid4()),
                metadata=metadata,
                imports=imports,
                modify=modify
            )
            # write OSCAL Profile to file
            if self._verbose:
                logger.info(f'output: {ofile}')
            profile.oscal_write(pathlib.Path(ofile))
        return TaskOutcome('success')
