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
import string
import traceback
import uuid
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook

from trestle import __version__
from trestle.core import const
from trestle.oscal import OSCAL_VERSION
from trestle.oscal.catalog import Catalog
from trestle.oscal.component import ComponentDefinition
from trestle.oscal.component import ControlImplementation
from trestle.oscal.component import DefinedComponent
from trestle.oscal.component import ImplementedRequirement
from trestle.oscal.component import Metadata
from trestle.oscal.component import Party
from trestle.oscal.component import Property
from trestle.oscal.component import Remarks
from trestle.oscal.component import ResponsibleParty
from trestle.oscal.component import ResponsibleRole
from trestle.oscal.component import Role
from trestle.oscal.component import SetParameter
from trestle.oscal.component import Statement
from trestle.tasks.base_task import TaskBase
from trestle.tasks.base_task import TaskOutcome
from trestle.utils.oscal_helper import CatalogHelper
from trestle.utils.parameter_helper import ParameterHelper

logger = logging.getLogger(__name__)


class XslxToOscalComponentDefinition(TaskBase):
    """
    Task to create OSCAL ComponentDefinition json.

    Attributes:
        name: Name of the task.
    """

    name = 'xslx-to-oscal-component-definition'
 
    def __init__(self, config_object: Optional[configparser.SectionProxy]) -> None:
        """
        Initialize trestle task xslx-to-oscal-component-definition.

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
        catalog_file = self._config.get('catalog-file')
        catalog_helper = CatalogHelper(catalog_file)
        spread_sheet = self._config.get('spread-sheet')
        if spread_sheet is None:
            logger.error(f'config missing "spread-sheet"')
            return TaskOutcome('failure')
        ipth = pathlib.Path(spread_sheet)
        odir = self._config.get('output-dir')
        opth = pathlib.Path(odir)
        self._overwrite = self._config.getboolean('output-overwrite', True)
        quiet = self._config.get('quiet', False)
        self._verbose = not quiet
        # insure output dir exists
        opth.mkdir(exist_ok=True, parents=True)
        # process spreadsheet
        if self._verbose:
            logger.info(f'input: {spread_sheet}')
        # calculate output file name & check writability
        oname = 'component-definition.json'
        ofile = opth / oname
        if not self._overwrite and pathlib.Path(ofile).exists():
            logger.error(f'output: {ofile} already exists')
            return TaskOutcome(mode + 'failure')
        # initialize
        defined_components = {}
        # load the .xlsl contents
        wb = load_workbook(spread_sheet)
        sheet_name = 'IBM Cloud Goals NIST'
        sheet_ranges = wb[sheet_name]
        component_names = []
        parameters = {}
        # accumulators
        self.rows_missing_goal_name_id = []
        self.rows_missing_controls = []
        self.rows_missing_parameters = []
        self.rows_missing_parameters_values = []
        # roles, parties, responsible-parties
        roles = [
            Role(id='prepared-by',title='Indicates the organization that created this content.'),
            Role(id='prepared-for',title='Indicates the organization for which this content was created..'),
            Role(id='content-approver',title='Indicates the organization responsible for all content represented in the "document".'),
        ]
        uuid01 = str(uuid.uuid4())
        uuid02 = str(uuid.uuid4())
        uuid03 = str(uuid.uuid4())
        parties = [
            Party(uuid=uuid01,
                  type='organization',
                  name='International Business Machines',
                  remarks='IBM'),
            Party(uuid=uuid02,
                  type='organization',
                  name='Customer',
                  remarks='organization to be customized at account creation only for their Component Definition'),
            Party(uuid=uuid03,
                  type='organization',
                  name='ISV',
                  remarks='organization to be customized at ISV subscription only for their Component Definition'),
        ]
        prepared_by = ResponsibleParty(
            party_uuids = [uuid01]
        )
        prepared_for = ResponsibleParty(
            party_uuids = [uuid02, uuid03]
        )
        content_approver = ResponsibleParty(
            party_uuids = [uuid01]
        )
        responsible_parties = { 
            'prepared-by': prepared_by,
            'prepared-for': prepared_for,
            'content-approver': content_approver,
        }
        # responsible-roles
        role_prepared_by = ResponsibleRole(
            party_uuids=[uuid01]
        )
        role_prepared_for = ResponsibleRole(
            party_uuids=[uuid02, uuid03]
        )
        role_content_approver = ResponsibleRole(
            party_uuids=[uuid01]
        )
        responsible_roles = { 
            'prepared-by': role_prepared_by,
            'prepared-for': role_prepared_for,
            'content-approver': role_content_approver,
        }
        # process each row of spread sheet
        for row in self._row_generator(sheet_ranges):
            # quit when first row with no goal_id encountered
            goal_id = self._get_goal_id(sheet_ranges, row)
            goal_name_id = self._get_goal_name_id(sheet_ranges, row)
            if goal_name_id is None:
                continue
            controls = self._get_controls(sheet_ranges, row)
            if len(controls) == 0:
                continue
            scc_check_name_id = str(goal_name_id)+'_check'
            # component
            component_name = self._get_component_name(sheet_ranges, row)
            if component_name not in component_names:
                logger.debug(f'component_name: {component_name}')
                component_names.append(component_name)
                component_title = component_name
                component_description = component_name
                defined_component = DefinedComponent(
                    description=component_description,
                    title=component_title,
                    type='Service',
                )
                defined_components[str(uuid.uuid4())] = defined_component
            else:
                for key in defined_components.keys():
                    defined_component = defined_components[key]
                    if component_name == defined_component.title:
                        break
            if component_name != defined_component.title:
                raise RuntimeError(f'component_name: {component_name}')
            # parameter
            parameter_name, parameter_description = self._get_parameter_name_and_description(sheet_ranges, row)
            if parameter_name is not None:
                parameter_helper = ParameterHelper(
                    values=self._get_parameter_values(sheet_ranges, row),
                    id=parameter_name,
                    label=parameter_description,
                    class_='scc_check_parameter',
                )
                parameter_helper.add_property(
                    name='scc_goal_version',
                    value=self._get_goal_version(),
                    class_='scc_goal_version',
                    remarks=goal_name_id,
                )
                parameter_helper.add_property(
                    name='scc_check_name_id',
                    value=scc_check_name_id,
                    class_='scc_check_name_id',
                    remarks=scc_check_name_id,
                )
                parameter_helper.add_property(
                    name='scc_check_version',
                    value=self._get_check_version(),
                    class_='scc_check_version',
                    remarks=scc_check_name_id,
                )
                parameters[str(uuid.uuid4())] = parameter_helper.get_parameter()
            # implemented requirements
            implemented_requirements = []
            controls = self._get_controls(sheet_ranges, row)
            goal_remarks = self._get_goal_remarks(sheet_ranges, row)
            parameter_value_default = self._get_parameter_value_default(sheet_ranges, row)
            for control in controls:
                control_uuid = self._get_control_uuid(control)
                prop1 = Property(
                    name='goal_name_id',
                    class_='scc_goal_name_id',
                    value=goal_name_id,
                    ns='http://ibm.github.io/compliance-trestle/schemas/oscal/cd/ibm-cloud',
                    remarks=Remarks(__root__=str(goal_remarks))
                )
                prop2 = Property(
                    name='goal_version',
                    class_='scc_goal_version',
                    value=self._get_goal_version(),
                    ns='http://ibm.github.io/compliance-trestle/schemas/oscal/cd/ibm-cloud',
                    remarks=Remarks(__root__=str(goal_name_id))
                )
                props = [prop1,prop2]
                control_id = catalog_helper.find_control_id(control)
                if control_id is None:
                    logger.info(f'row {row} control {control} not found in catalog')
                    control_id = control
                statement_id = control_id
                statement = Statement(
                    uuid=str(uuid.uuid4()),
                    description = f'{component_name} implements {statement_id}'
                    )
                statements = { statement_id: statement }
                implemented_requirement = ImplementedRequirement(
                    uuid=control_uuid,
                    description=control,
                    props=props,
                    control_id=control_id,
                    responsible_roles=responsible_roles,
                    statements=statements
                    )
                parameter_name = self._get_parameter_name(sheet_ranges, row)
                if parameter_name is None:
                    if row not in self.rows_missing_parameters:
                        self.rows_missing_parameters.append(row)
                else:
                    parameter_value_default = self._get_parameter_value_default(sheet_ranges, row)
                    if parameter_value_default is None:
                        if row not in self.rows_missing_parameters_values:
                            self.rows_missing_parameters_values.append(row)
                    else:
                        values = list(parameter_value_default)
                        set_parameter = SetParameter(values=values)
                        set_parameters = {}
                        #logger.info(f'use {row} {parameter_name} {values}')
                        set_parameters[parameter_name] = set_parameter
                        implemented_requirement.set_parameters = set_parameters
                implemented_requirements.append(implemented_requirement)
            # control implementations
            control_implementation = ControlImplementation(
                uuid=str(uuid.uuid4()),
                source='https://github.com/usnistgov/oscal-content/blob/master/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json',
                description=component_name+' implemented controls for NIST 800-53. It includes assessment asset configuration for CICD (and tbd runtime SCC)."',
                implemented_requirements=implemented_requirements,
            )
            if defined_component.control_implementations is None:
                defined_component.control_implementations = [control_implementation]
            else:
                defined_component.control_implementations.append(control_implementation)
        # create OSCAL ComponentDefinition
        metadata = Metadata(
            title='Component definition for NIST profiles',
            last_modified=self._timestamp,
            oscal_version=OSCAL_VERSION,
            version=__version__,
            roles=roles,
            parties=parties,
            responsible_parties=responsible_parties
        )
        component_definition = ComponentDefinition(
            uuid=str(uuid.uuid4()),
            metadata=metadata,
            components=defined_components,
            #params=parameters,
        )
        # write OSCAL ComponentDefinition to file
        if self._verbose:
            logger.info(f'output: {ofile}')
        component_definition.oscal_write(pathlib.Path(ofile))
        # issues
        if len(self.rows_missing_goal_name_id) > 0:
            logger.info(f'rows missing goal_name_id: {self.rows_missing_goal_name_id}')
        if len(self.rows_missing_controls) > 0:
            logger.info(f'rows missing controls: {self.rows_missing_controls}')
        if len(self.rows_missing_parameters) > 0:
            logger.info(f'rows missing parameters: {self.rows_missing_parameters}')
        if len(self.rows_missing_parameters_values) > 0:
            logger.info(f'rows missing parameters values: {self.rows_missing_parameters_values}')
        # <hack>
        tdir = self._config.get('output-dir')
        tdir = tdir.replace('component-definitions','catalogs')
        tpth = pathlib.Path(tdir)
        tname = 'catalog.json'
        tfile = tpth / tname
        parameter_helper.write_parameters_catalog(
            parameters=parameters, 
            timestamp=self._timestamp,
            oscal_version=OSCAL_VERSION,
            version=__version__,
            ofile=tfile,
            verbose=self._verbose,
        )
        #</hack>
        return TaskOutcome('success')
    
    def _row_generator(self, sheet_ranges):
        row = 1
        while True:
            row = row+1
            goal_id = self._get_goal_id(sheet_ranges, row)
            if goal_id is None:
                break
            yield row
    
    def _get_goal_version(self):
        return '1.0'
    
    def _get_check_version(self):
        return '1.0'
    
    def _get_control_uuid(self, control):
        value = str(uuid.uuid4())
        return value
    
    def _get_goal_id(self, sheet_ranges, row):
        col = 'b'
        value = sheet_ranges[col+str(row)].value
        return value
        
    def _get_goal_text(self, sheet_ranges, row):
        col = 'c'
        goal_text = sheet_ranges[col+str(row)].value
        # normalize & tokenize
        value = goal_text.replace('\t', ' ')
        return value
    
    def _get_controls(self, sheet_ranges, row):
        value = []
        for col in ['h', 'i', 'j', 'k', 'l', 'm', 'n']:
            control = sheet_ranges[col+str(row)].value
            if control is not None:
                control = ''.join(control.split())
                if len(control) > 0:
                    if ':' in control:
                        control = control.split(':')[0]
                    # remove alphabet part of control
                    for i in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o''p','q','r','s','t','u','v','w','x','y','z']:
                        needle = '('+i+')'
                        control = control.replace(needle,'')
                    control = control.lower()
                    # skip bogus control made up if dashes only
                    if len(control.replace('-','')) > 0:
                        if control not in value:
                            value.append(control)
        if len(value) == 0:
            self.rows_missing_controls.append(row)
        return value
        
    def _get_goal_name_id(self, sheet_ranges, row):
        col = 'r'
        value = sheet_ranges[col+str(row)].value
        if value is None:
            self.rows_missing_goal_name_id.append(row)
            value = self._get_goal_id(sheet_ranges, row)
        return value
    
    def _get_parameter_name(self, sheet_ranges, row):
        return self._get_parameter_name_and_description(sheet_ranges, row)[0]
    
    def _get_parameter_name_and_description(self, sheet_ranges, row):
        name = None
        description = None
        col = 'v'
        combined_values = sheet_ranges[col+str(row)].value
        if combined_values is not None:
            if '\n' in combined_values:
                parameter_parts = combined_values.split('\n')
            elif '\t' in combined_values:
                parameter_parts = combined_values.split('\t')
            elif ' ' in combined_values:
                parameter_parts = combined_values.split(' ',1)
            if len(parameter_parts) != 2:
                raise RuntimeError(f'row {row} col {col} unable to parse')
            name = parameter_parts[1]
            description = parameter_parts[0]
        value = name, description
        return value
    
    def _get_parameter_value_default(self, sheet_ranges, row):
        name = None
        description = None
        col = 'w'
        value = sheet_ranges[col+str(row)].value
        if value is not None:
            value = str(value).split(',')[0].strip()
        return value
    
    def _get_parameter_values(self, sheet_ranges, row):
        name = None
        description = None
        col = 'w'
        value = sheet_ranges[col+str(row)].value
        if value is None:
            raise RuntimeError(f'row {row} col {col} missing value')
        return value
    
    def _get_goal_remarks(self, sheet_ranges, row):
        goal_text = self._get_goal_text(sheet_ranges, row)
        tokens = goal_text.split()
        if tokens[0] != 'Check':
            raise ValueError(f'{row},0 is {tokens[0]} expected "Check"')
        if tokens[1] != 'whether':
            raise ValueError(f'{row},1 expected "whether"')
        tokens.pop(0)
        tokens[0] = 'Ensure'
        value = ' '.join(tokens)
        return value
    
    def _get_component_name(self, sheet_ranges, row):
        goal_text = self._get_goal_text(sheet_ranges, row)
        tokens = goal_text.split()
        code, value = self._get_component_part1(row, tokens)
        return value
    
    def _get_component_part1(self, row, tokens):
        code = 0
        value = code, ' '.join(tokens)
        if tokens[0] != 'Check':
            raise ValueError(f'{row},0 is {tokens[0]} expected "Check"')
        if tokens[1] != 'whether':
            raise ValueError(f'{row},1 expected "whether"')
        if len(tokens) > 10:
            code = 10
            if f'{tokens[9]} {tokens[10]}' in [
                'in IAM',
                'IBM Cloud',
                ]:
                value = code, f'IAM'
                return value
        if len(tokens) > 3:
            code = 3
            if tokens[2] in [
                'Cloudant',
                'IBMid',
                'IAM',
                'VPN',
                ]:
                value = code, f'{tokens[2]}'
                return value
            if tokens[2] in [
                'IAM-enabled',
                ]:
                value = code, f'IAM'
                return value
        if len(tokens) > 4: 
            code = 4 
            if f'{tokens[2]} {tokens[3]}' in [
                'App ID',
                'Block Storage',
                'Certificate Manager',
                'Container Registry',
                'Continuous Delivery',
                'Event Streams',
                'Key Protect',
                'Kubernetes Service',
                'Secrets Manager',
                'Security Groups',
                'Security Insights',
                'Transit Gateway',
                'Virtual Servers',
                'Vulnerability Advisor',
                ]:
                value = code, f'{tokens[2]} {tokens[3]}'
                return value
        if len(tokens) > 5:
            code = 5
            if f'{tokens[2]} {tokens[3]} {tokens[4]}' in [
                'Application Load Balancer',
                'Bare Metal Servers',
                'Cloud Internet Services',
                'Cloud Object Storage',
                'Direct Link (2.0)',
                'IBM Activity Tracker',
                'IBM Cloud Monitoring',
                'Virtual Private Cloud',
                ]:
                value = code, f'{tokens[2]} {tokens[3]} {tokens[4]}'
                return value
            if f'{tokens[2]} {tokens[3]} {tokens[4]}' in [
                'a support role',
                'account access is',
                'account has a',
                'account has no',
                'API keys are',
                'authorized IP ranges',
                'Identity and Access',
                'multifactor authentication (MFA)',
                'permissions for API',
                'permissions for service',
                'security questions are',
                'the HIPAA supported',
                'the EU supported',
                'there are no',
                'user list visibility',
                ]:
                value = code, f'IAM'
                return value
            if f'{tokens[2]} {tokens[3]} {tokens[4]}' in [
                'OS disks are',
                'data disks are',
                'unattached disks are',
                ]:
                value = code, f'Disks'
                return value
            if f'{tokens[2]} {tokens[3]} {tokens[4]}' in [
                'all network interfaces',
                'all virtual server',
                'Flow Logs for',
                'no VPC access',
                ]:
                value = code, f'Virtual Private Cloud'
                return value
            if f'{tokens[2]} {tokens[3]} {tokens[4]}' in [
                'account is configured',
                ]:
                value = code, f'VPN'
                return value
            if f'{tokens[2]} {tokens[3]}' in [
                'Databases for',
                ]:
                value = code, f'{tokens[2]} {tokens[3]} {tokens[4]}'
                return value
        if len(tokens) > 6:
            code = 6
            if f'{tokens[2]} {tokens[3]} {tokens[4]} {tokens[5]}' in [
                'Hyper Protect Crypto Services',
                ]:
                value = code, f'{tokens[2]} {tokens[3]} {tokens[4]} {tokens[5]}'
                return value
        return value
