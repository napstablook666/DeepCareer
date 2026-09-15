from copy import deepcopy

from backend.config import settings
from backend.services.matcher_service import MatcherService
from backend.utils.embedding_service import MagicArkEmbeddingService


class FakeResponse:
    status_code = 200
    is_error = False
    text = ""

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, path, json):
        self.calls.append((path, json))
        if path == "embeddings":
            count = (
                len(json["input"]) if isinstance(json["input"], list) else 1
            )
            return FakeResponse(
                {
                    "data": [
                        {
                            "index": index,
                            "embedding": [0.1 + index]
                            * settings.EMBEDDING_DIMENSION,
                        }
                        for index in range(count)
                    ]
                }
            )
        return FakeResponse(
            {
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.2},
                ]
            }
        )


def test_magic_ark_embedding_and_rerank_contract():
    client = FakeClient()
    service = MagicArkEmbeddingService(api_key="test-key", client=client)

    embeddings = service.create_embedding(["resume", "job"])
    reranked = service.rerank("resume", ["job A", "job B"], top_n=2)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == settings.EMBEDDING_DIMENSION
    assert reranked[0]["index"] == 1
    assert client.calls[0][0] == "embeddings"
    assert client.calls[1][0] == "rerank"


def test_rerank_updates_match_score():
    client = FakeClient()
    service = MagicArkEmbeddingService(api_key="test-key", client=client)
    matcher = MatcherService.__new__(MatcherService)
    matcher.embedding_service = service
    details = {
        "dimension_scores": {
            "position": 80,
            "skills": 70,
            "experience": 60,
            "education": 50,
            "semantic": 0,
        },
        "weights": {
            "position": 0.3,
            "skills": 0.25,
            "experience": 0.2,
            "education": 0.15,
            "semantic": 0.1,
        },
    }
    matches = [
        {"match_score": 60, "match_details": deepcopy(details)},
        {"match_score": 61, "match_details": deepcopy(details)},
    ]

    result = matcher.apply_rerank("resume", matches, ["job A", "job B"])

    assert result[0]["match_details"]["rerank"]["score"] == 90.0
    assert result[0]["match_score"] > result[1]["match_score"]
