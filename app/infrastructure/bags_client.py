import httpx
import logging
from typing import Any
from app.config import get_settings

logger = logging.getLogger(__name__)


class BagsAPIError(Exception):
    """Raised when the Bags API returns an error or unexpected response."""
    pass


class BagsClient:
    """
    HTTP client for the Bags.fm creator economy API.
    Handles creator token data, market stats, and holder info.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.bags_api_base_url
        self._api_key = settings.bags_api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=httpx.Timeout(10.0),
        )

    async def fetch_creator(self, bags_id: str) -> dict[str, Any]:
        """Fetch full creator profile including token stats."""
        try:
            response = await self._client.get(f"/creators/{bags_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Bags API HTTP error for creator %s: %s", bags_id, exc)
            raise BagsAPIError(f"Creator fetch failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("Bags API request error: %s", exc)
            raise BagsAPIError("Bags API unreachable") from exc

    async def fetch_trending_creators(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch creators sorted by 24h volume momentum."""
        try:
            response = await self._client.get(
                "/creators/trending",
                params={"limit": limit, "sort": "volume_24h"}
            )
            response.raise_for_status()
            return response.json().get("creators", [])
        except httpx.HTTPStatusError as exc:
            logger.error("Bags API trending fetch failed: %s", exc)
            raise BagsAPIError(f"Trending fetch failed: {exc.response.status_code}") from exc

    async def fetch_creator_holders(self, token_mint: str) -> list[dict[str, Any]]:
        """Fetch top holder list for whale accumulation analysis."""
        try:
            response = await self._client.get(
                f"/tokens/{token_mint}/holders",
                params={"limit": 100}
            )
            response.raise_for_status()
            return response.json().get("holders", [])
        except httpx.HTTPStatusError as exc:
            logger.error("Bags holders fetch failed for %s: %s", token_mint, exc)
            raise BagsAPIError(f"Holders fetch failed") from exc

    async def close(self) -> None:
        await self._client.aclose()