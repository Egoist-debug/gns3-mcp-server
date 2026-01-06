import asyncio
import httpx

# IDs
PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
SW2_ID = "ca5fb7a9-71bf-4c54-9f88-197ced2ba797"
LAPTOP2_TEMPLATE_ID = "19021f99-e36f-394d-b4a1-8aaa902ab9cc"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Create Laptop2
        print("Creating Laptop2...")
        try:
            resp = await client.post(
                f"{API_URL}/projects/{PROJECT_ID}/templates/{LAPTOP2_TEMPLATE_ID}",
                json={"x": 200, "y": 100, "compute_id": "local", "name": "Laptop2"}
            )
            resp.raise_for_status()
            node = resp.json()
            laptop2_id = node['node_id']
            print(f"Created Laptop2 (ID: {laptop2_id})")
        except Exception as e:
            print(f"Error creating Laptop2: {e}")
            return

        # 2. Get Laptop2 Port
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_ID}/nodes/{laptop2_id}")
            details = resp.json()
            l2_port = details.get("ports", [])[0] # VPCS usually has 1 port (Ethernet0)
        except Exception as e:
            print(f"Error getting Laptop2 ports: {e}")
            return

        # 3. Get Switch2 Port (Need a free one)
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_ID}/nodes/{SW2_ID}")
            details = resp.json()
            sw2_ports = details.get("ports", [])
            # Find a free port (simplistic approach: take port 1, since port 0 is connected to R1)
            # Better: check links or just try next index
            sw2_port = sw2_ports[1] 
        except Exception as e:
            print(f"Error getting Switch2 ports: {e}")
            return

        # 4. Link Switch2 -> Laptop2
        print("Linking Switch2 -> Laptop2...")
        try:
            link_data = {
                "nodes": [
                    {"node_id": SW2_ID, "adapter_number": sw2_port["adapter_number"], "port_number": sw2_port["port_number"]},
                    {"node_id": laptop2_id, "adapter_number": l2_port["adapter_number"], "port_number": l2_port["port_number"]}
                ]
            }
            resp = await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link_data)
            if resp.status_code >= 400:
                print(f"Failed to link: {resp.text}")
            else:
                print("Link created successfully.")
        except Exception as e:
            print(f"Error linking: {e}")

if __name__ == "__main__":
    asyncio.run(main())
