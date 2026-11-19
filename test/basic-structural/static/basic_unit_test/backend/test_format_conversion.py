"""Unit tests of FormatConversionService.validate_conversion (JSON <-> YAML)."""

import json

from ai_platform.backend.service_layer.format_processing.conversion.format_conversion_service import (
    FormatConversionService,
)

DATA = {"name": "Mruczek", "mammal": True, "ports": [8080, 8081], "nested": {"a": None}}


def test_round_trip_validates(tmp_path):
    service = FormatConversionService("Test", "1")
    source = tmp_path / "in.json"
    source.write_text(json.dumps(DATA), encoding="utf-8")
    target = tmp_path / "out.yaml"
    assert service.convert_file(str(source), str(target))
    assert service.validate_conversion(str(source), str(target)) is True
    back = tmp_path / "back.json"
    assert service.convert_file(str(target), str(back))
    assert service.validate_conversion(str(target), str(back)) is True


def test_changed_data_fails_and_unsupported_pair_is_not_a_pass(tmp_path):
    service = FormatConversionService("Test", "1")
    source = tmp_path / "in.json"
    source.write_text(json.dumps(DATA), encoding="utf-8")
    target = tmp_path / "out.yaml"
    target.write_text("name: Burek\n", encoding="utf-8")
    assert service.validate_conversion(str(source), str(target)) is False
    assert service.validate_conversion(str(source), str(tmp_path / "x.csv")) is False
