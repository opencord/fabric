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

import datetime
import imp
import unittest
import json
import time
from mock import patch, Mock, MagicMock, ANY

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

        # Mock the kafka producer
        self.mockxoskafka = MagicMock()
        modules = {
            'xoskafka': self.mockxoskafka,
            'xoskafka.XOSKafkaProducer': self.mockxoskafka.XOSKafkaProducer,
        }
        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

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

        # necessary to reset XOSKafkaProducer's call_count
        import onos_event
        reload(onos_event)

        from onos_event import OnosPortEventStep, XOSKafkaProducer
        self.XOSKafkaProducer = XOSKafkaProducer

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
                                kind="access",
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

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": self.switch.ofId,
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

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": self.switch.ofId,
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

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": "doesnotexist",
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

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": self.switch.ofId,
                          "portId": "doesnotexist",
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)

            step.process_event(event)

            # should not have changed
            self.assertEqual(self.port1.oper_status, None)

    def test_send_alarm(self):
        self.port2.oper_status = "disabled"
        value = {"timestamp":"2019-03-21T18:00:26.613Z",
                 "deviceId":"of:0000000000000001",
                 "portId":"2",
                 "enabled":False,
                 "speed":10000,
                 "type":"COPPER"}

        step = self.event_step(model_accessor=self.model_accessor, log=self.log)
        step.send_alarm(self.switch, self.port2, value)

        self.assertEqual(self.XOSKafkaProducer.produce.call_count, 1)
        topic = self.XOSKafkaProducer.produce.call_args[0][0]
        key = self.XOSKafkaProducer.produce.call_args[0][1]
        event = json.loads(self.XOSKafkaProducer.produce.call_args[0][2])

        self.assertEqual(topic, "xos.alarms.fabric-service")
        self.assertEqual(key, "of:0000000000000001:2")

        raised_ts = time.mktime(datetime.datetime.strptime(value["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

        self.maxDiff = None

        expected_alarm = {
                 u"category": u"SWITCH",
                 u"reported_ts": ANY,
                 u"raised_ts": raised_ts,
                 u"state": u"RAISED",
                 u"alarm_type_name": u"SWITCH.PORT_LOS",
                 u"severity": u"MAJOR",
                 u"resource_id": unicode(self.switch.ofId),
                 u"context": {u"portId": u"2", u"portKind": u"access",
                              u'switch.name': u'switch1'},
                 u"type": u"COMMUNICATION",
                 u"id": u"xos.fabricservice.%s.SWITCH_PORT_LOS" % self.switch.ofId,
                 u"description": u"xos.fabricservice.%s - SWITCH PORT LOS Alarm - SWITCH_PORT_LOS - RAISED" % self.switch.ofId}

        self.assertDictEqual(expected_alarm, event)

    def test_clear_alarm(self):
        self.port2.oper_status = "enabled"
        value = {"timestamp":"2019-03-21T18:00:26.613Z",
                 "deviceId":"of:0000000000000001",
                 "portId":"2",
                 "enabled":False,
                 "speed":10000,
                 "type":"COPPER"}

        step = self.event_step(model_accessor=self.model_accessor, log=self.log)
        step.send_alarm(self.switch, self.port2, value)

        self.assertEqual(self.XOSKafkaProducer.produce.call_count, 1)
        topic = self.XOSKafkaProducer.produce.call_args[0][0]
        key = self.XOSKafkaProducer.produce.call_args[0][1]
        event = json.loads(self.XOSKafkaProducer.produce.call_args[0][2])

        self.assertEqual(topic, "xos.alarms.fabric-service")
        self.assertEqual(key, "of:0000000000000001:2")

        raised_ts = time.mktime(datetime.datetime.strptime(value["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

        self.maxDiff = None

        expected_alarm = {
                 u"category": u"SWITCH",
                 u"reported_ts": ANY,
                 u"raised_ts": raised_ts,
                 u"state": u"CLEARED",
                 u"alarm_type_name": u"SWITCH.PORT_LOS",
                 u"severity": u"MAJOR",
                 u"resource_id": unicode(self.switch.ofId),
                 u"context": {u"portId": u"2", u"portKind": u"access",
                              u'switch.name': u'switch1'},
                 u"type": u"COMMUNICATION",
                 u"id": u"xos.fabricservice.%s.SWITCH_PORT_LOS" % self.switch.ofId,
                 u"description": u"xos.fabricservice.%s - SWITCH PORT LOS Alarm - SWITCH_PORT_LOS - CLEARED" % self.switch.ofId}

        self.assertDictEqual(expected_alarm, event)


if __name__ == '__main__':
    unittest.main()
