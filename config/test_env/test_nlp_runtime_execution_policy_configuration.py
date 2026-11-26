#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLP runtime execution policy configuration."""

from pydantic import ValidationError

from ai_platform.common.core.execution import RuntimePolicy
from ai_platform.common.nlp.provider.configuration_loader import (
    ENV_PREFIX,
    NLPProviderConfigurationLoader,
)
from ai_platform.common.nlp.provider.configuration_v2 import (
    NLPRuntimeConfigV2,
)
from ai_platform.common.nlp.provider.execution import (
    runtime_policy_from_nlp_config,
)


def _base_config():
    return {
        "provider_id": "stanza-pl",
        "engine": {
            "engine_name": "stanza",
        },
        "model": {
            "package": "default",
            "language": "pl",
        },
    }


def test_runtime_execution_limits_defaults():
    runtime = NLPRuntimeConfigV2()

    assert runtime.max_concurrency is None
    assert runtime.timeout_seconds is None
    assert runtime.queue_timeout_seconds is None


def test_runtime_execution_limits_validation():
    runtime = NLPRuntimeConfigV2(
        max_concurrency=3,
        timeout_seconds=120,
        queue_timeout_seconds=15,
    )

    assert runtime.max_concurrency == 3
    assert runtime.timeout_seconds == 120
    assert runtime.queue_timeout_seconds == 15


def test_boolean_is_not_accepted_as_max_concurrency():
    try:
        NLPRuntimeConfigV2(max_concurrency=True)
    except ValidationError:
        return

    raise AssertionError("Boolean max_concurrency was accepted")


def test_zero_max_concurrency_rejected():
    try:
        NLPRuntimeConfigV2(max_concurrency=0)
    except ValidationError:
        return

    raise AssertionError("Zero max_concurrency was accepted")


def test_zero_timeout_rejected():
    try:
        NLPRuntimeConfigV2(timeout_seconds=0)
    except ValidationError:
        return

    raise AssertionError("Zero timeout was accepted")


def test_infinite_timeout_rejected():
    try:
        NLPRuntimeConfigV2(timeout_seconds=float("inf"))
    except ValidationError:
        return

    raise AssertionError("Infinite timeout was accepted")


def test_nan_queue_timeout_rejected():
    try:
        NLPRuntimeConfigV2(queue_timeout_seconds=float("nan"))
    except ValidationError:
        return

    raise AssertionError("NaN queue timeout was accepted")


def test_environment_overrides():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}RUNTIME__MAX_CONCURRENCY": "4",
            f"{ENV_PREFIX}RUNTIME__TIMEOUT_SECONDS": "90.5",
            f"{ENV_PREFIX}RUNTIME__QUEUE_TIMEOUT_SECONDS": "12.25",
        },
    )

    assert config.runtime.max_concurrency == 4
    assert config.runtime.timeout_seconds == 90.5
    assert config.runtime.queue_timeout_seconds == 12.25


def test_invalid_float_environment_value_rejected():
    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}RUNTIME__TIMEOUT_SECONDS": "not-a-number",
            },
        )
    except ValueError:
        return

    raise AssertionError("Invalid timeout environment value was accepted")


def test_non_finite_environment_value_rejected():
    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}RUNTIME__TIMEOUT_SECONDS": "inf",
            },
        )
    except ValueError:
        return

    raise AssertionError("Infinite timeout environment value was accepted")


def test_runtime_policy_mapping():
    runtime = NLPRuntimeConfigV2(
        device="cpu",
        threads=4,
        batch_size=8,
        max_concurrency=3,
        timeout_seconds=120,
        queue_timeout_seconds=10,
        memory_limit_mb_hint=2048,
        allow_device_fallback=False,
    )

    policy = runtime_policy_from_nlp_config(runtime)

    assert isinstance(policy, RuntimePolicy)
    assert policy.device == "cpu"
    assert policy.max_threads == 4
    assert policy.batch_size == 8
    assert policy.max_concurrency == 3
    assert policy.timeout_seconds == 120
    assert policy.queue_timeout_seconds == 10
    assert policy.memory_limit_mb == 2048
    assert policy.allow_device_fallback is False


def test_runtime_policy_defaults_remain_unlimited():
    policy = runtime_policy_from_nlp_config(NLPRuntimeConfigV2())

    assert policy.max_concurrency is None
    assert policy.timeout_seconds is None
    assert policy.queue_timeout_seconds is None


def test_execution_limits_change_fingerprint():
    base = _base_config()

    first = NLPProviderConfigurationLoader.from_dict(
        {
            **base,
            "runtime": {
                "max_concurrency": 2,
                "timeout_seconds": 60,
            },
        },
        environ={},
    )

    second = NLPProviderConfigurationLoader.from_dict(
        {
            **base,
            "runtime": {
                "max_concurrency": 4,
                "timeout_seconds": 60,
            },
        },
        environ={},
    )

    assert first.fingerprint_sha256 != second.fingerprint_sha256


def test_identical_execution_limits_preserve_fingerprint():
    base = _base_config()
    runtime = {
        "max_concurrency": 2,
        "timeout_seconds": 60,
        "queue_timeout_seconds": 5,
    }

    first = NLPProviderConfigurationLoader.from_dict(
        {
            **base,
            "runtime": runtime,
        },
        environ={},
    )

    second = NLPProviderConfigurationLoader.from_dict(
        {
            **base,
            "runtime": dict(runtime),
        },
        environ={},
    )

    assert first.fingerprint_sha256 == second.fingerprint_sha256


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]

    passed = 0

    print("=" * 60)
    print("NLP RUNTIME EXECUTION POLICY CONFIGURATION TESTS")
    print("=" * 60)

    for test in tests:
        test()
        passed += 1
        print(f"{test.__name__}: OK")

    print("-" * 60)
    print(f"RESULT: {passed}/{len(tests)} PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

