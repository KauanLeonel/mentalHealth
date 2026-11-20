"""Classes persistidas nos artefatos calibrados.

Ficam num módulo próprio (e não em mindscreen.calibracao) para que o pickle registre
`mindscreen.modelo_calibrado.*` mesmo quando a calibração é executada com `python -m`.
"""

import numpy as np

from mindscreen.avaliacao import positive_probability

METODOS = ("nenhum", "sigmoide", "isotonica")
EPS = 1e-6


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


class Calibrador:
    """Transformação monotônica de pontuação em probabilidade estimada."""

    def __init__(self, metodo):
        if metodo not in METODOS:
            raise ValueError(f"Método de calibração desconhecido: {metodo}")
        self.metodo = metodo
        self.modelo_ = None

    def fit(self, scores, y):
        scores, y = np.asarray(scores, dtype=float), np.asarray(y).astype(int)
        if set(np.unique(y)) != {0, 1}:
            raise ValueError("A calibração exige ambas as classes")
        if self.metodo == "sigmoide":
            from sklearn.linear_model import LogisticRegression
            # Platt sobre o logit da pontuação, sem penalização.
            self.modelo_ = LogisticRegression(C=np.inf, max_iter=1000).fit(_logit(scores).reshape(-1, 1), y)
        elif self.metodo == "isotonica":
            from sklearn.isotonic import IsotonicRegression
            self.modelo_ = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip").fit(scores, y)
        return self

    def transform(self, scores):
        scores = np.asarray(scores, dtype=float)
        if self.metodo == "nenhum":
            return scores
        if self.modelo_ is None:
            raise ValueError("Calibrador não ajustado")
        if self.metodo == "sigmoide":
            return self.modelo_.predict_proba(_logit(scores).reshape(-1, 1))[:, list(self.modelo_.classes_).index(1)]
        return np.clip(self.modelo_.predict(scores), 0.0, 1.0)


class ModeloCalibrado:
    """Pipeline original seguido do calibrador; expõe o mesmo contrato do pipeline.

    `named_steps` é repassado ao pipeline base: o SHAP continua explicando a pontuação
    bruta (a calibração é monotônica e não altera a ordenação dos registros).
    """

    def __init__(self, base, calibrador):
        self.base = base
        self.calibrador = calibrador

    @property
    def classes_(self):
        return self.base.classes_

    @property
    def feature_names_in_(self):
        return self.base.feature_names_in_

    @property
    def named_steps(self):
        return self.base.named_steps

    def predict_proba(self, X):
        positive = self.calibrador.transform(positive_probability(self.base, X))
        classes = list(self.classes_)
        out = np.empty((len(positive), 2))
        out[:, classes.index(1)] = positive
        out[:, classes.index(0)] = 1 - positive
        return out
