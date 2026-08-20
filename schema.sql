CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS doc_chunks (
    id         bigserial PRIMARY KEY,
    source     text NOT NULL,
    title      text NOT NULL,
    content    text NOT NULL,
    embedding  vector(768) NOT NULL
);

CREATE INDEX IF NOT EXISTS doc_chunks_embedding_idx
    ON doc_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS sample_orders (
    order_id    bigserial PRIMARY KEY,
    customer_id integer NOT NULL,
    status      text NOT NULL,
    amount      numeric(10,2) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO sample_orders (customer_id, status, amount, created_at)
SELECT (random()*200)::int + 1,
       (ARRAY['pending','paid','shipped','cancelled'])[(random()*3)::int + 1],
       (random()*500 + 10)::numeric(10,2),
       now() - (random()*180 || ' days')::interval
FROM generate_series(1, 5000);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_ro') THEN
        CREATE ROLE agent_ro LOGIN;
    END IF;
END $$;

ALTER ROLE agent_ro PASSWORD 'Abc1234567890123!';   -- setup.ps1의 RO_PASSWORD와 동일하게
ALTER ROLE agent_ro SET statement_timeout = '5s';
GRANT CONNECT ON DATABASE agentdb TO agent_ro;
GRANT USAGE ON SCHEMA public TO agent_ro;
GRANT SELECT ON doc_chunks, sample_orders TO agent_ro;