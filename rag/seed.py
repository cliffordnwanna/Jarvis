"""
Seed script — embeds all rag/*.md files into Supabase for RAG retrieval.
Run once after setting up Supabase and configuring .env.

Usage:
  cd <repo_root>
  python rag/seed.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from backend.rag import iter_rag_sources, chunk_markdown, embed_texts_openai, upsert_document

RAG_USER_ID = os.getenv("RAG_USER_ID", "default")


async def main():
    repo_root = Path(__file__).parent.parent
    sources = iter_rag_sources(repo_root)

    if not sources:
        print("No markdown sources found in rag/")
        return

    print(f"Seeding {len(sources)} sources for user_id={RAG_USER_ID}")

    for source_name, content in sources:
        chunks = chunk_markdown(source_name, content)
        if not chunks:
            continue

        print(f"  {source_name}: {len(chunks)} chunks")
        texts = [c.content for c in chunks]
        embeddings = await embed_texts_openai(texts)

        for chunk, embedding in zip(chunks, embeddings):
            await upsert_document(
                user_id=RAG_USER_ID,
                source=chunk.source,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
            )

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
