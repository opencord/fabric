
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

import requests
from requests.auth import HTTPBasicAuth
from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import FabricService, Switch

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class SyncFabricSwitch(SyncStep):
    provides = [Switch]
    observes = Switch

    def get_fabric_onos_service_internal(self):
        # There will be a ServiceInstanceLink from the FabricService to the Fabric ONOS App
        fs = FabricService.objects.first()
        for link in fs.subscribed_links.all():
            if link.provider_service_instance:
                # cast from ServiceInstance to ONOSApp
                service_instance = link.provider_service_instance.leaf_model
                # cast from Service to ONOSService
                return service_instance.owner.leaf_model

        return None

    def get_fabric_onos_service(self):
        fos = self.get_fabric_onos_service_internal()
        if not fos:
            raise Exception("Fabric ONOS service not found")
        return fos

    def sync_record(self, model):
        # Send device info to onos-fabric netcfg
        data = {
          "devices": {
            model.ofId: {
              "basic": {
                "name": model.name,
                "driver": model.driver
              },
              "segmentrouting" : {
                "name" : model.name,
                "ipv4NodeSid" : model.ipv4NodeSid,
                "ipv4Loopback" : model.ipv4Loopback,
                "routerMac" : model.routerMac,
                "isEdgeRouter" : model.isEdgeRouter,
                "adjacencySids" : []
              }
            }
          }
        }

        onos = self.get_fabric_onos_service()

        url = 'http://%s:%s/onos/v1/network/configuration/' % (onos.rest_hostname, onos.rest_port)
        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to add device %s into ONOS" % model.name)
        else:
            try:
                print r.json()
            except Exception:
                print r.text

    def delete_record(self, switch):
        pass
