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
import urllib
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock
import multistructlog
from multistructlog import create_logger

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def match_json(desired, req):
    if desired!=req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
        return False
    return True

class TestSyncFabricPort(unittest.TestCase):

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
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from sync_fabric_port import SyncFabricPort

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncFabricPort
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

    def tearDown(self):
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_sync_port(self, m):
        # IPs
        ip1 = Mock()
        ip1.ip = "1.1.1.1/16"
        ip1.description = "My IPv4 ip"
        ip2 = Mock()
        ip2.ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64"
        ip2.description = "My IPv6 ip"
        ip3 = Mock()
        ip3.ip = "2.2.2.2/8"
        ip3.description = "My other IPv4 ip"

        intf1 = Mock()
        intf1.name = "intf1"
        intf1.vlanUntagged = None
        intf1.ips.all.return_value = [ip1, ip2]
        intf2 = Mock()
        intf2.name = "intf2"
        intf2.vlanUntagged = 42
        intf2.ips.all.return_value = [ip3]

        port = Mock()
        port.id = 1
        port.tologdict.return_value = {}
        port.host_learning = True
        port.interfaces.all.return_value = [intf1, intf2]
        port.switch.ofId = "of:1234"
        port.portId = "1"

        expected_conf = {
            "ports": {
                "%s/%s" % (port.switch.ofId, port.portId): {
                    "interfaces": [
                        {
                            "name": intf1.name,
                            "ips": [ ip1.ip, ip2.ip ]
                        },
                        {
                            "name": intf2.name,
                            "ips": [ip3.ip],
                            "vlan-untagged": intf2.vlanUntagged
                        }
                    ],
                    "hostLearning": {
                        "enabled": port.host_learning
                    }
                }
            }
        }

        m.post("http://onos-fabric:8181/onos/v1/network/configuration/",
               status_code=200,
               additional_matcher=functools.partial(match_json, expected_conf))

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric
            self.sync_step(model_accessor=self.model_accessor).sync_record(port)
            self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_delete_port(self, m):
        # create a mock SwitchPort instance
        port = Mock()
        port.id = 1
        port.tologdict.return_value = {}
        port.host_learning = True
        port.switch.ofId = "of:1234"
        port.portId = "1"

        key = urllib.quote("of:1234/1", safe='')
        m.delete("http://onos-fabric:8181/onos/v1/network/configuration/ports/%s" % key,
            status_code=204)

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric
            self.sync_step(model_accessor=self.model_accessor).delete_record(port)
            self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_delete_interface(self, m):
        ip1 = Mock()
        ip1.ip = "1.1.1.1/16"
        ip1.description = "My IPv4 ip"
        ip2 = Mock()
        ip2.ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64"
        ip2.description = "My IPv6 ip"

        # interfaces
        intf1 = Mock()
        intf1.name = "intf1"
        intf1.vlanUntagged = None
        intf1.ips.all.return_value = [ip1, ip2]

        # bindings
        # create a mock SwitchPort instance
        interface_to_remove = Mock()
        interface_to_remove.id = 1
        interface_to_remove.tologdict.return_value = {}
        interface_to_remove.leaf_model_name = "PortInterface"
        interface_to_remove.port.interfaces.all.return_value = [intf1]
        interface_to_remove.port.switch.ofId = "of:1234"
        interface_to_remove.port.portId = "1"
        interface_to_remove.port.host_learning = True

        m.post("http://onos-fabric:8181/onos/v1/network/configuration/", status_code=200)

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric
            self.sync_step(model_accessor=self.model_accessor).delete_record(interface_to_remove)
            self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_delete_ip(self, m):
        ip1 = Mock()
        ip1.ip = "1.1.1.1/16"
        ip1.description = "My IPv4 ip"

        intf1 = Mock()
        intf1.name = "intf1"
        intf1.vlanUntagged = None
        intf1.ips.all.return_value = [ip1]

        ip_to_remove = Mock()
        ip_to_remove.id = 1
        ip_to_remove.leaf_model_name = "FabricIpAddress"
        ip_to_remove.interface.port.interfaces.all.return_value = [intf1] 
        ip_to_remove.interface.port.switch.ofId = "of:1234"
        ip_to_remove.interface.port.portId = "1"
        ip_to_remove.interface.port.host_learning = True

        m.post("http://onos-fabric:8181/onos/v1/network/configuration/", status_code=200)

        with patch.object(Service.objects, "get") as onos_fabric_get:
            onos_fabric_get.return_value = self.fabric
            self.sync_step(model_accessor=self.model_accessor).delete_record(ip_to_remove)
            self.assertTrue(m.called)

if __name__ == '__main__':
    unittest.main()
