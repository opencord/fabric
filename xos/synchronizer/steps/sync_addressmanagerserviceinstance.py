
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


import os
import base64
from collections import defaultdict
from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import *
from xos.logger import observer_logger as logger
import json

class SyncAddressManagerServiceInstance(SyncStep):
    provides=[AddressManagerServiceInstance]
    observes = AddressManagerServiceInstance
    requested_interval=30
    playbook='sync_host.yaml'

    def get_fabric_onos_service(self):
        # There will be a ServiceInstanceLink from the FabricService to the Fabric ONOS App
        fs = FabricService.objects.first()
        for link in fs.subscribed_links.all():
            if link.provider_service_instance:
                # cast from ServiceInstance to ONOSApp
                service_instance = link.provider_service_instance.leaf_model
                # cast from Service to ONOSService
                return service_instance.owner.leaf_model

        return None

    def get_node_tag(self, node, tagname):
        tags = Tag.objects.filter(content_type=model_accessor.get_content_type_id(node),
                                  object_id=node.id,
                                  name=tagname)
        if tags:
            return tags[0].value
        else:
            return None

    def fetch_pending(self, deleted):
        # If fetch_pending is being called for delete, then just execute the standard delete logic.
        if deleted:
            return super(SyncAddressManagerServiceInstance, self).fetch_pending(deleted)

        fs = FabricService.objects.first()
        if (not fs) or (not fs.autoconfig):
            return None

        # TODO: Why is this a nonstandard synchronizer query?
        objs = AddressManagerServiceInstance.objects.all()

        objs = list(objs)

        # Check that each is a valid VSG tenant or instance
        for address_si in objs:
            sub = self.get_subscriber(address_si)
            if sub:
                if not sub.instance:
                    objs.remove(address_si)
            else:
                # Maybe the Address is for an instance
                # TODO: tenant_for_instance_id needs to be a real database field
                instance_id = address_si.get_attribute("tenant_for_instance_id")
                if not instance_id:
                    objs.remove(address_si)
                else:
                    instance = Instance.objects.filter(id=instance_id)[0]
                    if not instance.instance_name:
                        objs.remove(address_si)

        return objs

    def get_subscriber(self, address_si):
        links = address_si.provided_links.all()
        for link in links:
            if not link.subscriber_service_instance:
                continue
            # cast from ServiceInstance to VSGTEnant or similar
            sub = link.subscriber_service_instance.leaf_model
            # TODO: check here to make sure it's an appropriate type of ServiceInstance ?
            return sub
        return None

    def map_sync_inputs(self, address_si):

        fos = self.get_fabric_onos_service()

        if not fos:
            raise Exception("No fabric onos service")

        name = None
        instance = None
        # Address setup is kind of hacky right now, we'll
        # need to revisit.  The idea is:
        # * Look up the instance corresponding to the address
        # * Look up the node running the instance
        # * Get the "location" tag, push to the fabric

        sub = self.get_subscriber(address_si)
        if sub:
            instance = sub.instance
            name = str(sub)
        else:
            instance_id = address_si.get_attribute("tenant_for_instance_id")
            instance = Instance.objects.filter(id=instance_id)[0]
            name = str(instance)

        node = instance.node
        location = self.get_node_tag(node, "location")

        if not location:
            raise DeferredException("No location tag for node %s tenant %s -- skipping" % (str(node), str(address_si)))

        # Create JSON
        data = {
            "%s/-1" % address_si.public_mac : {
                "basic" : {
                    "ips" : [ address_si.public_ip ],
                    "location" : location
                }
            }
        }
        # Stupid Ansible... leading space so it doesn't think it's a dict
        rest_body = " " + json.dumps(data)

        # Is it a POST or DELETE?

        fields = {
            'rest_hostname': fos.rest_hostname,
            'rest_port': fos.rest_port,
            'rest_endpoint': "onos/v1/network/configuration/hosts",
            'rest_body': rest_body,
            'ansible_tag': '%s'%name, # name of ansible playbook
        }
        return fields

    def map_sync_outputs(self, controller_image, res):
        pass
