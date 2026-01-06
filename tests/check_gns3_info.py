import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        try:
            # Get Computes
            print("--- Computes ---")
            r = await client.get("http://localhost:3080/v2/computes")
            computes = r.json()
            print(json.dumps(computes, indent=2))
            
            # Get Templates
            print("\n--- Templates ---")
            r = await client.get("http://localhost:3080/v2/templates")
            templates = r.json()
            # print only names and ids to save space
            summary = [{"name": t.get("name"), "id": t.get("template_id"), "type": t.get("template_type")} for t in templates]
            print(json.dumps(summary, indent=2))
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

