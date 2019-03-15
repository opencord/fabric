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

import unittest
import json
from mock import patch, Mock

import os
import sys

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


class TestOnosPortEvent(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("fabric", "fabric.xproto"),
                                              ("onos-service", "onos.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor)  # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from mock_modelaccessor import MockObjectList
        from onos_event import OnosPortEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.event_step = OnosPortEventStep

        self.fabric_service = FabricService(name="fabric",
                                            id=1112,
                                            backend_code=1,
                                            backend_status="succeeded")

        self.switch = Switch(name="switch1",
                             ofId="of:0000000000000001",
                             backend_code=1,
                             backend_status="succeeded")

        self.port1 = SwitchPort(name="switch1port1",
                                switch=self.switch,
                                switch_id=self.switch.id,
                                portId="1",
                                oper_status=None,
                                backend_code=1,
                                backend_status="succeeded")

        self.port2 = SwitchPort(name="switch1port2",
                                switch=self.switch,
                                switch_id=self.switch.id,
                                portId="2",
                                oper_status=None,
                                backend_code=1,
                                backend_status="succeeded")

        self.switch.ports = MockObjectList([self.port1, self.port2])

        self.log = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_process_event_enable(self):
        with patch.object(Switch.objects, "get_items") as switch_objects, \
             patch.object(SwitchPort.objects, "get_items") as switchport_objects:
            switch_objects.return_value = [self.switch]
            switchport_objects.return_value = [self.port1, self.port2]

            event_dict = {"deviceId": self.switch.ofId,
                          "portId": self.port1.portId,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.port1.oper_status, "enabled")

    def test_process_event_disable(self):
        with patch.object(Switch.objects, "get_items") as switch_objects, \
             patch.object(SwitchPort.objects, "get_items") as switchport_objects:
            switch_objects.return_value = [self.switch]
            switchport_objects.return_value = [self.port1, self.port2]

            event_dict = {"deviceId": self.switch.ofId,
                          "portId": self.port1.portId,
                          "enabled": False}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.port1.oper_status, "disabled")

    def test_process_event_no_switch(self):
        with patch.object(Switch.objects, "get_items") as switch_objects, \
             patch.object(SwitchPort.objects, "get_items") as switchport_objects:
            switch_objects.return_value = [self.switch]
            switchport_objects.return_value = [self.port1, self.port2]

            event_dict = {"deviceId": "doesnotexist",
                          "portId": self.port1.portId,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)

            step.process_event(event)

            # should not have changed
            self.assertEqual(self.port1.oper_status, None)

    def test_process_event_no_port(self):
        with patch.object(Switch.objects, "get_items") as switch_objects, \
             patch.object(SwitchPort.objects, "get_items") as switchport_objects:
            switch_objects.return_value = [self.switch]
            switchport_objects.return_value = [self.port1, self.port2]

            event_dict = {"deviceId": self.switch.ofId,
                          "portId": "doesnotexist",
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)

            step.process_event(event)

            # should not have changed
            self.assertEqual(self.port1.oper_status, None)


if __name__ == '__main__':
    unittest.main()
