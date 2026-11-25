// AI Platform chat - browser side. No libraries, no build step.
// The server (backend/ui_layer/web/chat_server.py) streams the answer as
// Server-Sent Events over a POST response; fetch() + a stream reader parse it.
// All model text is inserted with textContent, never innerHTML (no HTML injection).
"use strict";

const $ = (id) => document.getElementById(id);
const conversation = [];          // {role, content} of the finished turns
let controller = null;            // AbortController of the running answer

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
}

function addMessage(role, text = "") {
  const box = document.createElement("article");
  box.className = `message ${role}`;
  const label = document.createElement("span");
  label.className = "role";
  label.textContent = role === "user" ? "Ty" : role === "error" ? "Błąd" : "Model";
  const body = document.createElement("div");
  body.textContent = text;
  box.append(label, body);
  $("conversation").append(box);
  box.scrollIntoView({ block: "end" });
  return { box, body };
}

function addDetails(box, title, lines) {
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = title;
  details.append(summary);
  for (const line of lines) {
    const pre = document.createElement("pre");
    pre.textContent = line;
    details.append(pre);
  }
  box.append(details);
}

function addMeta(box, text) {
  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = text;
  box.append(meta);
}

async function postJson(url, body) {
  const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                                      body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.status);
  return data;
}

async function loadMemory() {
  const list = $("memory-list");
  try {
    const response = await fetch("/api/memory");
    const data = await response.json();
    if (!response.ok) { $("memory-panel").hidden = true; $("use-memory").disabled = true; return; }
    $("memory-count").textContent = data.count;
    list.replaceChildren(...data.notes.map((note) => {
      const item = document.createElement("li");
      const text = document.createElement("span");
      text.textContent = note.text;
      const meta = document.createElement("small");
      meta.textContent = `${note.source}, ${note.created_utc}`;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Usuń";
      remove.setAttribute("aria-label", `Usuń notatkę: ${note.text.slice(0, 40)}`);
      remove.addEventListener("click", async () => { await postJson("/api/memory/delete", { id: note.id }); loadMemory(); });
      item.append(text, meta, remove);
      return item;
    }));
  } catch (error) {
    setStatus(`Nie mogę wczytać pamięci: ${error}`, true);
  }
}

async function loadModels() {
  setStatus("Wczytuję modele...");
  const select = $("model");
  const previous = select.value || localStorage.getItem("chat.model");
  try {
    const response = await fetch("/api/models");
    const { models } = await response.json();
    select.replaceChildren(...models.map((m) => new Option(`${m.name}  (${m.provider})`, m.id)));
    if (previous && models.some((m) => m.id === previous)) select.value = previous;
    const status = await (await fetch("/api/status")).json();
    const docs = status.documents.source;
    $("use-documents").disabled = !docs;
    setStatus(models.length
      ? `${models.length} modeli. Dokumenty: ${docs || "brak (serwer bez --documents)"}.`
      : "Brak modeli - czy Ollama / LocalAI działa?", !models.length);
  } catch (error) {
    setStatus(`Nie mogę wczytać modeli: ${error}`, true);
  }
}

function parseEvents(buffer, onEvent) {
  // SSE frames are separated by a blank line; returns the unparsed rest.
  const frames = buffer.split("\n\n");
  const rest = frames.pop();
  for (const frame of frames) {
    const data = frame.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5)).join("\n");
    if (data) onEvent(JSON.parse(data));
  }
  return rest;
}

async function send(question) {
  const model = $("model").value;
  if (!model) { setStatus("Wybierz model.", true); return; }
  localStorage.setItem("chat.model", model);
  addMessage("user", question);
  const messages = [...conversation, { role: "user", content: question }];
  const { box, body } = addMessage("assistant");
  const useTools = $("use-tools").checked;
  let answer = "";
  let reasoning = null;           // <pre> inside a "Rozumowanie" <details>, created on demand
  controller = new AbortController();
  $("send").disabled = true; $("stop").disabled = false;
  setStatus(useTools ? "Agent pracuje (narzędzia)..." : "Model odpowiada...");
  const started = performance.now();
  try {
    const response = await fetch("/api/chat", {
      method: "POST", signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model, messages, mode: useTools ? "agent" : "chat",
        use_documents: $("use-documents").checked,
        use_memory: $("use-memory").checked,
        temperature: Number($("temperature").value),
        max_seconds: Number($("max-seconds").value),
      }),
    });
    if (!response.ok) throw new Error((await response.json()).error || response.status);
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer = parseEvents(buffer + value, (event) => {
        if (event.type === "reasoning") {
          if (!reasoning) {
            const details = document.createElement("details");
            const summary = document.createElement("summary");
            summary.textContent = "Rozumowanie modelu";
            reasoning = document.createElement("pre");
            details.append(summary, reasoning);
            box.insertBefore(details, body);
          }
          reasoning.textContent += event.text;
          setStatus("Model rozumuje...");
        }
        else if (event.type === "delta") { answer += event.text; body.textContent = answer; box.scrollIntoView({ block: "end" }); }
        else if (event.type === "sources") {
          const dropped = event.below_min_score || [];
          addDetails(box, `Źródła (${event.sources.length}` +
            (dropped.length ? `, ${dropped.length} poniżej progu ${event.min_score}` : "") + ")",
            event.sources.map((s) => `${s.document_id}  score ${s.score}\n${s.text}`)
              .concat(dropped.map((s) => `[pominięte] ${s.document_id}  score ${s.score}\n${s.text}`)));
        }
        else if (event.type === "trace") addDetails(box, `Kroki agenta: ${event.steps.length}, narzędzia: ${event.tools_used.join(", ") || "brak"} (${event.stop_reason})`,
          event.steps.map((s) => `#${s.step} [${s.mode}] ${s.model_text}\n` +
            s.tool_calls.map((c) => `-> ${c.name}(${JSON.stringify(c.arguments)}) ${c.ok ? "=" : "BŁĄD"} ${c.result}`).join("\n")));
        else if (event.type === "finish") {
          const why = { loop: `przerwano: model się zapętlił ("${(event.timing || {}).loop_unit || ""}")`,
                        time_limit: `przerwano: limit czasu ${event.max_seconds} s`,
                        length: "przerwano: limit tokenów", stop: "koniec" }[event.finish_reason] || `koniec: ${event.finish_reason || "-"}`;
          const t = event.timing || {};
          addMeta(box, why + (event.usage && event.usage.completion_tokens ? `, tokeny: ${event.usage.completion_tokens}` : "") +
            (t.first_token_seconds !== undefined ? `, pierwszy token po ${t.first_token_seconds} s` : "") +
            (t.elapsed_seconds !== undefined ? `, generowanie ${t.elapsed_seconds} s` : ""));
          if (event.finish_reason === "loop" || event.finish_reason === "time_limit") box.classList.add("warning");
        }
        else if (event.type === "memory") {
          if (event.notes.length) addDetails(box, `Z pamięci (${event.notes.length})`,
            event.notes.map((n) => `[${n.id}] ${n.text}  (${n.match}, ${n.score})`));
        }
        else if (event.type === "context") addMeta(box, `kontekst: ~${event.prompt_tokens} z ${event.context_tokens} tokenów` +
          ` (${event.source}${event.trained ? `, model obsługuje ${event.trained}` : ""}), rezerwa na odpowiedź ${event.reserve_tokens}` +
          (event.dropped_messages ? `, starsze wiadomości poza oknem: ${event.dropped_messages}` +
            (event.summarized ? " (zastąpione streszczeniem)" : " (pominięte)") : ""));
        else if (event.type === "done") addMeta(box, `zapytanie ${event.received_utc} → odpowiedź ${event.finished_utc} (UTC), razem ${event.elapsed_seconds} s`);
        else if (event.type === "error") throw new Error(event.message);
      });
    }
    if (!answer) body.textContent = "(brak odpowiedzi)";
    if (useTools) loadMemory();  // the agent may have remembered or forgotten something
    conversation.push({ role: "user", content: question }, { role: "assistant", content: answer });
    setStatus(`Gotowe w ${((performance.now() - started) / 1000).toFixed(1)} s.`);
  } catch (error) {
    if (error.name === "AbortError") {
      setStatus("Zatrzymano.");
      if (answer) conversation.push({ role: "user", content: question }, { role: "assistant", content: answer });
    } else {
      box.classList.add("error");
      body.textContent = answer ? `${answer}\n\n${error.message}` : error.message;
      setStatus("Błąd odpowiedzi.", true);
    }
  } finally {
    controller = null;
    $("send").disabled = false; $("stop").disabled = true;
    $("question").focus();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadModels();
  loadMemory();
  $("memory-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = $("memory-text").value.trim();
    if (!text) return;
    try { await postJson("/api/memory", { text }); $("memory-text").value = ""; loadMemory(); }
    catch (error) { setStatus(`Nie zapisano notatki: ${error.message}`, true); }
  });
  $("refresh").addEventListener("click", loadModels);
  $("stop").addEventListener("click", () => controller && controller.abort());
  $("clear").addEventListener("click", () => {
    conversation.length = 0;
    $("conversation").replaceChildren();
    setStatus("Nowa rozmowa.");
  });
  $("composer").addEventListener("submit", (event) => {
    event.preventDefault();
    const question = $("question").value.trim();
    if (!question || controller) return;
    $("question").value = "";
    send(question);
  });
  $("question").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("composer").requestSubmit(); }
  });
});
