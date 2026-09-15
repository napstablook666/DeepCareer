"""
模力方舟 Embedding 与 Rerank 服务封装。

模力方舟的接口兼容 OpenAI Embeddings API，重排接口使用
``POST /v1/rerank``。服务端只从环境变量读取令牌，不在日志中输出令牌。
"""
from __future__ import annotations

from numbers import Real
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx

from backend.config import settings


EmbeddingInput = Union[str, List[str]]


def _normalize_base_url(base_url: str) -> str:
    """将用户提供的站点地址规范化为 OpenAI 兼容的 /v1 根地址。"""
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("MAGIC_ARK_BASE_URL 不能为空")
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


class MagicArkEmbeddingService:
    """调用模力方舟生成向量并执行文本重排。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        rerank_model: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        configured_key = (
            api_key or settings.MAGIC_ARK_API_KEY or settings.OPENAI_API_KEY
        )
        if not configured_key or not configured_key.strip():
            raise RuntimeError(
                "未配置模力方舟 API 密钥，请设置 MAGIC_ARK_API_KEY"
            )

        self.base_url = _normalize_base_url(
            base_url or settings.MAGIC_ARK_BASE_URL
        )
        self.embedding_model = (
            embedding_model or settings.MAGIC_ARK_EMBEDDING_MODEL
        )
        self.rerank_model = rerank_model or settings.MAGIC_ARK_RERANK_MODEL
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {configured_key.strip()}",
                "Content-Type": "application/json",
            },
            timeout=settings.MAGIC_ARK_TIMEOUT,
        )

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行带有限重试的 JSON 请求，并保留服务端错误原因。"""
        attempts = max(1, settings.MAGIC_ARK_MAX_RETRIES + 1)
        last_error: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                response = self._client.post(path.lstrip("/"), json=payload)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    continue
                raise RuntimeError(
                    f"模力方舟请求失败（{path}）：{exc}"
                ) from exc

            if response.status_code >= 500 and attempt + 1 < attempts:
                last_error = RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:500]}"
                )
                continue

            if response.is_error:
                detail = response.text[:1000].strip() or "服务端未返回错误详情"
                raise RuntimeError(
                    f"模力方舟请求失败（{path}，HTTP {response.status_code}）：{detail}"
                )

            try:
                body = response.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"模力方舟请求失败（{path}）：响应不是有效 JSON"
                ) from exc

            if not isinstance(body, dict):
                raise RuntimeError(
                    f"模力方舟请求失败（{path}）：响应结构不是 JSON 对象"
                )
            return body

        raise RuntimeError(f"模力方舟请求失败（{path}）：{last_error}")

    def create_embedding(
        self, text: EmbeddingInput
    ) -> Union[List[float], List[List[float]]]:
        """创建单条或批量文本向量，返回与原服务兼容的列表格式。"""
        if isinstance(text, str):
            inputs: EmbeddingInput = text
            single = True
        else:
            inputs = list(text)
            single = False

        if not inputs:
            return []

        body = self._post(
            "/embeddings",
            {"model": self.embedding_model, "input": inputs},
        )
        data = body.get("data")
        expected_count = 1 if single else len(inputs)
        if not isinstance(data, list) or len(data) != expected_count:
            raise RuntimeError("模力方舟 Embedding 响应缺少完整 data 数组")

        ordered = sorted(data, key=lambda item: item.get("index", 0))
        embeddings: List[List[float]] = []
        for item in ordered:
            embedding = (
                item.get("embedding") if isinstance(item, dict) else None
            )
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("模力方舟 Embedding 响应包含无效向量")
            if len(embedding) != self.embedding_dimension:
                raise RuntimeError(
                    "模力方舟 Embedding 维度不匹配："
                    f"收到 {len(embedding)}，配置为 {self.embedding_dimension}"
                )
            if not all(isinstance(value, Real) for value in embedding):
                raise RuntimeError("模力方舟 Embedding 响应包含非数值元素")
            embeddings.append([float(value) for value in embedding])

        return embeddings[0] if single else embeddings

    def get_dimension(self) -> int:
        """返回模型向量维度配置。"""
        return self.embedding_dimension

    def rerank(
        self,
        query: str,
        documents: Sequence[str],
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """按查询对候选文档重排，返回包含原始下标和相关度的结果。"""
        if not query or not query.strip():
            raise ValueError("Rerank query 不能为空")
        normalized_documents = [str(document) for document in documents]
        if not normalized_documents:
            return []

        payload: Dict[str, Any] = {
            "model": self.rerank_model,
            "query": query,
            "documents": normalized_documents,
        }
        if top_n is not None:
            if top_n <= 0:
                return []
            payload["top_n"] = min(top_n, len(normalized_documents))

        body = self._post("/rerank", payload)
        results = body.get("results")
        if not isinstance(results, list):
            raise RuntimeError("模力方舟 Rerank 响应缺少 results 数组")

        normalized_results: List[Dict[str, Any]] = []
        for result in results:
            if not isinstance(result, dict):
                raise RuntimeError("模力方舟 Rerank 响应包含无效结果")
            index = result.get("index")
            score = result.get("relevance_score", result.get("score"))
            if not isinstance(index, int) or not 0 <= index < len(
                normalized_documents
            ):
                raise RuntimeError("模力方舟 Rerank 响应包含无效文档下标")
            if not isinstance(score, Real):
                raise RuntimeError("模力方舟 Rerank 响应包含无效相关度")
            normalized_results.append(
                {
                    "index": index,
                    "score": max(0.0, min(1.0, float(score))),
                    "relevance_score": float(score),
                    "document": result.get("document"),
                }
            )
        return normalized_results


_embedding_service: Optional[MagicArkEmbeddingService] = None


def get_embedding_service() -> MagicArkEmbeddingService:
    """获取模力方舟远程 Embedding/Rerank 单例。"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = MagicArkEmbeddingService()
    return _embedding_service


def create_embeddings(
    texts: EmbeddingInput, model: Optional[str] = None
) -> Dict[str, Any]:
    """返回 OpenAI Embeddings API 兼容结构，保留旧调用入口。"""
    service = get_embedding_service()
    values = [texts] if isinstance(texts, str) else list(texts)
    embeddings = service.create_embedding(values)
    return {
        "data": [
            {
                "embedding": embedding,
                "index": index,
                "object": "embedding",
            }
            for index, embedding in enumerate(embeddings)
        ],
        "model": model or service.embedding_model,
        "object": "list",
    }
