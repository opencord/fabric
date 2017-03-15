import os
import base64
from collections import defaultdict
from xos.config import Config
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
        fos = None
        fs = FabricService.objects.first()
        if fs.subscribed_tenants.exists():
            app = fs.subscribed_tenants.first()
            if app.provider_service:
                ps = app.provider_service
                fos = ONOSService.objects.filter(id=ps.id)[0]
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
        fs = FabricService.objects.first()
        if (not fs) or (not fs.autoconfig):
            return None

        # TODO: Why is this a nonstandard synchronizer query?

        if (not deleted):
            objs = VRouterTenant.objects.all()
        else:
            objs = super(SyncVRouterTenant, self).fetch_pending(deleted)

        objs = list(objs)

        # Check that each is a valid vCPE tenant or instance
        for vroutertenant in objs:
            # Do we have a vCPE subscriber_tenant?
            if vroutertenant.subscriber_tenant:
                sub = vroutertenant.subscriber_tenant
                if sub.kind != 'vCPE':
                    objs.remove(vroutertenant)
                else:
                    # coerce the subscriber tenant over to the VSGTenant
                    vsg = VSGTenant.objects.filter(id=sub.id).first()
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

    def map_sync_inputs(self, vroutertenant):

        fos = self.get_fabric_onos_service()

        name = None
        instance = None
        # VRouterTenant setup is kind of hacky right now, we'll
        # need to revisit.  The idea is:
        # * Look up the instance corresponding to the address
        # * Look up the node running the instance
        # * Get the "location" tag, push to the fabric
        if vroutertenant.subscriber_tenant:
            sub = vroutertenant.subscriber_tenant
            assert(sub.kind == 'vCPE')
            vsg = VSGTenant.objects.filter(id=sub.id).first()
            instance = vsg.instance
            name = str(sub)
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
