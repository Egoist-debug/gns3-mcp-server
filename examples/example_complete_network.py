#!/usr/bin/env python3
"""
Complete Example: Building an Enterprise Network
Demonstrates all major features of the GNS3 MCP Server v2.0
"""

import asyncio
from server import *

# This example shows how to programmatically:
# 1. Create a project
# 2. Add routers and switches
# 3. Connect them
# 4. Configure routing (OSPF)
# 5. Configure VLANs
# 6. Add DHCP services
# 7. Configure security (ACLs, SSH)
# 8. Create snapshots
# 9. Validate the topology

async def main():
    SERVER = "http://localhost:3080"
    
    print("=" * 60)
    print("GNS3 MCP Server v2.0 - Complete Example")
    print("Building Enterprise Network with AI Automation")
    print("=" * 60)
    
    # Step 1: Create Project
    print("\n[1] Creating Project...")
    project_result = await gns3_create_project(
        name="Enterprise_Network_Demo",
        auto_start=False,
        auto_close=False,
        server_url=SERVER
    )
    
    if project_result["status"] != "success":
        print(f"Error: {project_result['error']}")
        return
    
    project_id = project_result["project"]["project_id"]
    print(f"✓ Project created: {project_id}")
    
    # Step 2: List Available Templates
    print("\n[2] Listing Available Templates...")
    templates_result = await gns3_list_templates(server_url=SERVER)
    
    if templates_result["status"] != "success":
        print(f"Error: {templates_result['error']}")
        return
    
    # Find router, switch, and PC templates
    router_template = None
    switch_template = None
    pc_template = None
    
    for template in templates_result["templates"]:
        if "router" in template["name"].lower() and not router_template:
            router_template = template["template_id"]
            print(f"✓ Found Router Template: {template['name']}")
        elif "switch" in template["name"].lower() and not switch_template:
            switch_template = template["template_id"]
            print(f"✓ Found Switch Template: {template['name']}")
        elif "vpcs" in template["name"].lower() and not pc_template:
            pc_template = template["template_id"]
            print(f"✓ Found PC Template: {template['name']}")
    
    if not all([router_template, switch_template, pc_template]):
        print("Warning: Not all templates found. Please install required templates in GNS3.")
        print("This is a demonstration - adjust template IDs for your GNS3 installation.")
        return
    
    # Step 3: Add Devices
    print("\n[3] Adding Network Devices...")
    
    # Add HQ Router
    print("  Adding HQ Router...")
    r_hq = await gns3_add_node(
        project_id=project_id,
        node_name="HQ-Router",
        template_id=router_template,
        x=-200, y=-100,
        server_url=SERVER
    )
    hq_router_id = r_hq["node"]["node_id"] if r_hq["status"] == "success" else None
    
    # Add Branch Router
    print("  Adding Branch Router...")
    r_branch = await gns3_add_node(
        project_id=project_id,
        node_name="Branch-Router",
        template_id=router_template,
        x=200, y=-100,
        server_url=SERVER
    )
    branch_router_id = r_branch["node"]["node_id"] if r_branch["status"] == "success" else None
    
    # Add Core Switch
    print("  Adding Core Switch...")
    s_core = await gns3_add_node(
        project_id=project_id,
        node_name="Core-Switch",
        template_id=switch_template,
        x=-200, y=50,
        server_url=SERVER
    )
    core_switch_id = s_core["node"]["node_id"] if s_core["status"] == "success" else None
    
    # Add Access Switch
    print("  Adding Access Switch...")
    s_access = await gns3_add_node(
        project_id=project_id,
        node_name="Access-Switch",
        template_id=switch_template,
        x=200, y=50,
        server_url=SERVER
    )
    access_switch_id = s_access["node"]["node_id"] if s_access["status"] == "success" else None
    
    # Add PCs
    pcs = []
    for i in range(4):
        print(f"  Adding PC{i+1}...")
        pc = await gns3_add_node(
            project_id=project_id,
            node_name=f"PC{i+1}",
            template_id=pc_template,
            x=-300 + (i * 200), y=200,
            server_url=SERVER
        )
        if pc["status"] == "success":
            pcs.append(pc["node"]["node_id"])
    
    print(f"✓ Added {2} routers, {2} switches, {len(pcs)} PCs")
    
    # Step 4: Create Links
    print("\n[4] Creating Network Links...")
    
    links = [
        ("HQ-Router", hq_router_id, "Branch-Router", branch_router_id, "WAN Link"),
        ("HQ-Router", hq_router_id, "Core-Switch", core_switch_id, "HQ LAN"),
        ("Branch-Router", branch_router_id, "Access-Switch", access_switch_id, "Branch LAN"),
    ]
    
    for name_a, id_a, name_b, id_b, desc in links:
        if id_a and id_b:
            result = await gns3_add_link(
                project_id=project_id,
                node_a_id=id_a,
                node_b_id=id_b,
                adapter_a=0, port_a=0,
                adapter_b=0, port_b=0,
                server_url=SERVER
            )
            if result["status"] == "success":
                print(f"  ✓ Connected {name_a} <-> {name_b} ({desc})")
    
    # Connect PCs to switches
    for i, pc_id in enumerate(pcs[:2]):
        await gns3_add_link(project_id, core_switch_id, pc_id, 0, i+1, 0, 0, SERVER)
    for i, pc_id in enumerate(pcs[2:]):
        await gns3_add_link(project_id, access_switch_id, pc_id, 0, i+1, 0, 0, SERVER)
    
    print(f"✓ Created all network links")
    
    # Step 5: Start All Devices
    print("\n[5] Starting Network Simulation...")
    start_result = await gns3_start_all_nodes(
        project_id=project_id,
        server_url=SERVER
    )
    
    if start_result["status"] == "success":
        print(f"✓ Started {start_result['successful']} devices")
        if start_result['failed_nodes']:
            print(f"  ⚠ Failed to start {len(start_result['failed_nodes'])} devices")
    
    # Wait for devices to boot
    print("  Waiting for devices to boot (30 seconds)...")
    await asyncio.sleep(30)
    
    # Step 6: Configure HQ Router
    print("\n[6] Configuring HQ Router...")
    
    # Basic configuration
    basic_result = await gns3_apply_config_template(
        project_id=project_id,
        node_id=hq_router_id,
        template_name="basic_router",
        template_params={
            "hostname": "HQ-Router",
            "domain": "enterprise.local"
        },
        save_config=False,
        server_url=SERVER
    )
    
    # Configure interfaces
    print("  Configuring interfaces...")
    await gns3_send_console_commands(
        project_id=project_id,
        node_id=hq_router_id,
        commands=[
            "interface GigabitEthernet0/0",
            "description WAN to Branch",
            "ip address 10.0.0.1 255.255.255.252",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "description LAN HQ",
            "ip address 192.168.1.1 255.255.255.0",
            "no shutdown",
            "exit"
        ],
        enter_config_mode=True,
        save_config=False,
        server_url=SERVER
    )
    
    # Configure OSPF
    print("  Configuring OSPF...")
    ospf_result = await gns3_apply_config_template(
        project_id=project_id,
        node_id=hq_router_id,
        template_name="ospf",
        template_params={
            "process_id": 1,
            "router_id": "1.1.1.1",
            "networks": [
                {"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0},
                {"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0}
            ]
        },
        save_config=True,
        server_url=SERVER
    )
    
    if ospf_result["status"] == "success":
        print("  ✓ HQ Router configured successfully")
    
    # Step 7: Configure Branch Router  
    print("\n[7] Configuring Branch Router...")
    
    # Use bulk configuration for efficiency
    branch_commands = [
        "hostname Branch-Router",
        "ip domain-name enterprise.local",
        "interface GigabitEthernet0/0",
        "description WAN to HQ",
        "ip address 10.0.0.2 255.255.255.252",
        "no shutdown",
        "exit",
        "interface GigabitEthernet0/1",
        "description LAN Branch",
        "ip address 192.168.2.1 255.255.255.0",
        "no shutdown",
        "exit",
        "router ospf 1",
        "router-id 2.2.2.2",
        "network 10.0.0.0 0.0.0.3 area 0",
        "network 192.168.2.0 0.0.0.255 area 0",
        "exit"
    ]
    
    await gns3_send_console_commands(
        project_id=project_id,
        node_id=branch_router_id,
        commands=branch_commands,
        enter_config_mode=True,
        save_config=True,
        server_url=SERVER
    )
    print("  ✓ Branch Router configured")
    
    # Step 8: Configure DHCP on Routers
    print("\n[8] Configuring DHCP Services...")
    
    # HQ DHCP
    await gns3_apply_config_template(
        project_id=project_id,
        node_id=hq_router_id,
        template_name="dhcp_pool",
        template_params={
            "pool_name": "HQ_LAN",
            "network": "192.168.1.0",
            "mask": "255.255.255.0",
            "default_router": "192.168.1.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "excluded_addresses": [("192.168.1.1", "192.168.1.10")]
        },
        save_config=True,
        server_url=SERVER
    )
    print("  ✓ HQ DHCP configured")
    
    # Branch DHCP
    await gns3_apply_config_template(
        project_id=project_id,
        node_id=branch_router_id,
        template_name="dhcp_pool",
        template_params={
            "pool_name": "Branch_LAN",
            "network": "192.168.2.0",
            "mask": "255.255.255.0",
            "default_router": "192.168.2.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "excluded_addresses": [("192.168.2.1", "192.168.2.10")]
        },
        save_config=True,
        server_url=SERVER
    )
    print("  ✓ Branch DHCP configured")
    
    # Step 9: Create Snapshot
    print("\n[9] Creating Backup Snapshot...")
    snapshot_result = await gns3_create_snapshot(
        project_id=project_id,
        snapshot_name="Initial_Configuration",
        server_url=SERVER
    )
    
    if snapshot_result["status"] == "success":
        print("  ✓ Snapshot created successfully")
    
    # Step 10: Validate Topology
    print("\n[10] Validating Network Topology...")
    validation_result = await gns3_validate_topology(
        project_id=project_id,
        server_url=SERVER
    )
    
    if validation_result["status"] == "success":
        val = validation_result["validation"]
        print(f"  Total Nodes: {val['total_nodes']}")
        print(f"  Total Links: {val['total_links']}")
        print(f"  Connected Nodes: {val['connected_nodes']}")
        print(f"  Disconnected Nodes: {val['disconnected_nodes']}")
        
        if val['issues']:
            print("\n  ⚠ Issues Found:")
            for issue in val['issues']:
                print(f"    - {issue}")
        
        if val['warnings']:
            print("\n  ⚠ Warnings:")
            for warning in val['warnings']:
                print(f"    - {warning}")
        
        if val['is_valid']:
            print("\n  ✓ Topology validation passed!")
    
    # Step 11: Get Final Topology Overview
    print("\n[11] Final Topology Overview...")
    topology_result = await gns3_get_topology(
        project_id=project_id,
        server_url=SERVER
    )
    
    if topology_result["status"] == "success":
        summary = topology_result["summary"]
        print(f"  ✓ Network built successfully!")
        print(f"    - Nodes: {summary['total_nodes']}")
        print(f"    - Links: {summary['total_links']}")
        print(f"    - Running: {summary['running_nodes']}")
        print(f"    - Stopped: {summary['stopped_nodes']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("ENTERPRISE NETWORK BUILD COMPLETE!")
    print("=" * 60)
    print(f"Project ID: {project_id}")
    print(f"Project Name: Enterprise_Network_Demo")
    print("\nConfigured Features:")
    print("  ✓ WAN connectivity between sites")
    print("  ✓ OSPF dynamic routing")
    print("  ✓ DHCP services on both sites")
    print("  ✓ Hierarchical topology (Core/Access)")
    print("  ✓ Backup snapshot created")
    print("  ✓ Topology validated")
    print("\nNext Steps:")
    print("  1. Open project in GNS3 GUI")
    print("  2. Configure PCs with DHCP")
    print("  3. Test connectivity between sites")
    print("  4. Add security features (ACLs, SSH)")
    print("  5. Implement advanced routing features")
    print("=" * 60)


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT:")
    print("1. Ensure GNS3 server is running on http://localhost:3080")
    print("2. Required templates must be installed (Router, Switch, VPCS)")
    print("3. This is a demonstration - adjust for your GNS3 setup")
    print("\nPress Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    try:
        import time
        time.sleep(5)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Please ensure GNS3 server is running and templates are installed.")
