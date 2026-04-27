BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE TABLE IF NOT EXISTS client_interest_embedding (
    client_id INT PRIMARY KEY REFERENCES client(client_id) ON DELETE CASCADE,
    embedding vector(384),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_movie_embedding ON movie
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_client_embedding ON client_interest_embedding
USING hnsw (embedding vector_cosine_ops);

COMMIT;
