
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

import json
from xossynchronizer.event_steps.eventstep import EventStep
from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))


class OnosPortEventStep(EventStep):
    topics = ["onos.events.port"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(OnosPortEventStep, self).__init__(*args, **kwargs)

    def process_event(self, event):
        value = json.loads(event.value)

        switch = self.model_accessor.Switch.objects.filter(
            ofId=value["deviceId"]
        )
        if not switch:
            log.info("Event for unknown switch", deviceId=value["deviceId"])
            return

        switch = switch[0]

        port = self.model_accessor.SwitchPort.objects.filter(
            switch_id=switch.id,
            portId=value["portId"]
        )
        if not port:
            log.info("Event for unknown port",
                     deviceId=value["deviceId"],
                     portId=value["portId"])
            return

        port = port[0]

        oper_status = "enabled" if value["enabled"] else "disabled"
        if oper_status != port.oper_status:
            port.oper_status = oper_status
            port.save_changed_fields()
