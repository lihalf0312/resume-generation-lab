"""Actual trainable linear evaluator baseline; provenance is preserved, never HR by implication."""
import math
from .core import digest


def fit(examples, epochs=1000, learning_rate=0.05):
    if not examples or epochs < 1 or not 0 < learning_rate <= 1:
        raise ValueError("valid labelled examples and training parameters required")
    n = len(examples[0]["features"])
    if n == 0:
        raise ValueError("empty feature vector")
    for e in examples:
        if e.get("split") != "train" or not e.get("label_origin"):
            raise ValueError("only provenance-labelled train examples may be fitted")
        if len(e["features"]) != n or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in e["features"] + [e["score"]]):
            raise ValueError("finite aligned features and labels required")
    means = [sum(e["features"][i] for e in examples) / len(examples) for i in range(n)]
    scales = [max(1.0, max(abs(e["features"][i] - means[i]) for e in examples)) for i in range(n)]
    xs = [[1.] + [(x - m) / s for x, m, s in zip(e["features"], means, scales)] for e in examples]
    weights = [0.] * (n + 1)
    for _ in range(epochs):
        gradient = [0.] * len(weights)
        for x, e in zip(xs, examples):
            err = sum(w * v for w, v in zip(weights, x)) - e["score"]
            for i, value in enumerate(x):
                gradient[i] += err * value / len(examples)
        weights = [w - learning_rate * g for w, g in zip(weights, gradient)]
    return {"version": "linear-mse-v1", "weights": weights, "means": means, "scales": scales,
            "training_hash": digest(examples), "label_origins": sorted({e["label_origin"] for e in examples}),
            "n_train": len(examples), "hr_validated": False}


def predict(model, features):
    if len(features) != len(model["means"]) or not all(math.isfinite(x) for x in features):
        raise ValueError("feature mismatch")
    x = [1.] + [(v - m) / s for v, m, s in zip(features, model["means"], model["scales"])]
    return sum(w * v for w, v in zip(model["weights"], x))
