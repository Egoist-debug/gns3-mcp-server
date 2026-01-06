import asyncio
import httpx

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
L1_ID = "24307f38-b9d7-418f-bd60-126fbd91f155"
OLD_SW1_ID = "8e879239-048a-4122-8e52-518b3b453ae3"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Delete Old Switch1 (Links are auto-deleted)
        print("Deleting Switch1...")
        await client.delete(f"{API_URL}/projects/{PROJECT_ID}/nodes/{OLD_SW1_ID}")
        
        # 2. Create New Switch1
        print("Creating Switch1_New...")
        # Template for Ethernet Switch: 1966b864-93e7-32d5-965f-001384eec461
        resp = await client.post(
            f"{API_URL}/projects/{PROJECT_ID}/templates/1966b864-93e7-32d5-965f-001384eec461",
            json={"x": -100, "y": 0, "compute_id": "local", "name": "Switch1_New"}
        )
        new_sw = resp.json()
        new_id = new_sw['node_id']
        print(f"Created Switch1_New (ID: {new_id})")
        
        # 3. Create Links
        print("Linking...")
        # R1 (Gi0/0) -> Switch1_New
        link1 = {
            "nodes": [
                {"node_id": R1_ID, "adapter_number": 0, "port_number": 0},
                {"node_id": new_id, "adapter_number": 0, "port_number": 0}
            ]
        }
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link1)
        
        # Switch1_New -> Laptop1
        link2 = {
            "nodes": [
                {"node_id": new_id, "adapter_number": 0, "port_number": 1},
                {"node_id": L1_ID, "adapter_number": 0, "port_number": 0}
            ]
        }
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/links", json=link2)
        
        # 4. Start New Switch
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{new_id}/start")
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
