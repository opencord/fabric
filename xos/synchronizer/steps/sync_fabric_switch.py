
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

#from __future__ import absolute_import

import requests
from requests.auth import HTTPBasicAuth
from xossynchronizer.steps.syncstep import SyncStep
from xossynchronizer.modelaccessor import FabricService, Switch, model_accessor

from xosconfig import Config
from multistructlog import create_logger

from helpers import Helpers

log = create_logger(Config().get('logging'))


class SyncFabricSwitch(SyncStep):
    provides = [Switch]
    observes = Switch

    def sync_record(self, model):
        log.info("Adding switch %s to onos-fabric" % model.name)
        # Send device info to onos-fabric netcfg
        data = {
            "devices": {
                model.ofId: {
                    "basic": {
                        "name": model.name,
                        "driver": model.driver,
                        "pipeconf": model.pipeconf,
                        "managementAddress": model.managementAddress
                    },
                    "segmentrouting": {
                        "name": model.name,
                        "ipv4NodeSid": model.ipv4NodeSid,
                        "ipv4Loopback": model.ipv4Loopback,
                        "routerMac": model.routerMac,
                        "isEdgeRouter": model.isEdgeRouter,
                        "adjacencySids": [],
                    }
                }
            }
        }

        onos = Helpers.get_onos_fabric_service(model_accessor=self.model_accessor)

        url = 'http://%s:%s/onos/v1/network/configuration/' % (onos.rest_hostname, onos.rest_port)
        r = requests.post(url, json=data, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to add device %s into ONOS: %s" % (model.name, r.text))
        else:
            try:
                log.info("result", json=r.json())
            except Exception:
                log.info("result", text=r.text)

    def delete_record(self, model):
        log.info("Removing switch %s from onos-fabric" % model.name)
        onos = Helpers.get_onos_fabric_service(model_accessor=self.model_accessor)
        url = 'http://%s:%s/onos/v1/network/configuration/devices/%s' % (
            onos.rest_hostname, onos.rest_port, model.ofId)

        r = requests.delete(url, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 204:
            log.error(r.text)
            raise Exception("Failed to remove switch %s from ONOS" % model.name)
