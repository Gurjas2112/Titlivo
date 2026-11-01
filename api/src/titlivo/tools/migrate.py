"""Apply supabase/migrations/*.sql in order, once each (tracked in public.titlivo_migrations).

Works against the local docker database and against any Supabase project (pass --url).
Run: uv run python -m titlivo.tools.migrate [--url postgresql://…]
"""

import argparse

import psycopg

from titlivo.settings import REPO_ROOT, get_settings


def run(url: str) -> list[str]:
    applied = []
    with psycopg.connect(url, autocommit=True, prepare_threshold=None) as conn:
        conn.execute("create table if not exists public.titlivo_migrations (name text primary key, applied_at timestamptz default now())")
        done = {r[0] for r in conn.execute("select name from public.titlivo_migrations")}
        for f in sorted((REPO_ROOT / "supabase" / "migrations").glob("*.sql")):
            if f.name in done:
                continue
            with conn.transaction():
                conn.execute(f.read_text(encoding="utf-8"))
                conn.execute("insert into public.titlivo_migrations (name) values (%s)", (f.name,))
            applied.append(f.name)
    return applied


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    a = ap.parse_args()
    print("applied:", run(a.url or get_settings().database_url) or "nothing new")


if __name__ == "__main__":
    main()
