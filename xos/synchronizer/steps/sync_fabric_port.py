
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
from synchronizers.new_base.syncstep import SyncStep, DeferredException, model_accessor
from synchronizers.new_base.modelaccessor import FabricService, SwitchPort

from xosconfig import Config
from multistructlog import create_logger

from helpers import Helpers

log = create_logger(Config().get('logging'))

class SyncFabricPort(SyncStep):
    provides = [SwitchPort]
    observes = SwitchPort

    def sync_record(self, model):
        log.info("Adding port %s/%s to onos-fabric" % (model.switch.ofId, model.portId))
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
            raise Exception("Failed to add port %s into ONOS" % model.name)
        else:
            try:
                log.info("Port %s/%s response" % (model.switch.ofId, model.portId), json=r.json())
            except Exception:
                log.info("Port %s/%s response" % (model.switch.ofId, model.portId), text=r.text)

    def delete_record(self, model):
        log.info("Removing port %s/%s from onos-fabric" % (model.switch.ofId, model.portId))
        onos = Helpers.get_onos_fabric_service()
        url = 'http://%s:%s/onos/v1/network/configuration/ports/%s/%s' % (onos.rest_hostname, onos.rest_port, model.switch.ofId, model.portId)

        r = requests.delete(url, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 204:
            log.error(r.text)
            raise Exception("Failed to remove port %s from ONOS" % model.name)
