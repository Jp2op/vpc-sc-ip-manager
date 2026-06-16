import json
import base64
import logging
import httpx
from app.config import get_settings
from app.models.schemas import IPEntry

logger = logging.getLogger(__name__)


class GitHubService:
    """Commits access_config.json to GitHub.
    Runs in mock mode if no token/repo is configured.
    """

    def __init__(self):
        s = get_settings()
        self.token = s.github_token
        self.repo = s.github_repo
        self.config_path = s.github_config_path
        self.branch = s.github_branch
        self.admin_ips = s.admin_ips
        self.mock = not self.token or not self.repo

        if self.mock:
            logger.info("GitHub service: MOCK mode (no token/repo)")
        else:
            logger.info(f"GitHub service: connected to {self.repo}")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def commit_config(self, active_ips: list[IPEntry], message: str) -> bool:
        config = self._build_config(active_ips)
        config_json = json.dumps(config, indent=2) + "\n"

        if self.mock:
            logger.info(f"[MOCK] Commit: {message}")
            logger.info(f"[MOCK] Config:\n{config_json}")
            return True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get current file SHA
                sha = await self._get_sha(client)

                payload = {
                    "message": message,
                    "content": base64.b64encode(config_json.encode()).decode(),
                    "branch": self.branch,
                }
                if sha:
                    payload["sha"] = sha

                url = f"https://api.github.com/repos/{self.repo}/contents/{self.config_path}"
                resp = await client.put(url, headers=self._headers(), json=payload)

                if resp.status_code in (200, 201):
                    logger.info(f"GitHub commit OK: {message}")
                    return True

                logger.error(f"GitHub commit failed: {resp.status_code} {resp.text}")
                return False

        except Exception as e:
            logger.error(f"GitHub error: {e}")
            return False

    async def _get_sha(self, client: httpx.AsyncClient) -> str | None:
        url = f"https://api.github.com/repos/{self.repo}/contents/{self.config_path}"
        resp = await client.get(url, headers=self._headers(), params={"ref": self.branch})
        if resp.status_code == 200:
            return resp.json().get("sha")
        return None

    def _build_config(self, active_ips: list[IPEntry]) -> dict:
        allowed = {entry.ip: entry.name for entry in active_ips}
        admins = {}
        if self.admin_ips:
            for ip in self.admin_ips.split(","):
                ip = ip.strip()
                if ip:
                    admins[ip] = "Admin"
        return {"allowed_ips": allowed, "admin_ips": admins}
