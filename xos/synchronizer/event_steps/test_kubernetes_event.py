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

import imp
import unittest
import json
from mock import patch, call, Mock
import os
import sys


test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


class TestKubernetesEvent(unittest.TestCase):

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
        imp.reload(mock_modelaccessor)  # in case nose2 loaded it in a previous test
        imp.reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from mock_modelaccessor import MockObjectList
        from kubernetes_event import KubernetesPodDetailsEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.event_step = KubernetesPodDetailsEventStep

        self.onos = ONOSService(name="myonos",
                                id=1111,
                                rest_hostname="onos-url",
                                rest_port="8181",
                                rest_username="karaf",
                                rest_password="karaf",
                                backend_code=1,
                                backend_status="succeeded")

        self.fabric_service = FabricService(name="fabric",
                                            id=1112,
                                            backend_code=1,
                                            backend_status="succeeded",
                                            provider_services=[self.onos])

        self.switch = Switch(name="switch1",
                             backend_code=1,
                             backend_status="succeeded")

        self.port1 = SwitchPort(name="switch1port1",
                                switch=self.switch,
                                backend_code=1,
                                backend_status="succeeded")

        self.port2 = SwitchPort(name="switch1port2",
                                switch=self.switch,
                                backend_code=1,
                                backend_status="succeeded")

        self.switch.ports = MockObjectList([self.port1, self.port2])

        self.log = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_process_event(self):
        with patch.object(FabricService.objects, "get_items") as fabric_service_objects, \
                patch.object(Service.objects, "get_items") as service_objects, \
                patch.object(Switch.objects, "get_items") as switch_objects, \
                patch.object(Switch, "save", autospec=True) as switch_save, \
                patch.object(SwitchPort, "save", autospec=True) as switchport_save:
            fabric_service_objects.return_value = [self.fabric_service]
            service_objects.return_value = [self.onos, self.fabric_service]
            switch_objects.return_value = [self.switch]

            event_dict = {"status": "created",
                          "labels": {"xos_service": "myonos"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.switch.backend_code, 0)
            self.assertEqual(self.switch.backend_status, "resynchronize due to kubernetes event")

            switch_save.assert_called_with(self.switch, update_fields=["updated", "backend_code", "backend_status"],
                                           always_update_timestamp=True)

            self.assertEqual(self.port1.backend_code, 0)
            self.assertEqual(self.port1.backend_status, "resynchronize due to kubernetes event")

            self.assertEqual(self.port2.backend_code, 0)
            self.assertEqual(self.port2.backend_status, "resynchronize due to kubernetes event")

            switchport_save.assert_has_calls(
                [
                    call(
                        self.port1,
                        update_fields=[
                            "updated",
                            "backend_code",
                            "backend_status"],
                        always_update_timestamp=True),
                    call(
                        self.port2,
                        update_fields=[
                            "updated",
                            "backend_code",
                            "backend_status"],
                        always_update_timestamp=True)])

    def test_process_event_unknownstatus(self):
        with patch.object(FabricService.objects, "get_items") as fabric_service_objects, \
                patch.object(Service.objects, "get_items") as service_objects, \
                patch.object(Switch.objects, "get_items") as switch_objects, \
                patch.object(Switch, "save") as switch_save, \
                patch.object(SwitchPort, "save") as switchport_save:
            fabric_service_objects.return_value = [self.fabric_service]
            service_objects.return_value = [self.onos, self.fabric_service]
            switch_objects.return_value = [self.switch]

            event_dict = {"status": "something_else",
                          "labels": {"xos_service": "myonos"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.switch.backend_code, 1)
            self.assertEqual(self.switch.backend_status, "succeeded")

            switch_save.assert_not_called()

            self.assertEqual(self.port1.backend_code, 1)
            self.assertEqual(self.port1.backend_status, "succeeded")

            self.assertEqual(self.port2.backend_code, 1)
            self.assertEqual(self.port2.backend_status, "succeeded")

            switchport_save.assert_not_called()

    def test_process_event_unknownservice(self):
        with patch.object(FabricService.objects, "get_items") as fabric_service_objects, \
                patch.object(Service.objects, "get_items") as service_objects, \
                patch.object(Switch.objects, "get_items") as switch_objects, \
                patch.object(Switch, "save") as switch_save, \
                patch.object(SwitchPort, "save") as switchport_save:
            fabric_service_objects.return_value = [self.fabric_service]
            service_objects.return_value = [self.onos, self.fabric_service]
            switch_objects.return_value = [self.switch]

            event_dict = {"status": "created",
                          "labels": {"xos_service": "something_else"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.switch.backend_code, 1)
            self.assertEqual(self.switch.backend_status, "succeeded")

            switch_save.assert_not_called()

            self.assertEqual(self.port1.backend_code, 1)
            self.assertEqual(self.port1.backend_status, "succeeded")

            self.assertEqual(self.port2.backend_code, 1)
            self.assertEqual(self.port2.backend_status, "succeeded")

            switchport_save.assert_not_called()

    def test_process_event_nolabels(self):
        with patch.object(FabricService.objects, "get_items") as fabric_service_objects, \
                patch.object(Service.objects, "get_items") as service_objects, \
                patch.object(Switch.objects, "get_items") as switch_objects, \
                patch.object(Switch, "save") as switch_save, \
                patch.object(SwitchPort, "save") as switchport_save:
            fabric_service_objects.return_value = [self.fabric_service]
            service_objects.return_value = [self.onos, self.fabric_service]
            switch_objects.return_value = [self.switch]

            event_dict = {"status": "created"}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.switch.backend_code, 1)
            self.assertEqual(self.switch.backend_status, "succeeded")

            switch_save.assert_not_called()

            self.assertEqual(self.port1.backend_code, 1)
            self.assertEqual(self.port1.backend_status, "succeeded")

            self.assertEqual(self.port2.backend_code, 1)
            self.assertEqual(self.port2.backend_status, "succeeded")

            switchport_save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
