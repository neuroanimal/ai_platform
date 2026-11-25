
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for the public NLP provider configuration loader API."""

from ai_platform.common.nlp.provider import (
    ENV_PREFIX,
    NLPConfigurationLoadError,
    NLPProviderConfigurationLoader,
    NLPProviderConfigurationV2,
)


def test_loader_is_exported():
    assert callable(NLPProviderConfigurationLoader.from_dict)


def test_loader_error_is_exported():
    assert issubclass(NLPConfigurationLoadError, ValueError)


def test_environment_prefix_is_exported():
    assert ENV_PREFIX == "AI_PLATFORM_NLP__"


def test_configuration_v2_is_available_from_public_api():
    assert NLPProviderConfigurationV2 is not None


def test_public_loader_returns_v2_configuration():
    configuration = NLPProviderConfigurationLoader.from_dict(
        {
            "provider_id": "public-api-test",
            "engine": {
                "engine_name": "test-engine",
            },
        },
        environ={},
    )

    assert isinstance(configuration, NLPProviderConfigurationV2)
    assert configuration.provider_id == "public-api-test"
    assert configuration.engine.engine_name == "test-engine"


def main():
    tests = [
        test_loader_is_exported,
        test_loader_error_is_exported,
        test_environment_prefix_is_exported,
        test_configuration_v2_is_available_from_public_api,
        test_public_loader_returns_v2_configuration,
    ]

    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION LOADER PUBLIC API TESTS")
    print("=" * 60)

    passed = 0

    for test in tests:
        test()
        print(f"{test.__name__}: OK")
        passed += 1

    print("-" * 60)
    print(f"RESULT: {passed}/{len(tests)} PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

