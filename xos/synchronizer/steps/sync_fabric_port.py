
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
from synchronizers.new_base.modelaccessor import FabricService, SwitchPort

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class SyncFabricPort(SyncStep):
    provides = [SwitchPort]
    observes = SwitchPort

    def get_fabric_onos_service_internal(self):
        # There will be a ServiceInstanceLink from the FabricService to the Fabric ONOS App
        fs = FabricService.objects.first()
        for link in fs.subscribed_links.all():
            if link.provider_service_instance:
                # Cast from ServiceInstance to ONOSApp
                service_instance = link.provider_service_instance.leaf_model
                # Cast from Service to ONOSService
                return service_instance.owner.leaf_model

        return None

    def get_fabric_onos_service(self):
        fos = self.get_fabric_onos_service_internal()
        if not fos:
            raise Exception("Fabric ONOS service not found")
        return fos

    def sync_record(self, model):
        interfaces = []
        for intf in model.interfaces.all():
            i = {
                "name" : intf.name,
                "ips" : [ intf.ips ]
            }
            if intf.vlanUntagged:
                i["vlan-untagged"] = intf.vlanUntagged
            interfaces.append(i)

        # Send port config to onos-fabric netcfg
        data = {
          "ports": {
            "%s/%s" % (model.switch.ofId, model.portId) : {
              "interfaces" : interfaces
            }
          }
        }

        onos = self.get_fabric_onos_service()

        url = 'http://%s:%s/onos/v1/network/configuration/' % (onos.rest_hostname, onos.rest_port)
        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to add port %s into ONOS" % model.name)
        else:
            try:
                print r.json()
            except Exception:
                print r.text

    def delete_record(self, switch):
        pass
