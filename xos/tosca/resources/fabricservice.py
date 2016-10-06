from service import XOSService
from services.fabric.models import FabricService

class FabricService(XOSService):
    provides = "tosca.nodes.FabricService"
    xos_model = FabricService
    copyin_props = ["view_url", "icon_url", "enabled", "published", "public_key", "versionNumber"]

