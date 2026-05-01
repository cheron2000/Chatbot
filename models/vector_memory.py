"""Vector-based memory for semantic search through conversation history."""
import uuid
from datetime import datetime, timezone
from typing import Optional

import chromadb


class VectorMemory:
    """Manages vector embeddings for semantic conversation search."""

    def __init__(self, persist_directory: str = "./vector_db"):
        # PersistentClient replaces deprecated Client + Settings pattern
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Conversation history with semantic search"},
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a message to vector memory. Returns the message ID."""
        message_id = str(uuid.uuid4())
        self.collection.add(
            documents=[content],
            metadatas=[
                {
                    "session_id": session_id,
                    "role": role,
                    # Use UTC ISO timestamp for consistent sorting
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **(metadata or {}),
                }
            ],
            ids=[message_id],
        )
        return message_id

    def add_messages(self, session_id: str, messages: list[dict]) -> list[str]:
        """
        Batch-add multiple messages in a single round-trip.

        Each item in `messages` must have 'role' and 'content' keys and
        may optionally include 'metadata'.
        """
        ids, documents, metadatas = [], [], []
        ts = datetime.now(timezone.utc).isoformat()
        for msg in messages:
            ids.append(str(uuid.uuid4()))
            documents.append(msg["content"])
            metadatas.append(
                {
                    "session_id": session_id,
                    "role": msg["role"],
                    "timestamp": ts,
                    **(msg.get("metadata") or {}),
                }
            )
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        return ids

    def search_similar(
        self,
        query: str,
        session_id: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """Return messages semantically similar to `query`."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"session_id": session_id} if session_id else None,
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # zip is cleaner and avoids repeated index lookups
        return [
            {"content": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(docs, metas, distances)
        ]

    def get_session_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """Return all messages for a session, ordered by timestamp."""
        results = self.collection.get(
            where={"session_id": session_id},
            limit=limit,
        )

        messages = [
            {"content": doc, "metadata": meta, "id": mid}
            for doc, meta, mid in zip(
                results.get("documents", []),
                results.get("metadatas", []),
                results.get("ids", []),
            )
        ]
        messages.sort(key=lambda x: x["metadata"].get("timestamp", ""))
        return messages

    def delete_session(self, session_id: str) -> int:
        """Delete all messages for a session. Returns the count deleted."""
        results = self.collection.get(
            where={"session_id": session_id},
            include=[],  # fetch only IDs — skip documents & metadatas
        )
        ids = results.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    def get_relevant_context(
        self, query: str, session_id: str, n_results: int = 3
    ) -> str:
        """Return a formatted string of the most relevant past messages."""
        similar = self.search_similar(query, session_id, n_results)
        if not similar:
            return ""
        lines = ["Relevant context from previous conversation:"] + [
            f"{msg['metadata'].get('role', 'unknown').capitalize()}: {msg['content']}"
            for msg in similar
        ]
        return "\n".join(lines)

    def get_stats(self) -> dict:
        return {
            "total_messages": self.collection.count(),
            "collection_name": self.collection.name,
            "metadata": self.collection.metadata,
        }


class HybridMemory:
    """Combines short-term (recent) memory with long-term vector memory."""

    def __init__(
        self,
        vector_memory: VectorMemory,
        session_id: str,
        max_short_term: int = 10,
    ):
        self.vector_memory = vector_memory
        self.session_id = session_id
        self.max_short_term = max_short_term
        # Deque would be O(1) for trimming, but list is fine at this scale
        self._short_term: list[dict] = []

    def add_message(self, role: str, content: str) -> None:
        self._short_term.append({"role": role, "content": content})
        # Trim to window in one slice — avoids repeated list rebuilds
        if len(self._short_term) > self.max_short_term:
            self._short_term = self._short_term[-self.max_short_term :]
        self.vector_memory.add_message(self.session_id, role, content)

    def get_context_for_query(
        self, query: str, include_recent: bool = True
    ) -> list[dict]:
        """
        Return context messages for a query using a hybrid strategy.

        Recent messages come first; then semantically relevant older messages
        are appended (duplicates filtered by content identity).
        """
        context: list[dict] = list(self._short_term) if include_recent else []

        # Build a set of already-included content strings for O(1) lookup
        seen: set[str] = {msg["content"] for msg in context}

        relevant = self.vector_memory.search_similar(
            query, self.session_id, n_results=3
        )
        for msg in relevant:
            content = msg["content"]
            if content not in seen:
                context.append({"role": msg["metadata"]["role"], "content": content})
                seen.add(content)

        return context

    @property
    def short_term(self) -> list[dict]:
        """Read-only view of the current short-term window."""
        return list(self._short_term)

    def clear(self) -> None:
        self._short_term.clear()
        self.vector_memory.delete_session(self.session_id)