"""Runtime settings, read from the environment and the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env",), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54329/titlivo"
    public_api_base: str = "http://localhost:8000"
    public_web_base: str = "http://localhost:5173"
    issuer_did: str = "did:web:localhost%3A8000"
    cors_origins: str = "http://localhost:5173"

    # Demo access. Keys with the `parcels:pii` scope see unmasked names.
    demo_api_key: str = "tlv_demo_local_only"
    admin_api_key: str = "tlv_admin_local_only"

    # Title Passport
    passport_signing_jwk: str = ""  # Ed25519 private JWK (JSON). `make keys` writes one.
    passport_validity_days: int = 90
    status_list_size: int = 131072

    # Ask the Property
    google_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    llm_mode: str = "live"  # live | mock

    @model_validator(mode="after")
    def _no_placeholder_keys_in_prod(self) -> "Settings":
        if self.app_env == "prod":
            bad = [k for k in ("demo_api_key", "admin_api_key") if getattr(self, k).endswith("_local_only")]
            if bad or not self.passport_signing_jwk:
                raise ValueError(f"production needs real secrets; missing or placeholder: {bad or ['passport_signing_jwk']}")
        return self

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
