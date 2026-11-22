
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLP provider configuration v2."""

from pathlib import Path

from pydantic import ValidationError

from ai_platform.common.nlp.provider.configuration_v2 import (
    NLPDownloadPolicy,
    NLPProviderEngineConfigV2,
    NLPModelConfigV2,
    NLPRuntimeConfigV2,
    NLPProviderConfigurationV2,
)


def test_engine_configuration():
    config = NLPProviderEngineConfigV2(
        engine_name="stanza",
        options={
            "processors": "tokenize,pos,lemma",
            "tokenize_pretokenized": False,
        },
    )

    assert config.engine_name == "stanza"
    assert config.options["processors"] == "tokenize,pos,lemma"


def test_engine_unknown_field_rejected():
    try:
        NLPProviderEngineConfigV2(
            engine_name="stanza",
            unknown_setting=True,
        )
    except ValidationError:
        return

    raise AssertionError("Unknown engine field was accepted.")


def test_engine_secret_reference():
    config = NLPProviderEngineConfigV2(
        engine_name="remote",
        api_key_env="MY_NLP_API_KEY",
    )

    assert config.api_key_env == "MY_NLP_API_KEY"
    assert "MY_NLP_API_KEY" in str(config.model_dump())


def test_engine_invalid_secret_reference():
    try:
        NLPProviderEngineConfigV2(
            engine_name="remote",
            api_key_env="MY-SECRET",
        )
    except ValidationError:
        return

    raise AssertionError("Invalid environment variable name was accepted.")


def test_model_identity_by_model_id():
    config = NLPModelConfigV2(
        model_id="pl-core-news",
    )

    assert config.model_id == "pl-core-news"


def test_model_identity_by_package():
    config = NLPModelConfigV2(
        package="default",
    )

    assert config.package == "default"


def test_model_identity_requires_identifier():
    try:
        NLPModelConfigV2()
    except ValidationError:
        return

    raise AssertionError("Empty model identity was accepted.")


def test_model_directory_normalization():
    config = NLPModelConfigV2(
        package="default",
        model_dir="~/models/stanza",
    )

    assert isinstance(config.model_dir, Path)
    assert "~" not in str(config.model_dir)


def test_download_policy_default_is_never():
    config = NLPModelConfigV2(
        model_id="pl-core-news",
    )

    assert config.download_policy == NLPDownloadPolicy.NEVER


def test_download_policy_if_missing():
    config = NLPModelConfigV2(
        model_id="pl-core-news",
        download_policy=NLPDownloadPolicy.IF_MISSING,
    )

    assert config.download_policy == NLPDownloadPolicy.IF_MISSING


def test_download_policy_always():
    config = NLPModelConfigV2(
        model_id="pl-core-news",
        download_policy="always",
    )

    assert config.download_policy == NLPDownloadPolicy.ALWAYS


def test_model_unknown_field_rejected():
    try:
        NLPModelConfigV2(
            model_id="pl-core-news",
            implicit_download=True,
        )
    except ValidationError:
        return

    raise AssertionError("Unknown model field was accepted.")


def test_runtime_default():
    config = NLPRuntimeConfigV2()

    assert config.device == "auto"
    assert config.threads is None
    assert config.batch_size is None
    assert config.memory_limit_mb_hint is None
    assert config.allow_device_fallback is True


def test_runtime_cpu():
    config = NLPRuntimeConfigV2(device="cpu")

    assert config.device == "cpu"


def test_runtime_cuda():
    config = NLPRuntimeConfigV2(device="cuda:0")

    assert config.device == "cuda:0"


def test_runtime_cuda_index():
    config = NLPRuntimeConfigV2(device="cuda:12")

    assert config.device == "cuda:12"


def test_runtime_invalid_device():
    try:
        NLPRuntimeConfigV2(device="gpu")
    except ValidationError:
        return

    raise AssertionError("Invalid device was accepted.")


def test_runtime_invalid_cuda_device():
    try:
        NLPRuntimeConfigV2(device="cuda:x")
    except ValidationError:
        return

    raise AssertionError("Invalid CUDA device was accepted.")


def test_runtime_positive_limits():
    config = NLPRuntimeConfigV2(
        threads=8,
        batch_size=16,
        memory_limit_mb_hint=4096,
    )

    assert config.threads == 8
    assert config.batch_size == 16
    assert config.memory_limit_mb_hint == 4096


def test_runtime_zero_threads_rejected():
    try:
        NLPRuntimeConfigV2(threads=0)
    except ValidationError:
        return

    raise AssertionError("Zero threads was accepted.")


def test_runtime_unknown_field_rejected():
    try:
        NLPRuntimeConfigV2(
            device="cpu",
            max_memory_mb=1024,
        )
    except ValidationError:
        return

    raise AssertionError("Unknown runtime field was accepted.")


def test_complete_configuration():
    config = NLPProviderConfigurationV2(
        provider_id="stanza-pl",
        engine={
            "engine_name": "stanza",
            "options": {
                "processors": "tokenize,mwt,pos,lemma,depparse",
                "tokenize_pretokenized": False,
            },
        },
        model={
            "package": "default",
            "language": "pl",
            "model_dir": "~/models/stanza",
            "download_policy": "never",
        },
        runtime={
            "device": "cpu",
            "threads": 4,
            "batch_size": 1,
        },
    )

    assert config.provider_id == "stanza-pl"
    assert config.engine.engine_name == "stanza"
    assert config.model is not None
    assert config.model.package == "default"
    assert config.model.download_policy == NLPDownloadPolicy.NEVER
    assert config.runtime.device == "cpu"


def test_configuration_from_dict():
    data = {
        "provider_id": "stanza-pl",
        "engine": {
            "engine_name": "stanza",
            "options": {
                "processors": "tokenize,pos,lemma",
            },
        },
        "model": {
            "package": "default",
            "language": "pl",
        },
    }

    config = NLPProviderConfigurationV2.from_dict(data)

    assert config.provider_id == "stanza-pl"
    assert config.engine.options["processors"] == "tokenize,pos,lemma"


def test_configuration_to_dict():
    config = NLPProviderConfigurationV2(
        provider_id="stanza-pl",
        engine={
            "engine_name": "stanza",
        },
        model={
            "package": "default",
            "language": "pl",
        },
    )

    data = config.to_dict()

    assert data["provider_id"] == "stanza-pl"
    assert data["engine"]["engine_name"] == "stanza"
    assert data["model"]["package"] == "default"
    assert data["model"]["download_policy"] == "never"


def test_configuration_unknown_field_rejected():
    try:
        NLPProviderConfigurationV2(
            provider_id="stanza-pl",
            engine={"engine_name": "stanza"},
            unknown_field=True,
        )
    except ValidationError:
        return

    raise AssertionError("Unknown configuration field was accepted.")


def test_configuration_is_frozen():
    config = NLPProviderConfigurationV2(
        provider_id="stanza-pl",
        engine={"engine_name": "stanza"},
    )

    try:
        config.provider_id = "other-provider"
    except ValidationError:
        return

    raise AssertionError("Frozen configuration was modified.")


def test_engine_configuration_is_frozen():
    config = NLPProviderEngineConfigV2(
        engine_name="stanza",
    )

    try:
        config.engine_name = "other-engine"
    except ValidationError:
        return

    raise AssertionError("Frozen engine configuration was modified.")


def test_model_configuration_is_frozen():
    config = NLPModelConfigV2(
        model_id="pl-core-news",
    )

    try:
        config.model_id = "other-model"
    except ValidationError:
        return

    raise AssertionError("Frozen model configuration was modified.")


def test_runtime_configuration_is_frozen():
    config = NLPRuntimeConfigV2()

    try:
        config.device = "cpu"
    except ValidationError:
        return

    raise AssertionError("Frozen runtime configuration was modified.")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]

    passed = 0

    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION V2 TESTS")
    print("=" * 60)

    for test in tests:
        test()
        passed += 1
        print(f"{test.__name__}: OK")

    print("-" * 60)
    print(f"RESULT: {passed}/{len(tests)} PASSED")


if __name__ == "__main__":
    main()


