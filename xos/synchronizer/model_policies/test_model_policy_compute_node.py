
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
import ipaddress
from mock import patch, call, Mock, PropertyMock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestComputeNodePolicy(unittest.TestCase):
    def setUp(self):
        global ComputeNodePolicy, MockObjectList

        self.sys_path_save = sys.path

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("fabric", "fabric.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from model_policy_compute_nodes import ComputeNodePolicy, model_accessor

        self.model_accessor = model_accessor

        from mock_modelaccessor import MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = ComputeNodePolicy
        self.model = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_getLastAddress(self):

        dataPlaneIp = unicode("10.6.1.2/24", "utf-8")
        interface = ipaddress.ip_interface(dataPlaneIp)
        subnet = ipaddress.ip_network(interface.network)
        last_ip = self.policy.getLastAddress(subnet)
        self.assertEqual(str(last_ip), "10.6.1.254/24")

    def test_generateVlan(self):

        used_vlans = range(16, 4093)
        used_vlans.remove(1000)

        vlan = self.policy.generateVlan(used_vlans)

        self.assertEqual(vlan, 1000)

    def test_generateVlanFail(self):

        used_vlans = range(16, 4093)

        with self.assertRaises(Exception) as e:
            self.policy.generateVlan(used_vlans)

        self.assertEqual(e.exception.message, "No VLANs left")

    def test_getVlanByCidr_same_subnet(self):

        mock_pi_ip = unicode("10.6.1.2/24", "utf-8")
        
        mock_pi = Mock()
        mock_pi.vlanUntagged = 1234
        mock_pi.ips = str(self.policy.getPortCidrByIp(mock_pi_ip))

        test_ip = unicode("10.6.1.1/24", "utf-8")
        test_subnet = self.policy.getPortCidrByIp(test_ip)

        with patch.object(PortInterface.objects, "get_items") as get_pi:
            get_pi.return_value = [mock_pi]
            vlan = self.policy.getVlanByCidr(test_subnet)

            self.assertEqual(vlan, mock_pi.vlanUntagged)

    def test_getVlanByCidr_different_subnet(self):

        mock_pi_ip = unicode("10.6.1.2/24", "utf-8")
        mock_pi = Mock()
        mock_pi.vlanUntagged = 1234
        mock_pi.ips = str(self.policy.getPortCidrByIp(mock_pi_ip))

        test_ip = unicode("192.168.1.1/24", "utf-8")
        test_subnet = self.policy.getPortCidrByIp(test_ip)

        with patch.object(PortInterface.objects, "get_items") as get_pi:

            get_pi.return_value = [mock_pi]
            vlan = self.policy.getVlanByCidr(test_subnet)

            self.assertNotEqual(vlan, mock_pi.vlanUntagged)

    def test_handle_create(self):

        policy = self.policy(model_accessor=self.model_accessor)
        with patch.object(policy, "handle_update") as handle_update:
            policy.handle_create(self.model)
            handle_update.assert_called_with(self.model)

    def test_handle_update_do_nothing(self):

        mock_pi_ip = unicode("10.6.1.2/24", "utf-8")
        mock_pi = Mock()
        mock_pi.port_id = 1
        mock_pi.name = "test_interface"
        mock_pi.ips = str(self.policy.getPortCidrByIp(mock_pi_ip))

        policy = self.policy(model_accessor=self.model_accessor)

        self.model.port.id = 1
        self.model.node.dataPlaneIntf = "test_interface"

        with patch.object(PortInterface.objects, "get_items") as get_pi, \
            patch.object(self.policy, "getPortCidrByIp") as get_subnet, \
            patch.object(PortInterface, 'save') as mock_save:

            get_pi.return_value = [mock_pi]
            get_subnet.return_value = mock_pi.ips

            policy.handle_update(self.model)

            mock_save.assert_not_called()

    def test_handle_update(self):

        policy = self.policy(model_accessor=self.model_accessor)

        self.model.port.id = 1
        self.model.node.dataPlaneIntf = "test_interface"
        self.model.node.dataPlaneIp = unicode("10.6.1.2/24", "utf-8")

        with patch.object(PortInterface.objects, "get_items") as get_pi, \
            patch.object(self.policy, "getVlanByCidr") as get_vlan, \
            patch.object(PortInterface, "save", autospec=True) as mock_save:

            get_pi.return_value = []
            get_vlan.return_value = "1234"

            policy.handle_update(self.model)

            self.assertEqual(mock_save.call_count, 1)
            pi = mock_save.call_args[0][0]

            self.assertEqual(pi.name, self.model.node.dataPlaneIntf)
            self.assertEqual(pi.port_id, self.model.port.id)
            self.assertEqual(pi.vlanUntagged, "1234")
            self.assertEqual(pi.ips, "10.6.1.254/24")


if __name__ == '__main__':
    sys.path.append("../steps")  # so we can import helpers from steps directory
    unittest.main()

