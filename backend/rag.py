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


def extract_system_prompt_from_agent_py(repo_root: Path) -> str | None:
    agent_path = repo_root / "backend" / "agent.py"
    if not agent_path.exists():
        return None
    text = agent_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'SYSTEM_PROMPT\s*=\s*"""(.*?)"""', text, flags=re.DOTALL)
    if not m:
        return None
    return m.group(1).strip()


def iter_rag_sources(repo_root: Path) -> list[tuple[str, str]]:
    """
    Returns (source_name, content) pairs.

    - rag/*.md are treated as user-editable seed truth
    - backend/agent.py SYSTEM_PROMPT is ingested so your long prompt is always searchable
    """
    sources: list[tuple[str, str]] = []
    rag_dir = repo_root / "rag"
    if rag_dir.exists():
        for p in sorted(rag_dir.glob("*.md")):
            content = p.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                sources.append((f"rag/{p.name}", content))

    agent_prompt = extract_system_prompt_from_agent_py(repo_root)
    if agent_prompt:
        sources.append(("backend/agent.py#SYSTEM_PROMPT", agent_prompt))
    return sources


def chunk_markdown(source: str, content: str, target_chars: int = 2400) -> list[RagChunk]:
    """
    Simple, robust chunking that:
    - splits on headings and blank lines
    - keeps chunks roughly under target_chars
    """
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

    out: list[RagChunk] = []
    for idx, c in enumerate(chunks):
        out.append(RagChunk(source=source, chunk_index=idx, content=c, content_hash=_sha256(c)))
    return out


def _vector_literal(vec: list[float]) -> str:
    # pgvector accepts: '[0.1, 0.2, ...]'
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


async def embed_texts_openai(texts: list[str]) -> list[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")

    model = DEFAULT_EMBED_MODEL
    dims = DEFAULT_EMBED_DIMS
    batch_size = int(os.getenv("OPENAI_EMBED_BATCH_SIZE", "20"))
    batch_sleep_s = float(os.getenv("OPENAI_EMBED_BATCH_SLEEP_S", "1.5"))
    max_attempts = int(os.getenv("OPENAI_EMBED_MAX_ATTEMPTS", "6"))
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        for batch_start in range(0, len(texts), batch_size):
            batch = texts[batch_start : batch_start + batch_size]
            payload: dict = {"model": model, "input": batch}
            if dims:
                payload["dimensions"] = dims

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
                raise RuntimeError(
                    f"Embedding batch {batch_start // batch_size + 1} failed after {max_attempts} attempts (persistent 429)"
                )

            if batch_start + batch_size < len(texts):
                await asyncio.sleep(batch_sleep_s)

    return all_embeddings


# ---------------------------------------------------------------------------
# Supabase REST API helpers  (replaces asyncpg — works through corporate firewalls)
# ---------------------------------------------------------------------------

def _supabase_url() -> str:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set (required for RAG storage/retrieval)")
    return url


def _supabase_key() -> str:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set (required for RAG storage/retrieval)")
    return key


def _rest_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def delete_source_chunks(user_id: str, source: str) -> None:
    base_url = _supabase_url()
    key = _supabase_key()
    endpoint = f"{base_url}/rest/v1/rag_documents"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(
            endpoint,
            headers=_rest_headers(key),
            params={"user_id": f"eq.{user_id}", "source": f"eq.{source}"},
        )
        resp.raise_for_status()


async def delete_chunk_indices(user_id: str, source: str, chunk_indices: list[int]) -> None:
    if not chunk_indices:
        return
    base_url = _supabase_url()
    key = _supabase_key()
    endpoint = f"{base_url}/rest/v1/rag_documents"
    in_list = ",".join(str(i) for i in sorted(set(chunk_indices)))
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        resp = await client.delete(
            endpoint,
            headers=_rest_headers(key),
            params={
                "user_id": f"eq.{user_id}",
                "source": f"eq.{source}",
                "chunk_index": f"in.({in_list})",
            },
        )
        resp.raise_for_status()


async def get_existing_hashes(user_id: str, source: str) -> dict[int, str]:
    """
    Read existing (chunk_index -> content_hash) for a single source.
    Used to avoid re-embedding unchanged chunks.
    """
    base_url = _supabase_url()
    key = _supabase_key()
    endpoint = f"{base_url}/rest/v1/rag_documents"
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        resp = await client.get(
            endpoint,
            headers=_rest_headers(key),
            params={
                "select": "chunk_index,content_hash",
                "user_id": f"eq.{user_id}",
                "source": f"eq.{source}",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        out: dict[int, str] = {}
        for r in rows:
            try:
                out[int(r["chunk_index"])] = str(r["content_hash"])
            except Exception:
                continue
        return out


async def upsert_chunks(user_id: str, chunks: list[RagChunk], embeddings: list[list[float]]) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    base_url = _supabase_url()
    key = _supabase_key()
    headers = {
        **_rest_headers(key),
        # merge-duplicates maps to ON CONFLICT DO UPDATE on the unique constraint
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    endpoint = f"{base_url}/rest/v1/rag_documents?on_conflict=user_id,source,chunk_index"

    rows = [
        {
            "user_id": user_id,
            "source": ch.source,
            "chunk_index": ch.chunk_index,
            "content": ch.content,
            "content_hash": ch.content_hash,
            "embedding": _vector_literal(emb),
        }
        for ch, emb in zip(chunks, embeddings)
    ]

    # PostgREST accepts batches; send all at once.
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(endpoint, headers=headers, content=json.dumps(rows).encode())
        resp.raise_for_status()

    return len(rows)


async def similarity_search(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    """
    Returns a list of dicts: {source, chunk_index, content, similarity}
    similarity is in [0..1] where higher is better (cosine similarity approx).
    """
    if not query.strip():
        return []

    q_emb = (await embed_texts_openai([query]))[0]

    base_url = _supabase_url()
    key = _supabase_key()
    headers = _rest_headers(key)
    endpoint = f"{base_url}/rest/v1/rpc/match_rag_documents"

    match_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.2"))
    payload = {
        "query_embedding": _vector_literal(q_emb),
        "match_threshold": match_threshold,
        "match_count": top_k,
        "p_user_id": user_id,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(endpoint, headers=headers, content=json.dumps(payload).encode())
        resp.raise_for_status()

    return resp.json()


def build_rag_context(results: Iterable[dict], max_chars: int = 2400) -> str | None:
    """
    Convert retrieval results into a compact context block.
    Hard-caps total characters to avoid token bloat.
    """
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
