"""Generate local secrets into the repo-root .env (git-ignored): passport signing key + demo API keys.

Existing values are kept. Production keys are generated the same way, stored in AWS SSM
Parameter Store and never written to disk on the server.
Run: uv run python -m titlivo.tools.keys
"""

import json
import secrets

from joserfc.jwk import OKPKey

from titlivo.settings import REPO_ROOT


def main() -> None:
    env = REPO_ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    present = {ln.split("=", 1)[0] for ln in lines if "=" in ln and not ln.startswith("#")}
    added = []
    wanted = {
        "PASSPORT_SIGNING_JWK": lambda: "'" + json.dumps(OKPKey.generate_key("Ed25519").as_dict(private=True)) + "'",
        "DEMO_API_KEY": lambda: "tlv_live_" + secrets.token_urlsafe(24),
        "ADMIN_API_KEY": lambda: "tlv_admin_" + secrets.token_urlsafe(24),
    }
    for k, make in wanted.items():
        if k not in present:
            lines.append(f"{k}={make()}")
            added.append(k)
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("added:", added or "nothing (all keys already present)")


if __name__ == "__main__":
    main()
