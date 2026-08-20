

def calculate_confidence(**signals: float | None) -> float:
    weights = {"evidence_score": 0.30, "parser_score": 0.20, "model_score": 0.20, "validation_score": 0.20, "consistency_score": 0.10}
    available = [(weights[key], max(0.0, min(1.0, value))) for key, value in signals.items() if key in weights and value is not None]
    if not available:
        return 0.0
    return round(sum(weight * value for weight, value in available) / sum(weight for weight, _ in available), 4)


def confidence_level(score: float) -> str:
    return "high" if score >= 0.9 else "medium" if score >= 0.7 else "low"

