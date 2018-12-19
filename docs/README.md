# Fabric service

The Fabric service is responsible for configuring the fabric switches in ONOS.

At this point we assume you followed the
[Fabric setup](../fabric-setup.md) guide and your physical infrastructure
is configured and ready to go.

## Models

The fabric service is composed of the following models:

- `FabricService`. Global service-related parameters such as the name of the service
    - `autoconfig`. Determines whether the fabric is automatically configured.
- `Switch`. Represents a fabric switch.
    - `name`. Name of switch.
    - `ofId`. Openflow ID of switch.
    - `driver`. Driver used by the SDN controller, defaults to ofdpa3.
    - `ipv4NodeSid`. MPLS label used by the switch.
    - `ipv4Loopback`. Fabric loopback interface IP address.
    - `routerMac`. MAC address of the fabric switch used for all interfaces.
    - `isEdgeRouter`. True if the switch is a leaf, false if it is a spine.
- `SwitchPort`. Represents a port on a fabric `Switch`.
    - `switch`. Relation to `Switch` that owns this port.
    - `portId`. Unique OpenFlow port ID.
    - `host_learning`. True to enable autodiscovery.
- `PortInterface`. Represents an interface on a `Port`.
    - `port`. Relation to the `SwitchPort` that owns this interface.
    - `name`. The unique name of the fabric switch port.
    - `vlanUntagged`. Optional untagged VLAN ID for the interface.
- `NodeToSwitchPort`. Connects a `SwitchPort` to a `Node`.
    - `port`. `SwitchPort` that will be connected.
    - `node`. `Node` that will be connected.
- `FabricIpAddress`. Specifies an IP address attached to a `PortInterface`.
    - `interface`. `PortInterface` that this IP address belongs to.
    - `ip`. IP Address.
    - `description`. A short description of this IP address.

## Example TOSCA - Configuring Switches and Ports

Here is an example of how to configure a `Switch` and `Ports` for OLT and BNG
on your fabric. This particular configuration is used in Seba-in-a-Box with an OpenVSwitch software switch, but it should be straightforward to adapt this example to a physical switch.

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/switch.yaml
  - custom_types/switchport.yaml

description: Configures the Ponsim SEBA POD with AT&T workflow

topology_template:
  node_templates:
    # Fabric configuration
    switch#leaf_1:
      type: tosca.nodes.Switch
      properties:
        driver: ofdpa-ovs # The driver used by the SDN controller
        ipv4Loopback: 192.168.0.201 # Fabric loopback interface
        ipv4NodeSid: 17 # The MPLS label used by the switch [17 - 1048576]
        isEdgeRouter: True # Whether is a leaf (True) or a spine (False)
        name: leaf_1
        ofId: of:0000000000000001 # The unique OpenFlow ID of the fabric switch
        routerMac: 00:00:02:01:06:01 # MAC address of the fabric switch used for all interfaces

    # Setup the OLT switch port
    port#olt_port:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 2 # The unique port OpenFlow port ID
        host_learning: false # True to enable autodiscovery
      requirements:
        - switch:
            node: switch#leaf_1
            relationship: tosca.relationships.BelongsToOne

    # Port connected to the BNG
    port#bng_port:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 1
      requirements:
        - switch:
            node: switch#leaf_1
            relationship: tosca.relationships.BelongsToOne
```

## Example TOSCA - Attaching Compute Nodes

> Note: This section is primarily for OpenStack-based compute nodes. It is not necessarily relevant to Kubernetes-based compute nodes at this time.

Compute nodes may be attached to the fabric in order to attach compute-based VNFs to the data plane. The following section assumes the fabric switches have already been setup. The example uses the following nodes: 

- `node1.cord.lab` has ip `10.6.1.17` on interface `fabricbridge` and it is attached to port `17` on the switch `leaf1` (and has a route like `10.6.2.0/24 via 10.6.1.254 dev fabricbridge` or the default route is pointing to the fabric)
- `node2.cord.lab` has ip `10.6.2.18` on interface `fabricbridge` and it is attached to port `18` on the switch `leaf1` (and has a route like `10.6.1.0/24 via 10.6.2.254 dev fabricbridge` or the default route is pointing to the fabric)

you can use the following TOSCA recipe to:

- add the Nodes to XOS
- add the two Ports to the Switch
- associate each Node to a Port

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
description: Set up Fabric service and attach it to ONOS (note that onos-service needs to be loaded)
imports:
  - custom_types/node.yaml
  - custom_types/nodetoswitchport.yaml
  - custom_types/switch.yaml
  - custom_types/switchport.yaml
  - custom_types/deployment.yaml
  - custom_types/site.yaml
  - custom_types/sitedeployment.yaml

topology_template:
  node_templates:

    # nodes
    node#node1:
        type: tosca.nodes.Node
        properties:
            dataPlaneIntf: fabricbridge
            dataPlaneIp: 10.6.1.17/24
            name: node1.cord.lab
        requirements:
            - site_deployment:
                node: site_deployment
                relationship: tosca.relationships.BelongsToOne
    
    node#node2:
        type: tosca.nodes.Node
        properties:
            dataPlaneIntf: fabricbridge
            dataPlaneIp: 10.6.2.18/24
            name: node2.cord.lab
        requirements:
            - site_deployment:
                node: site_deployment
                relationship: tosca.relationships.BelongsToOne

    # ports (defined in the above recipe)
    switch#leaf1:
      type: tosca.nodes.Switch
      properties:
        name: leaf1
        must-exist: true
    
    port#port17:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 17
      requirements:
        - switch:
            node: switch#leaf1
            relationship: tosca.relationships.BelongsToOne
    
    port#port18:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 18
      requirements:
        - switch:
            node: switch#leaf1
            relationship: tosca.relationships.BelongsToOne

    # attaching nodes to ports
    node1_to_port17:
        type: tosca.nodes.NodeToSwitchPort
        requirements:
            - port:
                node: port#port17
                relationship: tosca.relationships.BelongsToOne
            - node:
                node: node#node1
                relationship: tosca.relationships.BelongsToOne
    
    node2_to_port18:
        type: tosca.nodes.NodeToSwitchPort
        requirements:
            - port:
                node: port#port18
                relationship: tosca.relationships.BelongsToOne
            - node:
                node: node#node2
                relationship: tosca.relationships.BelongsToOne

    # extra setup required by XOS (note that this needs to be customized to your installation)
    mySite:
      type: tosca.nodes.Site
      properties:
          name: mySite
          login_base: opencord
          abbreviated_name: ms
          site_url: http://opencord.org/
          hosts_nodes: true

    myDeployment:
      type: tosca.nodes.Deployment
      properties:
        name: myDeployment

    site_deployment:
      type: tosca.nodes.SiteDeployment
      requirements:
        - site:
            node: mySite
            relationship: tosca.relationships.BelongsToOne
        - deployment:
            node: myDeployment
            relationship: tosca.relationships.BelongsToOne
```

This will cause the correct fabric configuration to be generated and pushed to the fabric.

## Integration with other Services

The Fabric Service is an infrastructure service that supports other services, and does not provide `ServiceInstances` of its own. The Fabric Service depends upon the ONOS Service, as Fabric is implemented as an ONOS Application.

## Synchronization workflow

### Switch, SwitchPort

When `Switch` or `SwitchPort` are created, modified, or deleted, the appropriate REST API calls are performed to ONOS using the `/onos/v1/network/configuration/` endpoint.

### Event Steps

If an event is received that indicates ONOS has been restarted, then all `Switch` and `SwitchPort` objects will be dirtied, causing the state to be resynchronized to ONOS.

