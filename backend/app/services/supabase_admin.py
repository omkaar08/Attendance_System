from __future__ import annotations

from typing import Any

import httpx


class SupabaseAuthAdminClient:
    def __init__(self, *, base_url: str, service_role_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/auth/v1",
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json",
            },
            timeout=30.0,
            http2=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.request(method, path, params=params, json=body)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    async def list_users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        page = 1
        per_page = 1000

        while True:
            payload = await self._request("GET", "/admin/users", params={"page": page, "per_page": per_page})
            page_users = payload.get("users", []) if isinstance(payload, dict) else payload
            users.extend(page_users)

            if len(page_users) < per_page:
                break
            page += 1

        return users

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        target = email.strip().lower()
        for user in await self.list_users():
            if str(user.get("email", "")).strip().lower() == target:
                return user
        return None

    async def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/admin/users", body=payload)

    async def update_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", f"/admin/users/{user_id}", body=payload)
