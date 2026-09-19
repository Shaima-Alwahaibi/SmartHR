from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_resume_vector_store(chunks):
    if not chunks:
        return None

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2)
    )

    matrix = vectorizer.fit_transform(chunks)

    return {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "matrix": matrix
    }


def search_resume_chunks(query, vector_store, top_k=4):
    if not vector_store:
        return []

    query_vector = vector_store["vectorizer"].transform([query])
    scores = cosine_similarity(query_vector, vector_store["matrix"])[0]

    ranked = sorted(
        list(enumerate(scores)),
        key=lambda x: x[1],
        reverse=True
    )

    results = []

    for index, score in ranked[:top_k]:
        if score > 0:
            results.append({
                "chunk": vector_store["chunks"][index],
                "score": round(float(score), 4)
            })

    return results