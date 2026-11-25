
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for NLP provider YAML and environment configuration loader."""

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.common.nlp.provider.configuration_loader import (
    ENV_PREFIX,
    NLPConfigurationLoadError,
    NLPProviderConfigurationLoader,
)
from ai_platform.common.nlp.provider.configuration_v2 import (
    NLPDownloadPolicy,
)


def _base_config():
    return {
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
        "runtime": {
            "device": "cpu",
            "threads": 4,
            "batch_size": 1,
            "allow_device_fallback": True,
        },
    }


def test_load_from_dict():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={},
    )

    assert config.provider_id == "stanza-pl"
    assert config.engine.engine_name == "stanza"
    assert config.model is not None
    assert config.model.package == "default"
    assert config.runtime.device == "cpu"


def test_load_from_dict_with_default_environment():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={},
    )

    assert config.runtime.allow_device_fallback is True


def test_load_from_mapping_with_env_override():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}RUNTIME__DEVICE": "cuda:0",
        },
    )

    assert config.runtime.device == "cuda:0"


def test_env_overrides_yaml_values():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}PROVIDER_ID": "stanza-pl-env",
            f"{ENV_PREFIX}RUNTIME__THREADS": "8",
        },
    )

    assert config.provider_id == "stanza-pl-env"
    assert config.runtime.threads == 8


def test_env_integer_parsing():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}RUNTIME__THREADS": "12",
            f"{ENV_PREFIX}RUNTIME__BATCH_SIZE": "16",
            f"{ENV_PREFIX}RUNTIME__MEMORY_LIMIT_MB_HINT": "4096",
        },
    )

    assert config.runtime.threads == 12
    assert config.runtime.batch_size == 16
    assert config.runtime.memory_limit_mb_hint == 4096


def test_env_boolean_parsing():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}RUNTIME__ALLOW_DEVICE_FALLBACK": "false",
        },
    )

    assert config.runtime.allow_device_fallback is False


def test_env_boolean_parsing_is_case_insensitive():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}RUNTIME__ALLOW_DEVICE_FALLBACK": "TRUE",
        },
    )

    assert config.runtime.allow_device_fallback is True


def test_env_model_fields_create_optional_model():
    data = {
        "provider_id": "remote-nlp",
        "engine": {
            "engine_name": "remote",
        },
    }

    config = NLPProviderConfigurationLoader.from_dict(
        data,
        environ={
            f"{ENV_PREFIX}MODEL__MODEL_ID": "pl-model-v1",
            f"{ENV_PREFIX}MODEL__LANGUAGE": "pl",
        },
    )

    assert config.model is not None
    assert config.model.model_id == "pl-model-v1"
    assert config.model.language == "pl"


def test_env_download_policy_parsing():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}MODEL__DOWNLOAD_POLICY": "if_missing",
        },
    )

    assert config.model is not None
    assert config.model.download_policy == NLPDownloadPolicy.IF_MISSING


def test_env_api_key_env_is_only_a_reference():
    config = NLPProviderConfigurationLoader.from_dict(
        _base_config(),
        environ={
            f"{ENV_PREFIX}ENGINE__API_KEY_ENV": "MY_NLP_SECRET",
        },
    )

    assert config.engine.api_key_env == "MY_NLP_SECRET"


def test_unknown_env_variable_rejected():
    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}UNKNOWN_SETTING": "value",
            },
        )
    except NLPConfigurationLoadError as error:
        assert "unsupported environment variable" in str(error)
        return

    raise AssertionError("Unknown NLP environment variable was accepted")


def test_env_cannot_override_engine_options():
    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}ENGINE__OPTIONS__PROCESSORS": "tokenize",
            },
        )
    except NLPConfigurationLoadError as error:
        assert "unsupported environment variable" in str(error)
        return

    raise AssertionError("ENV override of engine.options was accepted")


def test_invalid_env_integer_rejected_without_value_disclosure():
    secret_like_value = "not-an-integer-secret"

    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}RUNTIME__THREADS": secret_like_value,
            },
        )
    except NLPConfigurationLoadError as error:
        message = str(error)
        assert "RUNTIME__THREADS" in message
        assert secret_like_value not in message
        return

    raise AssertionError("Invalid integer environment value was accepted")


def test_invalid_env_boolean_rejected():
    try:
        NLPProviderConfigurationLoader.from_dict(
            _base_config(),
            environ={
                f"{ENV_PREFIX}RUNTIME__ALLOW_DEVICE_FALLBACK": "yes",
            },
        )
    except NLPConfigurationLoadError as error:
        assert "ALLOW_DEVICE_FALLBACK" in str(error)
        return

    raise AssertionError("Ambiguous boolean environment value was accepted")


def test_pydantic_validation_error_is_sanitized():
    data = _base_config()
    secret_like_value = "private-input-marker"
    data["runtime"]["threads"] = secret_like_value

    try:
        NLPProviderConfigurationLoader.from_dict(
            data,
            environ={},
            source="test-config",
        )
    except NLPConfigurationLoadError as error:
        message = str(error)
        assert "test-config" in message
        assert "runtime.threads" in message
        assert secret_like_value not in message
        return

    raise AssertionError("Invalid configuration was accepted")


def test_unknown_yaml_field_rejected():
    data = _base_config()
    data["unknown_setting"] = "value"

    try:
        NLPProviderConfigurationLoader.from_dict(
            data,
            environ={},
        )
    except NLPConfigurationLoadError as error:
        assert "unknown_setting" in str(error)
        return

    raise AssertionError("Unknown configuration field was accepted")


def test_load_from_yaml():
    yaml_content = """
provider_id: stanza-pl
engine:
  engine_name: stanza
  options:
    processors: tokenize,pos,lemma
model:
  package: default
  language: pl
runtime:
  device: cpu
  threads: 4
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "nlp.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        config = NLPProviderConfigurationLoader.from_yaml(
            path,
            environ={},
        )

    assert config.provider_id == "stanza-pl"
    assert config.engine.options["processors"] == "tokenize,pos,lemma"
    assert config.runtime.threads == 4


def test_yaml_env_precedence():
    yaml_content = """
provider_id: stanza-pl
engine:
  engine_name: stanza
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "nlp.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        config = NLPProviderConfigurationLoader.from_yaml(
            path,
            environ={
                f"{ENV_PREFIX}PROVIDER_ID": "stanza-pl-overridden",
                f"{ENV_PREFIX}RUNTIME__DEVICE": "cpu",
            },
        )

    assert config.provider_id == "stanza-pl-overridden"
    assert config.runtime.device == "cpu"


def test_yaml_missing_file_rejected():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "missing.yaml"

        try:
            NLPProviderConfigurationLoader.from_yaml(
                path,
                environ={},
            )
        except NLPConfigurationLoadError as error:
            assert "does not exist" in str(error)
            return

    raise AssertionError("Missing YAML file was accepted")


def test_yaml_invalid_syntax_rejected():
    yaml_content = """
provider_id: stanza-pl
engine:
  engine_name: [invalid
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "invalid.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        try:
            NLPProviderConfigurationLoader.from_yaml(
                path,
                environ={},
            )
        except NLPConfigurationLoadError as error:
            assert "invalid YAML syntax" in str(error)
            return

    raise AssertionError("Invalid YAML syntax was accepted")


def test_yaml_empty_file_rejected():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "empty.yaml"
        path.write_text("", encoding="utf-8")

        try:
            NLPProviderConfigurationLoader.from_yaml(
                path,
                environ={},
            )
        except NLPConfigurationLoadError as error:
            assert "empty" in str(error)
            return

    raise AssertionError("Empty YAML file was accepted")


def test_yaml_non_mapping_root_rejected():
    yaml_content = """
- stanza
- remote
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "list.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        try:
            NLPProviderConfigurationLoader.from_yaml(
                path,
                environ={},
            )
        except NLPConfigurationLoadError as error:
            assert "root must be a mapping" in str(error)
            return

    raise AssertionError("Non-mapping YAML root was accepted")


def test_load_dispatches_mapping():
    config = NLPProviderConfigurationLoader.load(
        _base_config(),
        environ={},
    )

    assert config.provider_id == "stanza-pl"


def test_load_dispatches_yaml_path():
    yaml_content = """
provider_id: stanza-pl
engine:
  engine_name: stanza
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "nlp.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        config = NLPProviderConfigurationLoader.load(
            path,
            environ={},
        )

    assert config.provider_id == "stanza-pl"


def test_fingerprint_is_stable_across_sources():
    data = _base_config()

    mapping_config = NLPProviderConfigurationLoader.from_dict(
        data,
        environ={},
    )

    yaml_content = """
provider_id: stanza-pl
engine:
  engine_name: stanza
  options:
    processors: tokenize,pos,lemma
model:
  package: default
  language: pl
runtime:
  device: cpu
  threads: 4
  batch_size: 1
  allow_device_fallback: true
"""

    with TemporaryDirectory() as directory:
        path = Path(directory) / "nlp.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        yaml_config = NLPProviderConfigurationLoader.from_yaml(
            path,
            environ={},
        )

    assert (
        mapping_config.fingerprint_sha256
        == yaml_config.fingerprint_sha256
    )


def test_loaded_options_are_deeply_immutable():
    config = NLPProviderConfigurationLoader.from_dict(
        {
            "provider_id": "test",
            "engine": {
                "engine_name": "test-engine",
                "options": {
                    "nested": {
                        "items": [1, 2, 3],
                    },
                },
            },
        },
        environ={},
    )

    try:
        config.engine.options["nested"]["items"][0] = 99
    except TypeError:
        return

    raise AssertionError("Loaded engine options are mutable")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]

    passed = 0

    print("=" * 60)
    print("NLP PROVIDER CONFIGURATION LOADER TESTS")
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

