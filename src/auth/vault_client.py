"""
HashiCorp Vault client for production secret retrieval.
Falls back to environment variables in development.
"""
from src.core.config import settings


class VaultClient:

    def __init__(self) -> None:
        self._client = None

    def _connect(self):
        if settings.app_env == "development" or not settings.vault_addr:
            return None
        import hvac

        client = hvac.Client(url=settings.vault_addr)
        with open(
            "/var/run/secrets/kubernetes.io/serviceaccount/token"
        ) as f:
            jwt_token = f.read()
        client.auth.kubernetes.login(role=settings.vault_role, jwt=jwt_token)
        return client

    def get_secret(self, path: str, key: str) -> str:
        if settings.app_env == "development":
            env_key = f"{path.replace('/', '_').upper()}_{key.upper()}"
            return getattr(settings, env_key.lower(), "")

        if self._client is None:
            self._client = self._connect()
        if self._client is None:
            return ""

        secret = self._client.secrets.kv.v2.read_secret_version(path=path)
        return secret["data"]["data"].get(key, "")


vault_client = VaultClient()
