#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Live checks of stage 8D on the real Polish Stanza models (needs ~/models/stanza or
the Stanza resources directory; loads the pipeline once, ~10 s on CPU).

1. The staged run (processors one by one) gives exactly the same analysis as
   the whole pipeline in one call - so splitting tokenize+mwt / pos / lemma /
   depparse changes nothing, and MWT really runs (``bom`` -> ``bo`` + ``m``).
2. A timeout inside a long processor: the caller is released at the
   deadline, the metadata says ``abandoned``, the slot stays held, and
   ``close()`` waits for the thread before the slot is released.
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_nlp_stanza_provider import build_request  # noqa: E402  pylint: disable=wrong-import-position

from ai_platform.common.core.execution import (  # noqa: E402  pylint: disable=wrong-import-position
    ExecutionContext,
    ExecutionRecorder,
    RuntimePolicy,
)
from ai_platform.common.core.registry.plugin_registry import (  # noqa: E402  pylint: disable=wrong-import-position
    PluginRegistry,
)
from ai_platform.common.nlp.provider import (  # noqa: E402  pylint: disable=wrong-import-position
    NLPProviderLifecycle,
    NLPProviderTimeoutError,
    StanzaPolishProvider,
)
from ai_platform.common.nlp.provider.stanza_provider import (  # noqa: E402  pylint: disable=wrong-import-position
    PROVIDER_ID,
)

MWT_TEXT = "Zrobiłem to, bom musiał. Nań czekałem długo, a tyś nie przyszedł."
LONG_TEXT = " ".join(["Ala ma kota, a kot ma Alę i obydwoje mieszkają w Gdyni."] * 400)
VOLATILE = {"analysis_id", "provider", "created_at", "metadata"}


async def check_staged_equals_whole() -> None:
    provider = StanzaPolishProvider(use_gpu=False)
    provider.initialize()
    whole = await provider.analyze(build_request(MWT_TEXT))
    context = ExecutionContext.create("live")
    recorder = ExecutionRecorder(context)
    staged = await provider.analyze_in_context(build_request(MWT_TEXT), context, recorder)
    assert whole.analysis.model_dump(exclude=VOLATILE) == \
        staged.analysis.model_dump(exclude=VOLATILE), "staged run differs from whole pipeline"
    words = [t.text for t in staged.analysis.tokens if t.multiword_token_id]
    assert "bo" in words and "m" in words, f"MWT not expanded: {words}"
    stages = list(recorder.extra["stage_seconds"])
    assert stages[0] == "tokenize+mwt", stages
    print(f"STAGED == WHOLE, MWT EXPANDED {words[:6]}, STAGES {stages}: OK")


async def check_timeout_inside_processor() -> None:
    lifecycle = NLPProviderLifecycle(PluginRegistry())
    lifecycle.register(StanzaPolishProvider(use_gpu=False),
                       policy=RuntimePolicy(max_concurrency=1))
    await lifecycle.initialize(PROVIDER_ID)
    slot = f"nlp:{PROVIDER_ID}"
    started = time.monotonic()
    try:
        await lifecycle.analyze_with_context(PROVIDER_ID, build_request(LONG_TEXT),
                                             timeout_seconds=1.0)
        raise AssertionError("the long text finished within 1 s - make it longer")
    except NLPProviderTimeoutError as exc:
        released = time.monotonic() - started
        assert released < 2.0, released
        assert exc.execution_metadata.abandoned
        assert lifecycle.resources.slots_in_use(slot) == 1, "slot freed while Stanza runs"
    snapshot = await lifecycle.close(PROVIDER_ID)
    assert lifecycle.resources.slots_in_use(slot) == 0
    print(f"TIMEOUT INSIDE A PROCESSOR: CALLER FREED AFTER {released:.2f} s, ABANDONED, "
          f"SLOT HELD UNTIL THE END, CLOSE {snapshot.state.value.upper()} "
          f"AFTER {time.monotonic() - started:.1f} s: OK")


async def main() -> None:
    print("=" * 60)
    print("STANZA EXECUTION CONTRACT LIVE CHECKS (8D)")
    print("=" * 60)
    await check_staged_equals_whole()
    await check_timeout_inside_processor()
    print()
    print("ALL STANZA EXECUTION CONTRACT LIVE CHECKS PASSED: 2/2")


if __name__ == "__main__":
    asyncio.run(main())
