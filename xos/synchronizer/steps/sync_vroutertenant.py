
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

import requests
from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import *
from xos.logger import Logger, logging

logger = Logger(level=logging.INFO)

DATAPLANE_IP = "dataPlaneIp"
PREFIX = "prefix"
NEXT_HOP = "nextHop"

class SyncVRouterTenant(SyncStep):
    provides=[VRouterTenant]
    observes = VRouterTenant
    requested_interval=30

    def get_fabric_onos_service_internal(self):
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

    def get_fabric_onos_service(self):
        fos = self.get_fabric_onos_service_internal()
        if not fos:
            raise Exception("Fabric ONOS service not found")
        return fos

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
            # cast from ServiceInstance to VSGTenant
            vsgs = VSGTenant.objects.filter(id=link.subscriber_service_instance.id)
            if vsgs:
                return vsgs[0]
        return None

    def get_routes_url(self, fos):
        url = 'http://%s:%s/onos/v1/routes' % (fos.rest_hostname, fos.rest_port)

        logger.info("url: %s" % url)
        return url

    def sync_record(self, vroutertenant):
        fos = self.get_fabric_onos_service()

        data = self.map_tenant_to_route(vroutertenant)

        r = self.post_route(fos, data)

        logger.info("status: %s" % r.status_code)
        logger.info('result: %s' % r.text)

    def delete_record(self, vroutertenant):
        pass
        # Disabled for now due to lack of feedback state field
        # self.delete_route(self.get_fabric_onos_service(),  self.map_tenant_to_route(vroutertenant))


    def map_tenant_to_route(self, vroutertenant):
        instance = None
        # VRouterTenant setup is kind of hacky right now, we'll
        # need to revisit.  The idea is:
        # * Look up the instance corresponding to the address
        # * Look up the node running the instance
        # * Get the "dataPlaneIp" tag, push to the fabric

        # TODO: hardcoded service dependency
        vsg = self.get_vsg_subscriber(vroutertenant)
        if vsg:
            instance = vsg.instance
        else:
            instance_id = vroutertenant.get_attribute("tenant_for_instance_id")
            instance = Instance.objects.filter(id=instance_id)[0]

        node = instance.node
        dataPlaneIp = self.get_node_tag(node, DATAPLANE_IP)

        if not dataPlaneIp:
            raise DeferredException("No IP found for node %s tenant %s -- skipping" % (str(node), str(vroutertenant)))

        data = {
            PREFIX : "%s/32" % vroutertenant.public_ip,
            NEXT_HOP : dataPlaneIp.split('/')[0]
        }

        return data

    def delete_route(self, fos, route):
        url = self.get_routes_url(fos)

        r = requests.delete(url, json=route, auth=(fos.rest_username, fos.rest_password))

        logger.info("status: %s" % r.status_code)
        logger.info('result: %s' % r.text)

        return r

    def post_route(self, fos, route):
        url = self.get_routes_url(fos)
        return requests.post(url, json=route, auth=(fos.rest_username, fos.rest_password))

