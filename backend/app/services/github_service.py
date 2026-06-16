import json
import base64
import logging
import asyncio
import httpx
from app.config import get_settings
from app.models.schemas import IPEntry

logger = logging.getLogger(__name__)


class GitHubService:

    def __init__(self):
        s = get_settings()
        self.token = s.github_token
        self.repo = s.github_repo
        self.config_path = s.github_config_path
        self.branch = s.github_branch
        self.admin_ips = s.admin_ips
        self.mock = not self.token or not self.repo

        # Debounce — batch all changes within 30s into one commit
        self._debounce_task: asyncio.Task | None = None
        self._debounce_seconds = 30
        self._commit_messages: list[str] = []
        self._storage = None  # Set via set_storage()

        if self.mock:
            logger.info("GitHub service: MOCK mode")
        else:
            logger.info(f"GitHub service: connected to {self.repo}")

    def set_storage(self, storage):
        """Give GitHub service access to storage for fetching active IPs at commit time."""
        self._storage = storage

    async def request_commit(self, message: str):
        """Request a commit. Actual commit happens after 30s of no new changes."""
        self._commit_messages.append(message)

        # Reset the timer
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounce_commit())

    async def _debounce_commit(self):
        """Wait 30s, then commit all batched changes in one shot."""
        try:
            await asyncio.sleep(self._debounce_seconds)
        except asyncio.CancelledError:
            return  # Timer reset by a new change

        if not self._commit_messages:
            return

        messages = self._commit_messages.copy()
        self._commit_messages.clear()

        if len(messages) == 1:
            commit_msg = messages[0]
        else:
            commit_msg = f"Batch update: {len(messages)} IP changes\n\n" + "\n".join(f"- {m}" for m in messages)

        if self._storage:
            active_ips = await self._storage.get_active_ips()
        else:
            active_ips = []

        logger.info(f"Debounce fired — committing {len(messages)} change(s)")
        await self._do_commit(active_ips, commit_msg)

    async def force_commit(self, active_ips: list[IPEntry], message: str):
        """Bypass debounce — commit immediately. Used for startup recovery."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._commit_messages.clear()

        return await self._do_commit(active_ips, message)

    async def _do_commit(self, active_ips: list[IPEntry], message: str):
        config = self._build_config(active_ips)
        config_json = json.dumps(config, indent=2) + "\n"

        if self.mock:
            logger.info(f"[MOCK] Commit: {message}")
            logger.info(f"[MOCK] Config:\n{config_json}")
            return True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

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
