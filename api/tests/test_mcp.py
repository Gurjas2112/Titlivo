import pytest
from fastmcp import Client

from titlivo.mcp_server import mcp


def test_mcp_requires_key(client):
    r = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401 and r.headers["content-type"] == "application/problem+json"


@pytest.mark.asyncio
async def test_mcp_tools_listed():
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
    assert names == {"search_parcels", "get_parcel_dossier", "get_title_chain", "list_red_flags"}
