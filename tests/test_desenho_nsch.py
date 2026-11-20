import numpy as np
from scipy.special import expit, logit

from mindscreen.desenho_nsch import regressao, resumo_proporcao, variancia_wr


def test_variancia_dois_estratos_com_unidades_fora_do_dominio():
    # Primeiro estrato: 3/2 * (1 + 0 + 1); segundo: 2 * (2,25 + 2,25).
    v = variancia_wr([2, 0, 1, 3, 0], np.array([0, 0, 0, 1, 1]), 2)
    assert v[0, 0] == 12


def test_regressao_saturada_confere_com_proporcoes_e_linearizacao_manual():
    grupo = np.array([0, 0, 1, 1, 0, 0, 1, 1, 0, 1])
    estrato = np.repeat([0, 1], 5)
    dominio = np.array([True] * 8 + [False, False])
    y = np.array([0, 1, 1, 0, 0, 1, 0, 1, 0, 0])
    pesos = np.array([1, 1, 3, 1, 2, 1, 1, 2, 7, 3], dtype=float)
    critico = 1.96
    a, b = dominio & (grupo == 0), dominio & (grupo == 1)
    pa, pb = np.average(y[a], weights=pesos[a]), np.average(y[b], weights=pesos[b])
    influencia = np.zeros(len(y))
    influencia[a] = -pesos[a] * (y[a] - pa) / (pesos[a].sum() * pa * (1 - pa))
    influencia[b] = pesos[b] * (y[b] - pb) / (pesos[b].sum() * pb * (1 - pb))
    var = sum(np.var(influencia[estrato == i], ddof=1) * 5 for i in range(2))
    x = np.column_stack([np.ones(dominio.sum()), grupo[dominio]])
    for fator in (1, 5):
        beta, limites, _ = regressao(x, y[dominio], pesos * fator, dominio, estrato, 2, critico)
        np.testing.assert_allclose(expit([beta[0], beta.sum()]), [pa, pb], atol=1e-8)
        np.testing.assert_allclose(limites[1], np.exp(logit(pb) - logit(pa) + critico * np.sqrt(var) * np.array([-1, 1])))
    assert resumo_proporcao(y, pesos, a, estrato, 2, critico)["estimativa"] == pa
