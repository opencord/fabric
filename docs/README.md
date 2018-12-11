# Fabric service

The Fabric service is responsible to configure the fabric switches in ONOS.

At this point we assume you followed the
[Fabric setup](../fabric-setup.md) guide and your physical infrastructure
is configured and ready to go.

## How to configure fabric switches

Here is an example of how to configure a `Switch` a `Port` and an `Interface`
on your fabric.

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/switch.yaml
  - custom_types/switchport.yaml
  - custom_types/portinterface.yaml
description: Configures fabric switches and related ports
topology_template:
  node_templates:
    switch#leaf1:
      type: tosca.nodes.Switch
      properties:
        driver: ofdpa3 # The driver used by the SDN controller
        ipv4Loopback: 192.168.0.201 # Fabric loopback interface
        ipv4NodeSid: 17 # The MPLS label used by the switch [17 - 1048576]
        isEdgeRouter: True # Whether is a leaf (True) or a spine (False)
        name: leaf1
        ofId: of:0000000000000001 # The unique OpenFlow ID of the fabric switch
        routerMac: 00:00:02:01:06:01 # MAC address of the fabric switch used for all interfaces

    # Setup a fabric switch port
    port#port1:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 1 # The unique port OpenFlow port ID
      requirements:
        - switch:
            node: switch#leaf1
            relationship: tosca.relationships.BelongsToOne

    # Setup a fabric switch port interface
    interface#interface1:
      type: tosca.nodes.PortInterface
      properties:
        ips: 192.168.0.254/24 # The interface IP address (xxx.yyy.www.zzz/nm)
        name: port1
      requirements:
        - port:
            node: port#port1
            relationship: tosca.relationships.BelongsToOne
```

## How to attach Compute Nodes to the Fabric

Assuming that you have the above mentioned fabric configuration
and you want to attach a two compute nodes to the fabric,
assuming that that:

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
