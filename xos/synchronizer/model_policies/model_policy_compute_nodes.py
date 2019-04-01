
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

import ipaddress
import random
from xossynchronizer.modelaccessor import NodeToSwitchPort, PortInterface, model_accessor
from xossynchronizer.model_policies.policy import Policy

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))


class ComputeNodePolicy(Policy):
    model_name = "NodeToSwitchPort"

    @staticmethod
    def getLastAddress(network):
        return str(network.network_address + network.num_addresses - 2) + "/" + str(network.prefixlen)
        # return ipaddress.ip_interface(network.network_address + network.num_addresses - 2)

    @staticmethod
    def getPortCidrByIp(ip):
        interface = ipaddress.ip_interface(ip)
        network = ipaddress.ip_network(interface.network)
        cidr = ComputeNodePolicy.getLastAddress(network)
        return cidr

    @staticmethod
    def generateVlan(used_vlans):
        availabel_tags = list(range(16, 4093))
        valid_tags = list(set(availabel_tags) - set(used_vlans))
        if len(valid_tags) == 0:
            raise Exception("No VLANs left")
        return random.choice(valid_tags)

    @staticmethod
    def getVlanByCidr(subnet):
        # vlanUntagged is unique per subnet
        same_subnet_ifaces = PortInterface.objects.filter(ips=str(subnet))

        if len(same_subnet_ifaces) > 0:
            return same_subnet_ifaces[0].vlanUntagged
        else:
            PortInterface.objects.all()
            used_vlans = list(set([i.vlanUntagged for i in same_subnet_ifaces]))
            log.info("MODEL_POLICY: used vlans", vlans=used_vlans, subnet=subnet)
            return ComputeNodePolicy.generateVlan(used_vlans)

    def handle_create(self, node_to_port):
        return self.handle_update(node_to_port)

    def handle_update(self, node_to_port):
        log.info(
            "MODEL_POLICY: NodeToSwitchPort %s handle update" %
            node_to_port.id,
            node=node_to_port.node,
            port=node_to_port.port,
            switch=node_to_port.port.switch)

        compute_node = node_to_port.node

        cidr = ComputeNodePolicy.getPortCidrByIp(compute_node.dataPlaneIp)

        # check if an interface already exists
        try:
            PortInterface.objects.get(
                port_id=node_to_port.port.id,
                name=compute_node.dataPlaneIntf,
                ips=str(cidr)
            )
        except IndexError:

            vlan = self.getVlanByCidr(cidr)

            log.info("MODEL_POLICY: choosen vlan", vlan=vlan, cidr=cidr)

            interface = PortInterface(
                port_id=node_to_port.port.id,
                name=compute_node.dataPlaneIntf,
                ips=str(cidr),
                vlanUntagged=vlan
            )

            interface.save()

        # TODO if the model is updated I need to remove the old interface, how?

    def handle_delete(self, node_to_port):
        pass
