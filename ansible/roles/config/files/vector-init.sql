-- pgvector needs its extension before the analyst vector seed loads (the seed
-- declares columns as vector(1024)). docker-entrypoint-initdb.d runs this once
-- on a fresh DB.
CREATE EXTENSION IF NOT EXISTS vector;
