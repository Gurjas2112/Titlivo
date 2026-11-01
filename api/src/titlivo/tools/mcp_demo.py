"""Call the Titlivo MCP server over Streamable HTTP, the way an external AI agent would.

Run: uv run python -m titlivo.tools.mcp_demo [--url http://localhost:8000/mcp/]
"""

import argparse
import asyncio
import re

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from titlivo.settings import get_settings


async def run(url: str, key: str) -> None:
    async with Client(StreamableHttpTransport(url, headers={"Authorization": f"Bearer {key}"})) as c:
        tools = await c.list_tools()
        print(f"$ mcp tools/list  →  {len(tools)} tools")
        for t in tools:
            first = re.split(r"(?<=[a-z)])\.\s", " ".join((t.description or "").split()))[0]
            print(f"  • {t.name}: {first}")
        hits = (await c.call_tool("search_parcels", {"query": "214/2", "limit": 3})).structured_content["result"]
        print(f"\n$ mcp tools/call search_parcels {{query: '214/2'}}  →  {len(hits)} parcels")
        for h in hits:
            print(f"  {h['id']}  survey {h['survey_no']}  {h['village']} ({h['state']})")
        async with httpx.AsyncClient() as http:
            f12 = (await http.get(url.replace("/mcp/", "/v1/demo/parcels"))).json()["F12"]
        flags = (await c.call_tool("list_red_flags", {"parcel_id": f12})).structured_content["result"]
        print(f"\n$ mcp tools/call list_red_flags {{parcel_id: '{f12}'}}")
        for f in flags:
            print(f"  [{f['id']}] {f['severity'].upper()}: {f['text']}")
            print(f"        source: {f['source_record_id']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/mcp/")
    a = ap.parse_args()
    asyncio.run(run(a.url, get_settings().demo_api_key))


if __name__ == "__main__":
    main()
