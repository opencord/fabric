
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
import urllib
from requests.auth import HTTPBasicAuth
from synchronizers.new_base.syncstep import SyncStep, DeferredException, model_accessor
from synchronizers.new_base.modelaccessor import FabricService, SwitchPort, PortInterface, FabricIpAddress

from xosconfig import Config
from multistructlog import create_logger

from helpers import Helpers

log = create_logger(Config().get('logging'))

class SyncFabricPort(SyncStep):
    provides = [SwitchPort]
    observes = [SwitchPort, PortInterface, FabricIpAddress]

    def sync_record(self, model):

        if model.leaf_model_name == "PortInterface":
            log.info("Receivent update for PortInterface", port=model.port.portId, interface=model)
            return self.sync_record(model.port)

        if model.leaf_model_name == "FabricIpAddress":
            log.info("Receivent update for FabricIpAddress", port=model.interface.port.portId, interface=model.interface.name, ip=model.ip)
            return self.sync_record(model.interface.port)

        log.info("Adding port %s/%s to onos-fabric" % (model.switch.ofId, model.portId))
        interfaces = []
        for intf in model.interfaces.all():
            i = {
                "name" : intf.name,
                "ips" : [ i.ip for i in intf.ips.all() ]
            }
            if intf.vlanUntagged:
                i["vlan-untagged"] = intf.vlanUntagged
            interfaces.append(i)

        # Send port config to onos-fabric netcfg
        data = {
            "ports": {
                "%s/%s" % (model.switch.ofId, model.portId) : {
                    "interfaces": interfaces,
                    "hostLearning": {
                        "enabled": model.host_learning
                    }
                }
            }
        }

        log.debug("Port %s/%s data" % (model.switch.ofId, model.portId), data=data)

        onos = Helpers.get_onos_fabric_service()

        url = 'http://%s:%s/onos/v1/network/configuration/' % (onos.rest_hostname, onos.rest_port)

        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to add port  %s/%s into ONOS" % (model.switch.ofId, model.portId))
        else:
            try:
                log.info("Port %s/%s response" % (model.switch.ofId, model.portId), json=r.json())
            except Exception:
                log.info("Port %s/%s response" % (model.switch.ofId, model.portId), text=r.text)

    def delete_netcfg_item(self, partial_url):
        onos = Helpers.get_onos_fabric_service()
        url = 'http://%s:%s/onos/v1/network/configuration/ports/%s' % (onos.rest_hostname, onos.rest_port, partial_url)

        r = requests.delete(url, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 204:
            log.error(r.text)
            raise Exception("Failed to %s port %s from ONOS" % url)

    def delete_record(self, model):
        if model.leaf_model_name == "PortInterface":
            log.info("Received update for PortInterface", port=model.port.portId, interface=model.name)
            log.info("Removing port interface %s from port %s/%s in onos-fabric" % (model.name, model.port.switch.ofId, model.port.portId))

            # resync the existing interfaces
            return self.sync_record(model.port)

        if model.leaf_model_name == "FabricIpAddress":
            # TODO add unit tests
            log.info("Received update for FabricIpAddress", port=model.interface.port.portId, interface=model.interface.name, ip=model.ip)
            log.info("Removing IP %s from interface %s, on port %s/%s in onos-fabric" % (model.ip, model.interface.name, model.interface.port.switch.ofId, model.interface.port.portId))

            # resync the existing interfaces
            return self.sync_record(model.interface.port)

        log.info("Removing port %s/%s from onos-fabric" % (model.switch.ofId, model.portId))

        key = "%s/%s" % (model.switch.ofId, model.portId)
        key = urllib.quote(key, safe='')

        # deleting the port
        self.delete_netcfg_item(key)
