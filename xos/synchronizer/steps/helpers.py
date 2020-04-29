# Copyright 2017-present Open Networking Foundation
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

from __future__ import absolute_import
from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class Helpers():
    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_onos_fabric_service(model_accessor, switch=None):
        fabric = None
        if switch:
            fabric = model_accessor.Service.objects.get(id=switch.fabric_id)
        else:
            fabric = model_accessor.Service.objects.get(name="fabric")
        onos_fabric_service = fabric.provider_services[0].leaf_model
        return onos_fabric_service

    @staticmethod
    def get_onos(model, model_accessor, onos=None):
        if(model.fabric != None):
            onos = Helpers.get_onos_fabric_service(model_accessor, model)
        else:
            fabric_service = model_accessor.FabricService.objects.all()
            if(len(fabric_service) == 1):
                onos = Helpers.get_onos_fabric_service(model_accessor)

        if not onos:
            log.error("Configuration error. Fabric Service without ONOS is not possible.")
            raise Exception("Configuration error. Fabric Service without ONOS is not possible.") 
        return onos
