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
        temperature: Number($("temperature").value),
      }),
    });
    if (!response.ok) throw new Error((await response.json()).error || response.status);
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer = parseEvents(buffer + value, (event) => {
        if (event.type === "delta") { answer += event.text; body.textContent = answer; box.scrollIntoView({ block: "end" }); }
        else if (event.type === "sources") addDetails(box, `Źródła (${event.sources.length})`,
          event.sources.map((s) => `${s.document_id}  score ${s.score}\n${s.text}`));
        else if (event.type === "trace") addDetails(box, `Kroki agenta: ${event.steps.length}, narzędzia: ${event.tools_used.join(", ") || "brak"} (${event.stop_reason})`,
          event.steps.map((s) => `#${s.step} [${s.mode}] ${s.model_text}\n` +
            s.tool_calls.map((c) => `-> ${c.name}(${JSON.stringify(c.arguments)}) ${c.ok ? "=" : "BŁĄD"} ${c.result}`).join("\n")));
        else if (event.type === "finish") addMeta(box, `koniec: ${event.finish_reason || "-"}` +
          (event.usage && event.usage.completion_tokens ? `, tokeny: ${event.usage.completion_tokens}` : ""));
        else if (event.type === "error") throw new Error(event.message);
      });
    }
    if (!answer) body.textContent = "(brak odpowiedzi)";
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
