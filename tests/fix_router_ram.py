import asyncio
import httpx

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        print("Stopping R1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}/stop")
        
        print("Updating RAM to 512MB...")
        resp = await client.put(
            f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}",
            json={"properties": {"ram": 512}}
        )
        if resp.status_code >= 400:
            print(f"Failed to update RAM: {resp.text}")
            return
            
        print("Starting R1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}/start")
        print("R1 restarted with 512MB RAM.")

if __name__ == "__main__":
    asyncio.run(main())
