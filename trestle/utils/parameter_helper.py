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
"""OSCAL utilities."""

import logging
import pathlib
import uuid

from trestle.oscal.catalog import Catalog
from trestle.oscal.catalog import Metadata
from trestle.oscal.catalog import Parameter
from trestle.oscal.catalog import ParameterGuideline
from trestle.oscal.catalog import ParameterValue

logger = logging.getLogger(__name__)


class ParameterHelper():
    """Parameter Helper class is a temporary hack because Component Definition does not support Parameters."""

    def __init__(self, values, id_, label, class_, usage, guidelines) -> None:
        """Initialize."""
        self._parameter_values = ParameterValue(__root__=str(values))
        self._id = id_
        self._label = label
        self._class_ = class_
        self._usage = usage
        self._guidelines = ParameterGuideline(prose=guidelines)

    def get_parameter(self):
        """Get parameter."""
        parameter = Parameter(
            id=self._id,
            label=self._label,
            class_=self._class_,
            usage=self._usage,
            guidelines=[self._guidelines],
            values=[self._parameter_values]
        )
        return parameter

    def write_parameters_catalog(
        self,
        parameters,
        timestamp,
        oscal_version,
        version,
        ofile,
        verbose,
    ):
        """Write parameters catalog."""
        parameter_metadata = Metadata(
            title='Component Parameters',
            last_modified=timestamp,
            oscal_version=oscal_version,
            version=version,
        )
        parameter_catalog = Catalog(
            uuid=str(uuid.uuid4()),
            metadata=parameter_metadata,
            params=list(parameters.values()),
        )
        if verbose:
            logger.info(f'output: {ofile}')
        parameter_catalog.oscal_write(pathlib.Path(ofile))
