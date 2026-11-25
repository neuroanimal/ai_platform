"""Small HTTP helper for OpenAI-compatible audio endpoints.

The opener is injectable so unit tests never touch the network. The default
opener is ``urllib``. API keys are sent as headers and are not copied into
error messages.
"""

import json
import urllib.error
import urllib.request
import uuid
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ai_platform.common.speech.speech_exception import SpeechResponseError


HeaderMap = Mapping[str, str]
Opener = Callable[[urllib.request.Request, float], Tuple[int, bytes]]


def urllib_opener(request: urllib.request.Request, timeout: float) -> Tuple[int, bytes]:
    """Perform one POST. HTTP error statuses are returned, not raised."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def post_json(url: str, payload: Dict, headers: HeaderMap, timeout: float,
              opener: Optional[Opener] = None) -> bytes:
    """POST a JSON body. Raises ``SpeechResponseError`` on HTTP 4xx/5xx."""
    body = json.dumps(payload).encode("utf-8")
    return _post(url, body, {**headers, "Content-Type": "application/json"}, timeout, opener)


def multipart_body(fields: Mapping[str, str],
                   files: Sequence[Tuple[str, str, bytes, str]]) -> Tuple[bytes, str]:
    """Encode ``fields`` and ``files`` (name, filename, content, content-type)."""
    boundary = "----aiplatformspeech" + uuid.uuid4().hex
    chunks: List[bytes] = []
    for key, value in fields.items():
        chunks.append(
            (f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
             f'{value}\r\n').encode("utf-8")
        )
    for key, filename, content, content_type in files:
        head = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        )
        chunks.append(head.encode("utf-8"))
        chunks.append(content)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def post_multipart(url: str, fields: Mapping[str, str],  # pylint: disable=too-many-arguments,too-many-positional-arguments
                   files: Sequence[Tuple[str, str, bytes, str]],
                   headers: HeaderMap, timeout: float,
                   opener: Optional[Opener] = None) -> bytes:
    """POST multipart form data."""
    body, boundary = multipart_body(fields, files)
    merged = {**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    return _post(url, body, merged, timeout, opener)


def _post(url: str, body: bytes, headers: HeaderMap, timeout: float,
          opener: Optional[Opener]) -> bytes:
    request = urllib.request.Request(
        url, data=body, headers=dict(headers), method="POST",
    )
    status, payload = (opener or urllib_opener)(request, timeout)
    if status >= 400:
        snippet = payload[:300]
        raise SpeechResponseError(f"HTTP {status} from {url}: {snippet!r}")
    return payload


def bearer(api_key: str) -> Dict[str, str]:
    """Authorization header plus a stable user agent."""
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "ai-platform-speech",
    }
