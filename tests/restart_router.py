import asyncio
import httpx
import time

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
R1_ID = "e7b85a31-83f1-4e8d-a7c7-d21b18367bbe"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        print("Stopping R1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}/stop")
        
        print("Waiting 2 seconds...")
        time.sleep(2)
        
        print("Starting R1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{R1_ID}/start")
        print("R1 restarted.")

if __name__ == "__main__":
    asyncio.run(main())
