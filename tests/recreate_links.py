import asyncio
import httpx

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
SW1_ID = "8e879239-048a-4122-8e52-518b3b453ae3"
L1_ID = "24307f38-b9d7-418f-bd60-126fbd91f155"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Get Links
        print("Getting links...")
        resp = await client.get(f"{API_URL}/projects/{PROJECT_ID}/links")
        links = resp.json()
        
        # 2. Find links for Switch1
        links_to_delete = []
        for link in links:
            node_ids = [n['node_id'] for n in link['nodes']]
            if SW1_ID in node_ids:
                links_to_delete.append(link['link_id'])
        
        # 3. Delete Links
        print(f"Deleting {len(links_to_delete)} links for Switch1...")
        for link_id in links_to_delete:
            await client.delete(f"{API_URL}/projects/{PROJECT_ID}/links/{link_id}")
        
        # 4. Recreate Links
        print("Recreating links...")
        
        # R1 (Gi0/0) -> Switch1 (Port 1)
        # Gi0/0 is usually adapter 0, port 0 for IOSv if it has 2 adapters? 
        # Wait, IOSv with 2 adapters usually has Gi0/0 and Gi0/1.
        # But earlier output for R1 showed "adapters: 2".
        # Let's assume adapter 0 port 0 is Gi0/0.
        
        link1 = {
            "nodes": [
                {"node_id": R1_ID, "adapter_number": 0, "port_number": 0},
                {"node_id": SW1_ID, "adapter_number": 0, "port_number": 0}
            ]
        }
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link1)
        
        # Switch1 (Port 2) -> Laptop1
        link2 = {
            "nodes": [
                {"node_id": SW1_ID, "adapter_number": 0, "port_number": 1},
                {"node_id": L1_ID, "adapter_number": 0, "port_number": 0}
            ]
        }
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link2)
        
        print("Links recreated.")

if __name__ == "__main__":
    asyncio.run(main())
