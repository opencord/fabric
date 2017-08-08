
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

class SyncVRouterTenant(SyncStep):
    provides=[VRouterTenant]
    observes = VRouterTenant
    requested_interval=30
    playbook='sync_host.yaml'

    def get_fabric_onos_service(self):
        fs = FabricService.objects.first()
        for link in fs.subscribed_links.all():
            if link.provider_service_instance:
                # cast from ServiceInstance to ONOSApp
                apps = ONOSApp.objects.filter(id=link.provider_service_instance.id)
                if apps:
                    # cast from Service to ONOSService
                    onos = ONOSService.objects.get(id=apps[0].owner.id)
                    return onos
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
            return super(SyncVRouterTenant, self).fetch_pending(deleted)

        fs = FabricService.objects.first()
        if (not fs) or (not fs.autoconfig):
            return None

        # TODO: Why is this a nonstandard synchronizer query?
        objs = VRouterTenant.objects.all()

        objs = list(objs)

        # Check that each is a valid vCPE tenant or instance
        for vroutertenant in objs:
            # TODO: hardcoded service dependency
            vsg = self.get_vsg_subscriber(vroutertenant)
            if vsg:
                if not vsg.instance:
                    objs.remove(vroutertenant)
            else:
                # Maybe the VRouterTenant is for an instance
                # TODO: tenant_for_instance_id needs to be a real database field
                instance_id = vroutertenant.get_attribute("tenant_for_instance_id")
                if not instance_id:
                    objs.remove(vroutertenant)
                else:
                    instance = Instance.objects.filter(id=instance_id)[0]
                    if not instance.instance_name:
                        objs.remove(vroutertenant)

        return objs

    def get_vsg_subscriber(self, vroutertenant):
        links = vroutertenant.provided_links.all()
        for link in links:
            if not link.subscriber_service_instance:
                continue
            # cast from ServiceInstance to VSGTEnant
            vsgs = VSGTenant.objects.filter(id=link.subscriber_service_instance.id)
            if vsgs:
                return vsgs[0]
        return None

    def map_sync_inputs(self, vroutertenant):

        fos = self.get_fabric_onos_service()

        if not fos:
            raise Exception("No fabric onos service")

        name = None
        instance = None
        # VRouterTenant setup is kind of hacky right now, we'll
        # need to revisit.  The idea is:
        # * Look up the instance corresponding to the address
        # * Look up the node running the instance
        # * Get the "location" tag, push to the fabric

        # TODO: hardcoded service dependency
        vsg = self.get_vsg_subscriber(vroutertenant)
        if vsg:
            instance = vsg.instance
            name = str(vsg)
        else:
            instance_id = vroutertenant.get_attribute("tenant_for_instance_id")
            instance = Instance.objects.filter(id=instance_id)[0]
            name = str(instance)

        node = instance.node
        location = self.get_node_tag(node, "location")

        if not location:
            raise DeferredException("No location tag for node %s tenant %s -- skipping" % (str(node), str(vroutertenant)))

        # Create JSON
        data = {
            "%s/-1" % vroutertenant.public_mac : {
                "basic" : {
                    "ips" : [ vroutertenant.public_ip ],
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
