"""Narrow GitHub App client for installation-scoped Mitro operations."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

API = "https://api.github.com"
API_VERSION = "2022-11-28"


class GitHubNotConfigured(RuntimeError):
    pass


class GitHubAPIError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@dataclass
class GitHubAppConfig:
    app_id: str
    slug: str
    private_key: str
    webhook_secret: str
    enable_pull_requests: bool

    @classmethod
    def load(cls) -> "GitHubAppConfig":
        app_id = os.getenv("MITRO_GITHUB_APP_ID", "").strip()
        slug = os.getenv("MITRO_GITHUB_APP_SLUG", "").strip()
        key_path = os.getenv("MITRO_GITHUB_PRIVATE_KEY_PATH", "").strip()
        key_value = os.getenv("MITRO_GITHUB_PRIVATE_KEY", "")
        if key_path:
            try:
                key_value = Path(key_path).expanduser().read_text(encoding="utf-8")
            except OSError as exc:
                raise GitHubNotConfigured(f"GitHub App private key file could not be read: {exc}") from exc
        key_value = key_value.replace("\\n", "\n").strip()
        if not app_id or not slug or not key_value:
            raise GitHubNotConfigured("Set MITRO_GITHUB_APP_ID, MITRO_GITHUB_APP_SLUG, and MITRO_GITHUB_PRIVATE_KEY_PATH to connect a GitHub App")
        return cls(app_id, slug, key_value, os.getenv("MITRO_GITHUB_WEBHOOK_SECRET", ""),
                   os.getenv("MITRO_GITHUB_ENABLE_PULL_REQUESTS", "false").lower() == "true")


def sign_webhook(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_webhook(secret: str, body: bytes, signature: str) -> bool:
    return bool(secret and signature and hmac.compare_digest(sign_webhook(secret, body), signature))


class GitHubAppClient:
    """Creates short-lived, repo-scoped installation tokens; never persists tokens."""
    def __init__(self, config: GitHubAppConfig | None = None, transport: httpx.BaseTransport | None = None):
        self.config = config or GitHubAppConfig.load()
        self._transport = transport
        self._tokens: dict[tuple, tuple[str, float]] = {}

    def app_jwt(self) -> str:
        try:
            import jwt
        except ImportError as exc:
            raise GitHubNotConfigured("Install PyJWT with cryptography support to use GitHub App authentication") from exc
        now = int(time.time())
        return jwt.encode({"iat": now - 60, "exp": now + 8 * 60, "iss": self.config.app_id},
                          self.config.private_key, algorithm="RS256")

    def _request(self, method: str, path: str, *, token: str, json: Any = None,
                 params: dict | None = None, binary: bool = False) -> httpx.Response:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION,
                   "Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=45.0, follow_redirects=binary, transport=self._transport) as client:
            response = client.request(method, API + path, headers=headers, json=json, params=params)
        if response.status_code >= 400:
            detail = "GitHub request failed"
            try:
                detail = str(response.json().get("message", detail))
            except Exception:
                pass
            raise GitHubAPIError(response.status_code, detail[:500])
        return response

    def app_get(self, path: str) -> dict:
        return self._request("GET", path, token=self.app_jwt()).json()

    def installation_token(self, installation_id: int, repo_ids: list[int] | None = None,
                           permissions: dict[str, str] | None = None) -> str:
        repos = sorted(set(repo_ids or []))
        perms = permissions or {"contents": "read", "metadata": "read"}
        key = (installation_id, tuple(repos), tuple(sorted(perms.items())))
        cached = self._tokens.get(key)
        if cached and cached[1] > time.time() + 120:
            return cached[0]
        body: dict[str, Any] = {"permissions": perms}
        if repos:
            body["repository_ids"] = repos
        response = self._request("POST", f"/app/installations/{installation_id}/access_tokens",
                                 token=self.app_jwt(), json=body)
        data = response.json()
        expiry = time.time() + 3000
        try:
            from datetime import datetime
            expiry = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
        self._tokens[key] = (data["token"], expiry)
        return data["token"]

    def get(self, installation_id: int, path: str, *, repo_ids: list[int] | None = None,
            params: dict | None = None, permissions: dict[str, str] | None = None) -> httpx.Response:
        return self._request("GET", path, token=self.installation_token(installation_id, repo_ids, permissions), params=params)

    def post(self, installation_id: int, path: str, *, repo_ids: list[int] | None = None,
             json: Any = None, permissions: dict[str, str] | None = None) -> httpx.Response:
        return self._request("POST", path, token=self.installation_token(installation_id, repo_ids, permissions), json=json)

    def put(self, installation_id: int, path: str, *, repo_ids: list[int] | None = None,
            json: Any = None, permissions: dict[str, str] | None = None) -> httpx.Response:
        return self._request("PUT", path, token=self.installation_token(installation_id, repo_ids, permissions), json=json)

    def download_archive(self, installation_id: int, repo_id: int, owner: str, name: str, ref: str) -> bytes:
        from urllib.parse import quote
        token = self.installation_token(installation_id, [repo_id])
        response = self._request("GET", f"/repos/{owner}/{name}/zipball/{quote(ref, safe='/')}", token=token, binary=True)
        return response.content

    @staticmethod
    def decode_content(data: dict) -> bytes:
        if data.get("encoding") != "base64":
            raise GitHubAPIError(422, "GitHub returned an unsupported file encoding")
        return base64.b64decode(data["content"])
