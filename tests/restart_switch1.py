import asyncio
import httpx
import time

PROJECT_ID = "46122279-e935-4f4d-b208-3a1501093bb8"
SW1_ID = "8e879239-048a-4122-8e52-518b3b453ae3"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        print("Stopping Switch1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{SW1_ID}/stop")
        
        print("Waiting 1 second...")
        time.sleep(1)
        
        print("Starting Switch1...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/{SW1_ID}/start")
        print("Switch1 restarted.")

if __name__ == "__main__":
    asyncio.run(main())
