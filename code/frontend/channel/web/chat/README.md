# Browser chat (code/frontend/channel/web/chat)

Static page (HTML, CSS, plain JavaScript; no libraries, no build step) served by
`ai_platform.backend.ui_layer.web.chat_server`, which talks to the local model
servers through `backend/service_layer/macro/chat/chat_service.py`. The page
imports nothing from the backend; it only calls the HTTP API.

    python3 -m ai_platform.backend.ui_layer.web.chat_server      # then open http://127.0.0.1:8765/
    python3 -m ai_platform.backend.ui_layer.web.chat_server --documents ~/notes --embedder ollama:bge-m3

- Model: every chat model of Ollama (:11434) and LocalAI (:8081) that is running.
- "z dokumentami": RAG over the corpus fixed at server start (default: the
  fictional Nordwind corpus `demo:bilingual_qa`); the passages used are shown
  under "Źródła".
- "z narzędziami": the tool agent (calculator, unit converter, date, and
  `search_documents` with documents on); its steps are shown under
  "Kroki agenta". The agent sees only the last question.
- Stop interrupts the answer; "Nowa rozmowa" clears the history (kept only in
  the page - the server stores nothing).

Security: no authentication. The server listens on 127.0.0.1 only and refuses
another address without `--allow-remote`. Model text is inserted with
`textContent`, and the server sends a Content-Security-Policy that allows only
its own scripts and styles.
