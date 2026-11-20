"""Métricas amostrais e avaliação temporal; nenhuma escolha é feita em 2024."""

import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)


def positive_probability(model, X):
    classes = list(model.classes_)
    if len(classes) != 2 or set(classes) != {0, 1}:
        raise ValueError("O modelo deve declarar classes binárias 0 e 1")
    scores = np.asarray(model.predict_proba(X))[:, classes.index(1)]
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Saídas preditivas inválidas")
    return scores


def binary_metrics(y, scores, threshold=0.5):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if y.ndim != 1 or scores.ndim != 1 or not np.isin(y, [0, 1]).all() or set(np.unique(y)) != {0, 1} or len(y) != len(scores):
        raise ValueError("A avaliação exige ambas as classes e tamanhos consistentes")
    y = y.astype(int)
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Scores inválidos")
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    precision, recall, _ = precision_recall_curve(y, scores, drop_intermediate=True)
    fpr, tpr, _ = roc_curve(y, scores)
    metrics = {"n": len(y), "positivos": int(y.sum()), "roc_auc": float(roc_auc_score(y, scores)),
               "pr_auc": float(average_precision_score(y, scores)), "average_precision": float(average_precision_score(y, scores)),
               "accuracy": float(accuracy_score(y, predicted)), "precision": float(precision_score(y, predicted, zero_division=0)),
               "recall": float(recall_score(y, predicted, zero_division=0)), "f1": float(f1_score(y, predicted, zero_division=0)),
               "specificity": float(tn / (tn + fp)), "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
               "brier": float(brier_score_loss(y, scores)), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "threshold": threshold}
    # As métricas acima usam todos os pontos; os gráficos usam até 500 por curva.
    def sampled(a, b):
        index = np.unique(np.linspace(0, len(a) - 1, min(len(a), 500)).astype(int))
        return {"x": a[index].tolist(), "y": b[index].tolist()}
    return metrics, {"roc": sampled(fpr, tpr), "pr": sampled(recall, precision)}


def calibration_metrics(y, scores, bins=10):
    """Concordância entre pontuação e frequência observada (calibração), sem escolher nada.

    - brier_prevalencia: Brier de prever a prevalência observada nos próprios dados (referência);
      brier_skill = 1 − brier/brier_prevalencia (> 0: melhor que a prevalência constante).
    - intercepto/inclinação de Cox: regressão logística de y no logit da pontuação (ideal 0 e 1;
      inclinação < 1 indica pontuações extremas demais, > 1 tímidas demais).
    - ECE: erro absoluto médio ponderado entre pontuação média e frequência observada em bins de quantis.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss
    y, p = np.asarray(y).astype(int), np.asarray(scores, dtype=float)
    if y.ndim != 1 or len(y) != len(p) or set(np.unique(y)) != {0, 1}:
        raise ValueError("A calibração exige ambas as classes e tamanhos consistentes")
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("Scores inválidos")
    prevalence = float(y.mean())
    brier = float(brier_score_loss(y, p))
    reference = prevalence * (1 - prevalence)
    intercept = slope = float("nan")
    if np.ptp(p) > 1e-12:
        clipped = np.clip(p, 1e-6, 1 - 1e-6)
        cox = LogisticRegression(C=np.inf, max_iter=1000).fit(np.log(clipped / (1 - clipped)).reshape(-1, 1), y)
        intercept, slope = float(cox.intercept_[0]), float(cox.coef_[0, 0])
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    index = np.zeros(len(p), dtype=int) if len(edges) < 2 else np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
    curve = {"media_prevista": [], "frequencia_observada": [], "n": []}
    ece = mce = 0.0
    for b in np.unique(index):
        mask = index == b
        predicted, observed = float(p[mask].mean()), float(y[mask].mean())
        curve["media_prevista"].append(predicted); curve["frequencia_observada"].append(observed); curve["n"].append(int(mask.sum()))
        ece += mask.mean() * abs(predicted - observed)
        mce = max(mce, abs(predicted - observed))
    metrics = {"n": len(y), "prevalencia_observada": prevalence, "media_prevista": float(p.mean()),
               "diferenca_media": float(p.mean() - prevalence), "brier": brier, "brier_prevalencia": reference,
               "brier_skill": float(1 - brier / reference), "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
               "intercepto_cox": intercept, "inclinacao_cox": slope, "ece": float(ece), "mce": float(mce), "bins": len(curve["n"])}
    return metrics, curve


def choose_threshold(y, scores):
    """Limiar que maximiza F1 em scores fora do fold (desenvolvimento); nunca usar dados de teste."""
    y, scores = np.asarray(y).astype(int), np.asarray(scores, dtype=float)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("A escolha do limiar exige ambas as classes")
    precision, recall, thresholds = precision_recall_curve(y, scores)
    precision, recall = precision[:-1], recall[:-1]
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(precision), where=(precision + recall) > 0)
    best = int(np.argmax(f1))
    return float(thresholds[best]), float(f1[best])


def paired_bootstrap(y, scores_a, scores_b, metrics=("roc_auc", "average_precision"), n=1000, seed=42, level=0.95):
    """IC percentil por bootstrap pareado (mesmas reamostras) para métricas de A, B e A − B."""
    functions = {"roc_auc": roc_auc_score, "average_precision": average_precision_score}
    y, a, b = np.asarray(y).astype(int), np.asarray(scores_a, dtype=float), np.asarray(scores_b, dtype=float)
    if not (len(y) == len(a) == len(b)):
        raise ValueError("Tamanhos inconsistentes no bootstrap")
    rng = np.random.default_rng(seed)
    draws = {m: {"A": [], "B": [], "delta": []} for m in metrics}
    for _ in range(n):
        index = rng.integers(0, len(y), len(y))
        if y[index].min() == y[index].max():
            continue
        for m in metrics:
            va, vb = functions[m](y[index], a[index]), functions[m](y[index], b[index])
            draws[m]["A"].append(va); draws[m]["B"].append(vb); draws[m]["delta"].append(va - vb)
    low, high = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    result = {}
    for m in metrics:
        for part, values in draws[m].items():
            values = np.asarray(values)
            result[f"{m}_{part}_ic_inf"] = float(np.percentile(values, low))
            result[f"{m}_{part}_ic_sup"] = float(np.percentile(values, high))
        result[f"{m}_delta_prop_positivo"] = float(np.mean(np.asarray(draws[m]["delta"]) > 0))
    result["reamostras_validas"] = len(draws[metrics[0]]["delta"])
    return result
