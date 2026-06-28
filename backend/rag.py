"""
RAG layer — semantic search and document embedding via Supabase pgvector.
Ported from v2. Uses service role key for admin embed operations.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx


DEFAULT_EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_EMBED_DIMS = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))


@dataclass(frozen=True)
class RagChunk:
    source: str
    chunk_index: int
    content: str
    content_hash: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_rag_sources(repo_root: Path) -> list[tuple[str, str]]:
    """Returns (source_name, content) pairs from rag/*.md files."""
    sources: list[tuple[str, str]] = []
    rag_dir = repo_root / "rag"
    if rag_dir.exists():
        for p in sorted(rag_dir.glob("*.md")):
            content = p.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                sources.append((f"rag/{p.name}", content))
    return sources


def chunk_markdown(source: str, content: str, target_chars: int = 2400) -> list[RagChunk]:
    """Split markdown content into chunks roughly under target_chars."""
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = content.split("\n")

    blocks: list[str] = []
    buf: list[str] = []
    for line in lines:
        is_heading = bool(re.match(r"^\s*#{1,6}\s+", line))
        if is_heading and buf:
            blocks.append("\n".join(buf).strip())
            buf = [line]
            continue
        if not line.strip() and buf:
            blocks.append("\n".join(buf).strip())
            buf = []
            continue
        buf.append(line)
    if buf:
        blocks.append("\n".join(buf).strip())

    chunks: list[str] = []
    current = ""
    for b in blocks:
        if not b:
            continue
        if not current:
            current = b
            continue
        if len(current) + 2 + len(b) <= target_chars:
            current = f"{current}\n\n{b}"
        else:
            chunks.append(current.strip())
            current = b
    if current:
        chunks.append(current.strip())

    return [
        RagChunk(source=source, chunk_index=idx, content=c, content_hash=_sha256(c))
        for idx, c in enumerate(chunks)
    ]


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


async def embed_texts_openai(texts: list[str]) -> list[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")

    batch_size = int(os.getenv("OPENAI_EMBED_BATCH_SIZE", "20"))
    batch_sleep_s = float(os.getenv("OPENAI_EMBED_BATCH_SLEEP_S", "1.5"))
    max_attempts = int(os.getenv("OPENAI_EMBED_MAX_ATTEMPTS", "6"))
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        for batch_start in range(0, len(texts), batch_size):
            batch = texts[batch_start: batch_start + batch_size]
            payload: dict = {"model": DEFAULT_EMBED_MODEL, "input": batch}
            if DEFAULT_EMBED_DIMS:
                payload["dimensions"] = DEFAULT_EMBED_DIMS

            for attempt in range(max_attempts):
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    content=json.dumps(payload).encode("utf-8"),
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", 0))
                    wait = retry_after if retry_after > 0 else (2 ** attempt) * 5
                    print(f"  429 rate limit — waiting {wait}s (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                all_embeddings.extend(item["embedding"] for item in data["data"])
                break
            else:
                raise RuntimeError(f"Embedding batch failed after {max_attempts} attempts")

            if batch_start + batch_size < len(texts):
                await asyncio.sleep(batch_sleep_s)

    return all_embeddings


def _supabase_url() -> str:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set")
    return url


def _supabase_service_key() -> str:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set")
    return key


def _rest_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def similarity_search(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over RAG documents. Returns [{source, content, similarity}]."""
    if not query.strip():
        return []

    q_emb = (await embed_texts_openai([query]))[0]

    base_url = _supabase_url()
    key = _supabase_service_key()
    match_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.2"))

    payload = {
        "query_embedding": _vector_literal(q_emb),
        "match_user_id": user_id,
        "match_threshold": match_threshold,
        "match_count": top_k,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base_url}/rest/v1/rpc/match_rag_documents",
            headers=_rest_headers(key),
            content=json.dumps(payload).encode(),
        )
        resp.raise_for_status()
    return resp.json()


async def search_rag(query: str, user_id: str, threshold: float = 0.7, count: int = 5) -> list[dict]:
    """Alias used by memory router."""
    if not query.strip():
        return []
    q_emb = (await embed_texts_openai([query]))[0]
    base_url = _supabase_url()
    key = _supabase_service_key()
    payload = {
        "query_embedding": _vector_literal(q_emb),
        "match_user_id": user_id,
        "match_threshold": threshold,
        "match_count": count,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base_url}/rest/v1/rpc/match_rag_documents",
            headers=_rest_headers(key),
            content=json.dumps(payload).encode(),
        )
        resp.raise_for_status()
    return resp.json()


def build_rag_context(results: Iterable[dict], max_chars: int = 2400) -> str | None:
    """Convert retrieval results into a compact context block for system prompt injection."""
    parts: list[str] = []
    used = 0
    for r in results:
        src = str(r.get("source", ""))
        sim = r.get("similarity")
        content = str(r.get("content", "")).strip()
        if not content:
            continue
        header = f"[{src}]"
        if isinstance(sim, (int, float)):
            header = f"{header} (sim={sim:.3f})"
        block = f"{header}\n{content}"
        if used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    if not parts:
        return None
    return "PROFILE MEMORY (retrieved)\n\n" + "\n\n---\n\n".join(parts)


async def upsert_document(user_id: str, source: str, content: str, chunk_index: int = 0):
    """Embed and upsert a single document chunk into the RAG store."""
    content_hash = _sha256(content)
    base_url = _supabase_url()
    key = _supabase_service_key()
    headers = _rest_headers(key)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check if already up-to-date
        check = await client.get(
            f"{base_url}/rest/v1/rag_documents",
            headers=headers,
            params={
                "select": "id",
                "user_id": f"eq.{user_id}",
                "source": f"eq.{source}",
                "content_hash": f"eq.{content_hash}",
            },
        )
        if check.json():
            return

        try:
            embedding = (await embed_texts_openai([content[:8000]]))[0]
        except Exception as e:
            print(f"Embedding error: {e}")
            return

        row = {
            "user_id": user_id,
            "source": source,
            "chunk_index": chunk_index,
            "content": content,
            "content_hash": content_hash,
            "embedding": _vector_literal(embedding),
        }
        upsert_headers = {
            **headers,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        resp = await client.post(
            f"{base_url}/rest/v1/rag_documents?on_conflict=user_id,source,chunk_index",
            headers=upsert_headers,
            content=json.dumps([row]).encode(),
        )
        resp.raise_for_status()
