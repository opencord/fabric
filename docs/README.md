# Fabric service

The Fabric service is responsible to correctly configure the fabric switches in
ONOS.

At this point we assume you followed the
[Fabric seutp](../prereqs/fabric-setup.md) guide and your physical infrastructure
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
        driver: ofdpa3
        ipv4Loopback: 192.168.0.201
        ipv4NodeSid: 17
        isEdgeRouter: True
        name: leaf1
        ofId: of:0000000000000001
        routerMac: 00:00:02:01:06:01
        

    # Setup a fabric switch port
    port#port1:
      type: tosca.nodes.SwitchPort
      properties:
        portId: 1
      requirements:
        - switch:
            node: switch#leaf1
            relationship: tosca.relationships.BelongsToOne

    # Setup a fabric switch port interface
    interface#interface1:
      type: tosca.nodes.PortInterface
      properties:
        ips: 192.168.0.254/24
        name: port1
      requirements:
        - port:
            node: port#port1
            relationship: tosca.relationships.BelongsToOne
```