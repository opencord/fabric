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
from requests.auth import HTTPBasicAuth
from requests.models import InvalidURL

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import Helpers

log = create_logger(Config().get('logging'))

class ONOSDevicePullStep(PullStep):
    def __init__(self, model_accessor):
        super(ONOSDevicePullStep, self).__init__(model_accessor=model_accessor)

    def get_onos_fabric_service(self):
        # FIXME do not select by name but follow ServiceDependency
        fabric_service = self.model_accessor.Service.objects.get(name="fabric")
        onos_fabric_service = fabric_service.provider_services[0].leaf_model
        return onos_fabric_service

    def pull_records(self):
        log.debug("[ONOS device pull step] pulling devices from ONOS")

        onos = self.get_onos_fabric_service()

        url = 'http://%s:%s/onos/v1/devices/' % (onos.rest_hostname, onos.rest_port)

        r = requests.get(url, auth=HTTPBasicAuth(onos.rest_username, onos.rest_password))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to get onos devices")
        else:
            try:
                log.info("Get devices response", json=r.json())
            except Exception:
                log.info("Get devices exception response", text=r.text)

        for device in r.json()["devices"]:
            if device["type"] != "SWITCH":
                continue

            xos_devices = self.model_accessor.Switch.objects.filter(ofId = device["id"])
            if not xos_devices:
                continue

            xos_device = xos_devices[0]
            changed = False

            managementAddress = device.get("annotations", {}).get("managementAddress")
            if (xos_device.managementAddress != managementAddress):
                log.info("Setting managementAddress on switch %s to %s" % (xos_device.id, managementAddress))
                xos_device.managementAddress = managementAddress
                changed = True

            if changed:
                xos_device.save_changed_fields()
