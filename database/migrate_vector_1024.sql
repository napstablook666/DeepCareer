-- 迁移脚本：将向量列更新为模力方舟 bge-m3 的 1024 维
-- 执行前请确认已配置 pgvector 扩展，并准备重新生成已有数据的向量。

ALTER TABLE resumes DROP COLUMN IF EXISTS text_embedding;
ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding;

ALTER TABLE resumes ADD COLUMN text_embedding VECTOR(1024);
ALTER TABLE jobs ADD COLUMN description_embedding VECTOR(1024);

-- 数据量较大时可在写入新向量后创建索引：
-- CREATE INDEX ON resumes USING hnsw (text_embedding vector_cosine_ops);
-- CREATE INDEX ON jobs USING hnsw (description_embedding vector_cosine_ops);
