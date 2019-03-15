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

from xossynchronizer.pull_steps.pullstep import PullStep

from xosconfig import Config
from multistructlog import create_logger

import requests
from requests import ConnectionError
from requests.models import InvalidURL
from requests.auth import HTTPBasicAuth

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = create_logger(Config().get('logging'))

class SwitchPortPullStep(PullStep):
    def __init__(self, model_accessor):
        # TODO(smbaker): observied_model probably isn't used
        super(SwitchPortPullStep, self).__init__(model_accessor=model_accessor, observed_model="SwitchPort")

    def get_onos_service(self, fabric_service):
        for service in fabric_service.provider_services:
            # TODO(smbaker: find a better way than name comparison
            if not "onos" in service.name:
                continue
            return service.leaf_model
        return None

    def pull_records(self):
        log.debug("pulling switches from ONOS")

        for fabric_service in self.model_accessor.FabricService.objects.all():
            onos = self.get_onos_service(fabric_service)
            if not onos:
                log.warning("No onos service for fabric service", fabric_service=fabric_service)

            # TODO(smbaker): FabricSwitch should be ForeignKey linked to FabricService
            for switch in self.model_accessor.Switch.objects.all():
                url = "http://%s:%s/onos/v1/devices/%s/ports" % (onos.rest_hostname, onos.rest_port, switch.ofId)

                r = requests.get(url, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

                if r.status_code != 200:
                    log.error(r.text)
                    raise Exception("Failed query switch %s from ONOS" % switch.ofId)

                response = r.json()

                log.info("Switch %s port response" % switch.ofId, json=response)

                for port in response.get("ports", []):
                    try:
                        portId = int(port["port"])
                    except ValueError:
                        continue

                    xos_port = self.model_accessor.SwitchPort.objects.filter(switch_id=switch.id,
                                                                            portId=portId)
                    if not xos_port:
                        log.warning("Switch %s port %s not found" % (switch.ofId, portId))
                        continue

                    xos_port = xos_port[0]

                    isEnabled = port["isEnabled"]
                    oper_status = {True: "enabled", False: "disabled"}[isEnabled]

                    if oper_status != xos_port.oper_status:
                        xos_port.oper_status = oper_status
                        xos_port.save_changed_fields()
