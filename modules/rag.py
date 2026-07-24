import config

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL = None


def get_model():
    global MODEL
    if MODEL is None:
        from sentence_transformers import SentenceTransformer

        MODEL = SentenceTransformer(MODEL_NAME, local_files_only=True)
    return MODEL


def split_text(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
    for start in range(0, len(cleaned), step):
        chunk = cleaned[start : start + config.CHUNK_SIZE].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def create_index(chunks: list[str]):
    if not chunks:
        return None

    try:
        import faiss
        import numpy as np

        embeddings = get_model().encode(chunks, convert_to_numpy=True)
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        index = faiss.IndexFlatIP(normalized.shape[1])
        index.add(normalized.astype("float32"))
        return index
    except Exception:
        # Keep the app usable even when the embedding model is unavailable offline.
        return None


def retrieve(query: str, index, chunks: list[str], k: int = config.TOP_K) -> list[str]:
    if not query or not chunks:
        return []

    if index is not None:
        try:
            import numpy as np

            query_vector = get_model().encode([query], convert_to_numpy=True)
            normalized = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)
            _, indices = index.search(normalized.astype("float32"), min(k, len(chunks)))

            results: list[str] = []
            for idx in indices[0]:
                if 0 <= idx < len(chunks):
                    results.append(chunks[idx])
            return results
        except Exception:
            pass

    query_terms = {term for term in query.lower().split() if term}
    scored_chunks = []
    for chunk in chunks:
        chunk_terms = set(chunk.lower().split())
        score = len(query_terms & chunk_terms)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    fallback_results = [chunk for score, chunk in scored_chunks if score > 0][:k]
    return fallback_results or chunks[: min(k, len(chunks))]
