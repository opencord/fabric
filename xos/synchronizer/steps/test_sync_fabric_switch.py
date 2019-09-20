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
import functools
from mock import patch, Mock
import requests_mock

import os
import sys

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


def match_json(desired, req):
    if desired != req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
        return False
    return True


class TestSyncFabricSwitch(unittest.TestCase):

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
        mock_modelaccessor_config(test_path, [("fabric", "fabric.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        imp.reload(mock_modelaccessor)  # in case nose2 loaded it in a previous test
        imp.reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from sync_fabric_switch import SyncFabricSwitch

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncFabricSwitch
        self.sync_step.log = Mock()

        # mock onos-fabric
        onos_fabric = Mock()
        onos_fabric.name = "onos-fabric"
        onos_fabric.rest_hostname = "onos-fabric"
        onos_fabric.rest_port = "8181"
        onos_fabric.rest_username = "onos"
        onos_fabric.rest_password = "rocks"

        onos_fabric_base = Mock()
        onos_fabric_base.leaf_model = onos_fabric

        self.fabric = Mock()
        self.fabric.name = "fabric"
        self.fabric.provider_services = [onos_fabric_base]

        # create a mock Switch instance
        self.o = Mock()
        self.o.name = "MockSwitch"
        self.o.ofId = "of:1234"

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_sync_switch(self, m):

        self.o.ofId = "of:1234"
        self.o.portId = "1"
        self.o.driver = "ofdpa3"
        self.o.ipv4NodeSid = "17"
        self.o.ipv4Loopback = "192.168.0.201"
        self.o.routerMac = "00:00:02:01:06:01"
        self.o.isEdgeRouter = False
        self.o.pipeconf = "pipeconf"
        self.o.managementAddress = "192.168.100.123"

        expected_conf = {
            "devices": {
                self.o.ofId: {
                    "basic": {
                        "name": self.o.name,
                        "driver": self.o.driver,
                        "pipeconf": self.o.pipeconf,
                        "managementAddress": self.o.managementAddress
                    },
                    "segmentrouting": {
                        "name": self.o.name,
                        "ipv4NodeSid": self.o.ipv4NodeSid,
                        "ipv4Loopback": self.o.ipv4Loopback,
                        "routerMac": self.o.routerMac,
                        "isEdgeRouter": self.o.isEdgeRouter,
                        "adjacencySids": []
                    }
                }
            }
        }

        m.post("http://onos-fabric:8181/onos/v1/network/configuration/",
               status_code=200,
               additional_matcher=functools.partial(match_json, expected_conf))

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

            self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_delete_switch(self, m):
        m.delete("http://onos-fabric:8181/onos/v1/network/configuration/devices/of:1234",
                 status_code=204)

        self.o.ofId = "of:1234"

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric

            self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

            self.assertTrue(m.called)


if __name__ == '__main__':
    unittest.main()
