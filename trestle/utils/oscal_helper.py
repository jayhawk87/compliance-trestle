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
from trestle.oscal.catalog import Catalog

logger = logging.getLogger(__name__)


class CatalogHelper():
    
    def __init__(self, catalog_file) -> None:
        self._catalog = Catalog.oscal_read(pathlib.Path(catalog_file))
        logger.info(f'catalog: {catalog_file}')
        
    def _find_property(self, control, ctrl_name):
        value = None
        for prop in control.props:
            if prop.name == 'label':
                lhs = prop.value.strip().upper()
                rhs = ctrl_name.strip().upper()
                if lhs == rhs:
                    value = control.id
                    return value
                break
        if hasattr(control, 'controls'):
            if control.controls is not None:
                for embedded_control in control.controls:
                    value = self._find_property(embedded_control, ctrl_name)
                    if value is not None:
                        return value
        return value
                
    def find_control_id(self, ctrl_name):
        value = None
        for group in self._catalog.groups:
            for control in group.controls:
                value = self._find_property(control, ctrl_name)
                if value is not None:
                    return value
        return value
    