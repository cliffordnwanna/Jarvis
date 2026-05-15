from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running via `python backend/scripts/rag_ingest.py` from repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# override=True so the last occurrence in the .env file wins (avoids confusion if variables are duplicated).
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)

from backend.rag import (
    DEFAULT_EMBED_DIMS,
    DEFAULT_EMBED_MODEL,
    chunk_markdown,
    delete_chunk_indices,
    embed_texts_openai,
    get_existing_hashes,
    iter_rag_sources,
    upsert_chunks,
)


async def main() -> None:
    repo_root = REPO_ROOT
    user_id = os.getenv("RAG_USER_ID", "default")
    target_chars = int(os.getenv("RAG_CHUNK_TARGET_CHARS", "2400"))

    sources = iter_rag_sources(repo_root)
    if not sources:
        raise SystemExit("No RAG sources found (expected rag/*.md and/or backend/agent.py SYSTEM_PROMPT).")

    print(f"RAG ingest: user_id={user_id}")
    print(f"Embedding model={DEFAULT_EMBED_MODEL} dims={DEFAULT_EMBED_DIMS}")
    print(f"Sources={len(sources)} target_chars={target_chars}")

    total_chunks = 0
    total_upserts = 0

    for source_name, content in sources:
        chunks = chunk_markdown(source=source_name, content=content, target_chars=target_chars)
        if not chunks:
            continue
        existing = await get_existing_hashes(user_id=user_id, source=source_name)
        desired_indices = {c.chunk_index for c in chunks}
        stale_indices = [idx for idx in existing.keys() if idx not in desired_indices]

        changed_chunks = [c for c in chunks if existing.get(c.chunk_index) != c.content_hash]
        if changed_chunks:
            texts = [c.content for c in changed_chunks]
            embeddings = await embed_texts_openai(texts)
            upserts = await upsert_chunks(user_id=user_id, chunks=changed_chunks, embeddings=embeddings)
        else:
            upserts = 0

        if stale_indices:
            await delete_chunk_indices(user_id=user_id, source=source_name, chunk_indices=stale_indices)

        total_chunks += len(chunks)
        total_upserts += upserts
        print(
            f"- {source_name}: chunks={len(chunks)} updated={upserts} deleted={len(stale_indices)} unchanged={len(chunks) - upserts}"
        )

    print(f"Done. chunks={total_chunks} upserted={total_upserts}")


if __name__ == "__main__":
    asyncio.run(main())
