import asyncio
import sys
# Import classes from server.py
from server import GNS3APIClient, GNS3Config, TelnetClient

PROJECT_ID = "3b705e60-bf7a-42ca-a7c1-9b7f310f475c"
ROUTER_TPL = "25f27a32-288d-4d47-abe7-34a36e58ee36"
VPCS_TPL = "19021f99-e36f-394d-b4a1-8aaa902ab9cc"

async def main():
    print("--- Setup Client ---")
    config = GNS3Config()
    client = GNS3APIClient(config)
    
    print("--- 1. Adding Nodes ---")
    # R1
    try:
        r1 = await client.create_node_from_template(
            project_id=PROJECT_ID,
            template_id=ROUTER_TPL,
            compute_id="vm",
            name="R1",
            x=0, y=0
        )
        r1_id = r1["node_id"]
        print(f"R1 Added: {r1_id}")
    except Exception as e:
        print(f"Error adding R1: {e}")
        return

    # PC1
    try:
        pc1 = await client.create_node_from_template(
            project_id=PROJECT_ID,
            template_id=VPCS_TPL,
            compute_id="local",
            name="PC1",
            x=0, y=100
        )
        pc1_id = pc1["node_id"]
        print(f"PC1 Added: {pc1_id}")
    except Exception as e:
        print(f"Error adding PC1: {e}")
        return

    print("\n--- 2. Linking R1 -> PC1 ---")
    # Need to check if names work. I'll try adapters first as it's safer.
    # R1 (Gi0/0) -> PC1 (Ethernet0)
    # Gi0/0 is adapter 0 port 0.
    try:
        link_data = {
            "nodes": [
                {"node_id": r1_id, "adapter_number": 0, "port_number": 0},
                {"node_id": pc1_id, "adapter_number": 0, "port_number": 0}
            ]
        }
        await client.create_link(PROJECT_ID, link_data)
        print("Link created.")
    except Exception as e:
        print(f"Error linking: {e}")

    print("\n--- 3. Starting Simulation ---")
    nodes = await client.get_project_nodes(PROJECT_ID)
    for node in nodes:
        await client.start_node(PROJECT_ID, node["node_id"])
    print("Simulation started. Waiting 30s...")
    await asyncio.sleep(30)

    print("\n--- 4. Configure R1 via Console (using TelnetClient) ---")
    # Get console info
    r1_console = await client.get_node_console_info(PROJECT_ID, r1_id)
    print(f"R1 Console: {r1_console}")
    
    if r1_console["host"]:
        tn = TelnetClient(r1_console["host"], r1_console["port"], timeout=60)
        if tn.connect():
            print("Connected to R1. Waiting for boot...")
            if tn.wait_for_boot(timeout=120):
                print("R1 Booted. Sending commands...")
                cmds = [
                    "enable",
                    "conf t",
                    "int gi0/0",
                    "ip address 192.168.1.1 255.255.255.0",
                    "no shut",
                    "end", 
                    "show ip int brief"
                ]
                for cmd in cmds:
                    res = tn.send_cmd(cmd, wait_time=0.5)
                    print(f"CMD: {cmd}") # -> {res.strip()}")
                print("R1 Configured.")
            else:
                print("R1 Boot Timeout.")
            tn.close()
        else:
            print("Failed to connect to R1.")

    print("\n--- 5. Configure PC1 via Console ---")
    pc1_console = await client.get_node_console_info(PROJECT_ID, pc1_id)
    print(f"PC1 Console: {pc1_console}")
    
    if pc1_console["host"]:
        tn = TelnetClient(pc1_console["host"], pc1_console["port"])
        if tn.connect():
            print("Connected to PC1.")
            tn.send_cmd("\r")
            res = tn.send_cmd("ip 192.168.1.2/24 192.168.1.1", wait_time=2)
            print(f"IP Config: {res.strip()}")
            
            print("Pinging Gateway...")
            res = tn.send_cmd("ping 192.168.1.1", wait_time=5)
            print(f"Ping Result: {res.strip()}")
            tn.close()

if __name__ == "__main__":
    asyncio.run(main())
