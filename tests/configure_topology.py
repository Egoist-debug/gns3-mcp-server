import asyncio
import httpx
import logging

# Config
PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
API_URL = "http://localhost:3080/v2"

# Templates
TEMPLATES = {
    "R1": {"id": "25f27a32-288d-4d47-abe7-34a36e58ee36", "compute": "local", "x": 0, "y": -100},
    "Switch1": {"id": "1966b864-93e7-32d5-965f-001384eec461", "compute": "local", "x": -100, "y": 0},
    "Switch2": {"id": "1966b864-93e7-32d5-965f-001384eec461", "compute": "local", "x": 100, "y": 0},
    "Laptop1": {"id": "19021f99-e36f-394d-b4a1-8aaa902ab9cc", "compute": "local", "x": -100, "y": 100}
}

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Create Nodes
        nodes = {}
        for name, info in TEMPLATES.items():
            print(f"Creating {name}...")
            try:
                resp = await client.post(
                    f"{API_URL}/projects/{PROJECT_ID}/templates/{info['id']}",
                    json={"x": info["x"], "y": info["y"], "compute_id": info["compute"], "name": name}
                )
                if resp.status_code >= 400:
                    print(f"Failed to create {name}: {resp.text}")
                    # Try VM if local fails for Router
                    if name == "R1" and info["compute"] == "local":
                        print("Retrying R1 on VM...")
                        resp = await client.post(
                            f"{API_URL}/projects/{PROJECT_ID}/templates/{info['id']}",
                            json={"x": info["x"], "y": info["y"], "compute_id": "vm", "name": name}
                        )
                
                resp.raise_for_status()
                node = resp.json()
                nodes[name] = node
                print(f"Created {name} (ID: {node['node_id']})")
            except Exception as e:
                print(f"Error creating {name}: {e}")
                return

        # 2. Get Node Ports
        node_ports = {}
        for name, node in nodes.items():
            try:
                resp = await client.get(f"{API_URL}/projects/{PROJECT_ID}/nodes/{node['node_id']}")
                details = resp.json()
                node_ports[name] = details.get("ports", [])
            except Exception as e:
                print(f"Error getting ports for {name}: {e}")

        # Helper to find port
        def get_port(node_name, port_index):
            ports = node_ports.get(node_name, [])
            if port_index < len(ports):
                return ports[port_index]
            return None

        # 3. Create Links
        links_to_create = [
            ("R1", 0, "Switch1", 0), # R1 e0 -> Switch1 Port 1
            ("R1", 1, "Switch2", 0), # R1 e1 -> Switch2 Port 1
            ("Switch1", 1, "Laptop1", 0) # Switch1 Port 2 -> Laptop1 e0
        ]

        for src, src_idx, dst, dst_idx in links_to_create:
            print(f"Linking {src} to {dst}...")
            p1 = get_port(src, src_idx)
            p2 = get_port(dst, dst_idx)
            
            if not p1 or not p2:
                print(f"Cannot link {src} to {dst}: Ports not found (indices {src_idx}, {dst_idx})")
                continue

            link_data = {
                "nodes": [
                    {"node_id": nodes[src]["node_id"], "adapter_number": p1["adapter_number"], "port_number": p1["port_number"]},
                    {"node_id": nodes[dst]["node_id"], "adapter_number": p2["adapter_number"], "port_number": p2["port_number"]}
                ]
            }
            
            try:
                resp = await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link_data)
                if resp.status_code >= 400:
                    print(f"Failed to link: {resp.text}")
                else:
                    print(f"Link created: {src}:{p1['name']} <-> {dst}:{p2['name']}")
            except Exception as e:
                print(f"Error linking: {e}")

if __name__ == "__main__":
    asyncio.run(main())
