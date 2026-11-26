# code/common/core/execution — runtime execution contract (stage 8B)

One contract for running engine work, shared by every provider family of the
platform: NLP (Stanza today), OCR/HTR, speech, LLM. It answers six questions
the same way for all of them, so the architecture does not take the shape of
one engine's limits.

| # | Concern | Module | Contract |
|---|---|---|---|
| 1 | Execution context | `context.py` | `ExecutionContext`: execution/request/provider ids, parent for nested steps, absolute deadline, cancellation token, effective policy, frozen labels. `child()` never extends the deadline or loosens the policy. |
| 2 | Runtime policy | `policy.py` | `RuntimePolicy`: device (+ fallback), threads, batch size, concurrency, timeout, queue timeout, memory limit (hint unless `memory_limit_enforced`). `narrow()` = a request can only tighten a provider's policy. `from_runtime_config()` reads `NLPRuntimeConfigV2`. |
| 3 | Resource management | `resources.py` | `ResourceManager`: shared objects created once and reference-counted (`lease`), concurrency slots (`slot`), claims of process-global settings (`claim_setting`, e.g. `torch.set_num_threads`) with conflict detection. |
| 4 | Execution metadata | `metadata.py` | `ExecutionRecorder` filled by the adapter, frozen into `ExecutionMetadata`: device really used, threads, engine + version, queue and run time, outcome, error, `abandoned`, configuration fingerprint. |
| 5 | Cancellation / timeout | `cancellation.py`, `executor.py` | `CancellationToken` (set once, callbacks, child tokens). `execute()` enforces the deadline for the caller; work stops cooperatively at `context.check()`. |
| 6 | Error propagation | `errors.py`, `executor.py` | Engine/provider errors keep their type; the execution layer raises only cancellation, timeout, policy, resource errors; every error leaving `execute()` carries `execution_metadata`; `ErrorInfo.from_exception()` describes any error as data (duck-typed `code`, `retryable`, `details`). |

## The honest part: what cannot be enforced in-process

- **A thread cannot be killed.** An engine that makes one long blocking call
  (a Stanza pipeline over the whole text, an OCR page) cannot be stopped in the
  middle. `execute()` releases the *caller* at the deadline, gives the worker
  `stop_grace_seconds` to stop at its next `context.check()`, and otherwise
  reports `abandoned=True`. The concurrency slot stays held until the thread
  really ends, so `max_concurrency` stays true.
- **Memory limits are hints.** Python cannot cap the memory of a library in
  the same process; a real limit needs a separate process (a later stage).
- **Thread settings are often process-global** (PyTorch). Two providers with
  different `threads` would overwrite each other; `claim_setting` turns that
  into a `ResourceConflictError`.

## How a provider adopts it (next stages, not done in 8B)

- **8C — lifecycle integration:** `NLPProviderLifecycle.analyze(provider_id, request,
  context=None)` creates a context from the provider's policy narrowed by the
  request, runs the provider through `execute()` with `slot_key=provider_id`,
  and returns the response together with `ExecutionMetadata` (e.g. in
  `NLPProviderResponse` diagnostics or a new metadata field). Providers that
  accept a context implement `analyze(request, context, recorder)`; old ones
  keep working (the lifecycle checks context at its own boundaries only).
- **8D — Stanza:** check the context between sentences/batches instead of one
  call over the whole text; claim `torch.num_threads`; lease the pipeline per
  (language, processors, package) key; record device and version. Then run
  `conformance.check_execution_conformance` in its tests.
- **OCR/HTR and speech** reuse the same steps with their own keys.

`conformance.py` gives each provider a ready check: cancellation honoured,
deadline honoured, metadata reported, error types kept.
