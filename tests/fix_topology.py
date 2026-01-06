import asyncio
import httpx

# IDs from previous run
PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
SW2_ID = "ca5fb7a9-71bf-4c54-9f88-197ced2ba797"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Update R1 adapters
        print("Updating R1 adapters...")
        try:
            # First stop the node if it's running (it shouldn't be, but good practice)
            await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}/stop")
            
            # Update properties
            resp = await client.put(
                f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}",
                json={"properties": {"adapters": 2}}
            )
            resp.raise_for_status()
            print("R1 updated with 2 adapters.")
        except Exception as e:
            print(f"Error updating R1: {e}")

        # 2. Link R1 (e1) -> Switch2 (e0)
        print("Linking R1 -> Switch2...")
        try:
            link_data = {
                "nodes": [
                    {"node_id": R1_ID, "adapter_number": 1, "port_number": 0}, # Ethernet1
                    {"node_id": SW2_ID, "adapter_number": 0, "port_number": 0}  # Ethernet0
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
