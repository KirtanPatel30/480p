from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(text):
    model = get_model()
    vec = model.encode([text])[0]
    return vec.tolist()

def embed_all_movies(conn):
    cur = conn.cursor()
    cur.execute("SELECT movie_id, title, description, original_language FROM movie")
    movies = cur.fetchall()
    model = get_model()
    for movie in movies:
        text = f"{movie[1]}. {movie[2] or ''} Language: {movie[3]}"
        vec = model.encode([text])[0].tolist()
        cur.execute(
            "UPDATE movie SET embedding = %s::vector WHERE movie_id = %s",
            (str(vec), movie[0])
        )
    conn.commit()

def embed_client_interests(conn, client_id, interests_text):
    vec = embed(interests_text)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO client_interest_embedding (client_id, embedding, updated_at)
        VALUES (%s, %s::vector, NOW())
        ON CONFLICT (client_id) DO UPDATE
        SET embedding = EXCLUDED.embedding, updated_at = NOW()
    """, (client_id, str(vec)))
    conn.commit()

def get_recommendations(conn, client_id, top_n=3):
    cur = conn.cursor()
    cur.execute("SELECT embedding FROM client_interest_embedding WHERE client_id = %s", (client_id,))
    row = cur.fetchone()
    if not row:
        return []
    cur.execute("""
        SELECT m.movie_id, m.title, m.description, m.original_language,
               1 - (m.embedding <=> %s::vector) AS similarity
        FROM movie m
        WHERE m.embedding IS NOT NULL
        ORDER BY m.embedding <=> %s::vector
        LIMIT %s
    """, (row[0], row[0], top_n))
    return cur.fetchall()
