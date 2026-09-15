-- 兼容旧文件名：将向量列更新为模力方舟 bge-m3 的 1024 维

-- 1. 删除旧的向量列（会丢失已有向量数据）
ALTER TABLE resumes DROP COLUMN IF EXISTS text_embedding;
ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding;

-- 2. 添加新的 1024 维向量列
ALTER TABLE resumes ADD COLUMN text_embedding VECTOR(1024);
ALTER TABLE jobs ADD COLUMN description_embedding VECTOR(1024);

-- 3. 创建向量索引（可选，提升搜索性能）
-- 使用 IVFFlat 索引，适合中等规模数据
-- CREATE INDEX ON resumes USING ivfflat (text_embedding vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX ON jobs USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100);

-- 或使用 HNSW 索引，适合大规模数据
-- CREATE INDEX ON resumes USING hnsw (text_embedding vector_cosine_ops);
-- CREATE INDEX ON jobs USING hnsw (description_embedding vector_cosine_ops);
