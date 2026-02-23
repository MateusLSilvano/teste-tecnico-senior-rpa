import json
import pytest
import httpx

from app.crawlers.oscar import fetch_oscar

pytestmark = pytest.mark.asyncio


def _handler_dict(request: httpx.Request) -> httpx.Response:
    year = int(request.url.params.get("year"))
    payload = {"data": [{"title": f"Movie {year}", "nominations": "2", "awards": "1", "best_picture": "false"}]}
    return httpx.Response(200, content=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})


def _handler_list(request: httpx.Request) -> httpx.Response:
    year = int(request.url.params.get("year"))
    payload = [{"title": f"Movie {year}", "nominations": 3, "awards": 2, "best_picture": True}]
    return httpx.Response(200, content=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})


async def test_fetch_oscar_with_dict_payload_transport():
    transport = httpx.MockTransport(_handler_dict)
    async with httpx.AsyncClient(transport=transport) as client:
        rows = await fetch_oscar([2014, 2015], client=client)

    assert len(rows) == 2
    assert rows[0]["year"] == 2014
    assert rows[0]["title"] == "Movie 2014"
    assert rows[0]["best_picture"] is False


async def test_fetch_oscar_with_list_payload_transport():
    transport = httpx.MockTransport(_handler_list)
    async with httpx.AsyncClient(transport=transport) as client:
        rows = await fetch_oscar([2010], client=client)

    assert len(rows) == 1
    assert rows[0]["title"] == "Movie 2010"
    assert rows[0]["best_picture"] is True