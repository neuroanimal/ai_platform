"""RAGFlow RAG adapter (RAGFlow HTTP API, https://ragflow.io/docs).

RAGFlow is a server that parses, chunks and indexes documents itself. This
adapter uses its HTTP API:

    ingest   POST /api/v1/datasets                       (create dataset once)
             POST /api/v1/datasets/<id>/documents        (multipart upload)
             POST /api/v1/datasets/<id>/chunks           (start parsing)
    query    POST /api/v1/retrieval                      (chunks for a question)

and generates the answer with a platform LLM adapter (``llm``), so that the
answer step is the same as for every other RAG adapter. Parsing is
asynchronous on the server; ``wait_parsed`` polls the document list.

Configuration (on top of NativeRAGAdapter's shared keys):

    url                     RAGFlow server, default "http://127.0.0.1:9380"
    api_key / api_key_env   default env RAGFLOW_API_KEY
    dataset_id              use an existing dataset; else ``dataset_name``
                            (default "ai_platform") is created on first ingest
    wait_parsed             seconds to wait for parsing after ingest (default 120, 0 = no wait)

Not verified against a running RAGFlow here; unit tests use a fake server.
Responses follow RAGFlow's envelope ``{"code": 0, "data": ...}``.
Previously a stub returning a fabricated answer; the class name and the
RAGAdapter methods are unchanged.
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter, RAGError
from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError


class RAGFlowAdapter(NativeRAGAdapter):
    """RAG on a RAGFlow server's retrieval API."""

    STACK = "ragflow"

    def __init__(self):
        super().__init__()
        self._client: Optional[HttpJsonClient] = None
        self.dataset_id: Optional[str] = None
        self.dataset_name = "ai_platform"
        self.wait_parsed = 120.0

    def _setup(self, config: Dict[str, Any]) -> None:
        key = config.get("api_key") or os.environ.get(
            config.get("api_key_env") or "RAGFLOW_API_KEY")
        if not key:
            raise RAGError("ragflow: API key missing (RAGFLOW_API_KEY)")
        self._client = HttpJsonClient(config.get("url", "http://127.0.0.1:9380"),
                                      timeout=float(config.get("timeout", 120)),
                                      headers={"Authorization": f"Bearer {key}"})
        self.dataset_id = config.get("dataset_id")
        self.dataset_name = config.get("dataset_name", "ai_platform")
        self.wait_parsed = float(config.get("wait_parsed", 120))

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Upload each document as a text file, then start parsing."""
        self._require()
        for number, document in enumerate(documents):
            if not str(document.get("text", "")).strip():
                raise RAGError(f"document {number} needs a non-empty 'text'")
        dataset = self._dataset()
        ids = []
        for number, document in enumerate(documents):
            name = f"{document.get('id', f'doc{number}')}.txt"
            uploaded = self._upload(dataset, name, str(document["text"]).encode("utf-8"))
            ids.extend(item["id"] for item in uploaded)
        if ids:
            self._call("POST", f"/api/v1/datasets/{dataset}/chunks", {"document_ids": ids})
            self._wait(dataset, ids)

    def _retrieve(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        if not self.dataset_id:
            return []
        data = self._call("POST", "/api/v1/retrieval", {
            "question": question, "dataset_ids": [self.dataset_id],
            "page": 1, "page_size": top_k, "top_k": max(top_k, 64)})
        return [self.make_source(c.get("id"), c.get("similarity"),
                                 {"document_id": c.get("document_id"), "text": c.get("content", ""),
                                  "document_name": c.get("document_keyword")})
                for c in (data or {}).get("chunks", [])[:top_k]]

    def _teardown(self) -> None:
        self._client = None

    # -- helpers ------------------------------------------------------------

    def _dataset(self) -> str:
        if not self.dataset_id:
            self.dataset_id = self._call("POST", "/api/v1/datasets",
                                         {"name": self.dataset_name})["id"]
        return self.dataset_id

    def _wait(self, dataset: str, ids: List[str]) -> None:
        deadline = time.monotonic() + self.wait_parsed
        while time.monotonic() < deadline:
            docs = self._call("GET", f"/api/v1/datasets/{dataset}/documents?page_size=1024")
            states = {d["id"]: d.get("run") for d in (docs or {}).get("docs", [])}
            if all(states.get(i) in ("DONE", "FAIL", "CANCEL") for i in ids):
                failed = [i for i in ids if states.get(i) != "DONE"]
                if failed:
                    raise RAGError(f"ragflow: parsing failed for {failed}")
                return
            time.sleep(1.0)
        if self.wait_parsed:
            raise RAGError(f"ragflow: documents not parsed within {self.wait_parsed:.0f} s")

    def _call(self, method: str, path: str, payload: Any = None) -> Any:
        try:
            envelope = self._client.request(method, path, payload).data or {}
        except HttpJsonError as exc:
            raise RAGError(f"ragflow: {exc}") from exc
        if envelope.get("code", 0) != 0:
            raise RAGError(f"ragflow: {envelope.get('message', envelope)}")
        return envelope.get("data")

    def _upload(self, dataset: str, filename: str, content: bytes) -> List[Dict[str, Any]]:
        """multipart/form-data upload - the JSON client cannot do this."""
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n").encode()
        body += content + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            self._client.url(f"/api/v1/datasets/{dataset}/documents"), data=body, method="POST",
            headers={**self._client.headers,
                     "Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(request, timeout=self._client.timeout) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RAGError(f"ragflow: upload of {filename} failed: {exc}") from exc
        if envelope.get("code", 0) != 0:
            raise RAGError(f"ragflow: {envelope.get('message', envelope)}")
        return envelope.get("data") or []
