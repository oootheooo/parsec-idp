import pytest

from app.providers import MockExtractionProvider
from app.security import hash_password, validate_webhook_url, verify_password, webhook_signature
from app.services.confidence import calculate_confidence, confidence_level
from app.services.rules import evaluate
from app.services.schema_tools import apply_overrides, validate_processor_schema


def test_password_hashing():
    encoded = hash_password("correct horse battery staple")
    assert "correct horse" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_schema_validation_rejects_unsafe_features():
    validate_processor_schema({"type": "object", "properties": {"total": {"type": "number"}}})
    with pytest.raises(ValueError, match="root"):
        validate_processor_schema({"type": "string"})
    with pytest.raises(ValueError, match="Unsupported"):
        validate_processor_schema({"type": "object", "oneOf": [{"type": "string"}]})


def test_safe_rule_evaluation_and_confidence():
    data = {"subtotal": 100, "tax": 12, "total": 112}
    rule = {"op": "approx_equal", "left": {"op": "add", "args": [
        {"op": "path", "path": "$.subtotal"}, {"op": "path", "path": "$.tax"}]},
        "right": {"op": "path", "path": "$.total"}, "tolerance": .02}
    assert evaluate(rule, data) is True
    with pytest.raises(ValueError):
        evaluate({"op": "eval", "args": []}, data)
    score = calculate_confidence(evidence_score=1, parser_score=None, model_score=.8,
                                 validation_score=1, consistency_score=None)
    assert score == pytest.approx(.9429, abs=.001)
    assert confidence_level(score) == "high"


def test_override_application_preserves_raw():
    class Override:
        json_path = "$.total"
        override_value = 125
        action = "correct"
    raw = {"total": 100}
    effective = apply_overrides(raw, [Override()])
    assert raw == {"total": 100}
    assert effective == {"total": 125}


def test_webhook_signing_and_ssrf():
    assert webhook_signature("secret", "123", b"{}") == webhook_signature("secret", "123", b"{}")
    with pytest.raises(ValueError):
        validate_webhook_url("http://127.0.0.1/hook", allow_private=False)


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    provider = MockExtractionProvider()
    schema = {"type": "object", "properties": {"name": {"type": ["string", "null"]}}, "required": ["name"]}
    context = {"text": "Name: Acme", "pages": [{"blocks": [{"id": "p1_b1", "text": "Name: Acme"}]}]}
    first = await provider.extract(schema=schema, instructions="", document_context=context, config={})
    second = await provider.extract(schema=schema, instructions="", document_context=context, config={})
    assert first.data == second.data == {"name": None}
    assert first.field_evidence[0]["block_ids"] == ["p1_b1"]
