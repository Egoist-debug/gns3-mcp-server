import asyncio
import httpx
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class GNS3Config(BaseModel):
    server_url: str = "http://localhost:3080"
    username: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: bool = True

class GNS3APIClient:
    def __init__(self, config: GNS3Config):
        self.config = config
        self.base_url = config.server_url.rstrip('/')
        self.auth = None
        if config.username and config.password:
            self.auth = (config.username, config.password)
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/v2{endpoint}"
        print(f"Requesting: {method} {url}")
        headers = {"Content-Type": "application/json"}
        
        async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, auth=self.auth)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers, auth=self.auth)
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            response.raise_for_status()
            return response.json()

async def main():
    config = GNS3Config()
    client = GNS3APIClient(config)
    try:
        print("Testing /version...")
        await client._request("GET", "/version")
        print("\nTesting /projects...")
        await client._request("GET", "/projects")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
