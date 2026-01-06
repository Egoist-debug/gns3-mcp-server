import asyncio
import httpx
import json

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        nodes = ["e7b85a31-83f1-4e8d-a7c7-d21b18367bbe", "24307f38-b9d7-418f-bd60-126fbd91f155", "4aee526c-a689-4792-ae5c-d1fa64de632a"]
        names = ["R1", "Laptop1", "Laptop2"]
        
        for name, node_id in zip(names, nodes):
            resp = await client.get(f"{API_URL}/projects/{PROJECT_ID}/nodes/{node_id}")
            data = resp.json()
            print(f"{name}: Host={data.get('console_host')}, Port={data.get('console')}")

if __name__ == "__main__":
    asyncio.run(main())
