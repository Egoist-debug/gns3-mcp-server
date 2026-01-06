import asyncio
import httpx

PROJECT_ID = "3b705e60-bf7a-42ca-a7c1-9b7f310f475c"
API_URL = "http://localhost:3080/v2"

async def main():
    async with httpx.AsyncClient() as client:
        print("Stopping nodes...")
        await client.post(f"{API_URL}/projects/{PROJECT_ID}/nodes/stop")
        print("Deleting project...")
        await client.delete(f"{API_URL}/projects/{PROJECT_ID}")
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
