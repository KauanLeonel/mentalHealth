"""Métricas amostrais e avaliação temporal; nenhuma escolha é feita em 2024."""

import numpy as np
from sklearn.metrics import (accuracy_score, auc, average_precision_score, balanced_accuracy_score,
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
               "pr_auc": float(average_precision_score(y, scores)), "pr_auc_trapezoidal": float(auc(recall[::-1], precision[::-1])), "average_precision": float(average_precision_score(y, scores)),
               "accuracy": float(accuracy_score(y, predicted)), "precision": float(precision_score(y, predicted, zero_division=0)),
               "recall": float(recall_score(y, predicted, zero_division=0)), "f1": float(f1_score(y, predicted, zero_division=0)),
               "specificity": float(tn / (tn + fp)), "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
               "brier": float(brier_score_loss(y, scores)), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "threshold": threshold}
    # As métricas acima usam todos os pontos; os gráficos usam até 500 por curva.
    def sampled(a, b):
        index = np.unique(np.linspace(0, len(a) - 1, min(len(a), 500)).astype(int))
        return {"x": a[index].tolist(), "y": b[index].tolist()}
    return metrics, {"roc": sampled(fpr, tpr), "pr": sampled(recall, precision)}
