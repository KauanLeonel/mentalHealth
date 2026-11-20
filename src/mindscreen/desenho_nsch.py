"""Análise complementar de domínios NSCH por linearização de Taylor (WR)."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.stats import t

from mindscreen.dados_validados import TARGETS, load_dataset, safe_output
from mindscreen.harmonizacao import sha256

ANOS = (2020, 2021, 2022, 2023, 2024)
COLUNAS = ["HHID", "FIPSST", "STRATUM", "FWC", "SC_AGE_YEARS"]
DEMOG = ["SC_SEX", "ano"]
ROTINA = ["HOURSLEEP", "PHYSACTIV", "MAKEFRIEND"]
TELA = "SCREENTIME"


def juntar_desenho(frame, pasta, hashes):
    """Restaura as unidades fora do domínio e verifica os campos comuns."""
    arquivos = {}
    for path in Path(pasta).rglob("*.csv"):
        match = re.fullmatch(r"nsch_(202[0-4])e?_topical\.csv", path.name, re.IGNORECASE)
        if match:
            ano = int(match[1])
            if ano in arquivos:
                raise ValueError(f"Dois arquivos para {ano}")
            arquivos[ano] = path
    if set(arquivos) != set(ANOS) or set(hashes) != set(ANOS):
        raise ValueError("São necessários os cinco arquivos Topical vinculados ao manifesto")
    for ano in ANOS:
        if sha256(arquivos[ano]) != hashes[ano]:
            raise ValueError(f"CSV de {ano} não corresponde à fonte do manifesto")
    desenho = pd.concat([
        pd.read_csv(arquivos[ano], usecols=COLUNAS, dtype={x: str for x in COLUNAS[:3]}).assign(ano=ano)
        for ano in ANOS
    ], ignore_index=True)
    if (desenho[COLUNAS].isna().any().any() or (desenho.FWC <= 0).any()
            or not np.isfinite(desenho.FWC).all() or desenho.HHID.duplicated().any()):
        raise ValueError("Desenho inválido ou HHID não único entre edições")
    elegiveis = desenho.loc[desenho.SC_AGE_YEARS.between(6, 17)]
    comparacao = elegiveis.merge(frame, on=["ano", "HHID"], suffixes=("_csv", "_pq"), validate="1:1")
    if len(comparacao) != len(frame) or len(comparacao) != len(elegiveis):
        raise ValueError("CSV e Parquet têm domínios diferentes")
    for nome in COLUNAS[1:]:
        if not comparacao[f"{nome}_csv"].eq(comparacao[f"{nome}_pq"]).all():
            raise ValueError(f"Campo de desenho divergente: {nome}")
    return desenho.merge(frame.drop(columns=COLUNAS[1:]), on=["ano", "HHID"], how="left", validate="1:1")


def variancia_wr(influencia, estrato, n_estratos):
    """Uma linha por PSU. Inclui os zeros das unidades fora do domínio."""
    valores = np.asarray(influencia, dtype=float)
    if valores.ndim == 1:
        valores = valores[:, None]
    grupos = np.bincount(estrato, minlength=n_estratos)
    if (grupos <= 1).any():
        raise ValueError("Estrato com menos de duas unidades no desenho completo")
    soma = np.zeros((n_estratos, valores.shape[1]))
    np.add.at(soma, estrato, valores)
    centro = valores - (soma / grupos[:, None])[estrato]
    escala = (grupos / (grupos - 1))[estrato]
    return centro.T @ (centro * escala[:, None])


def resumo_proporcao(y, w, dominio, estrato, h, critico):
    peso_total = w[dominio].sum()
    p = float(w[dominio] @ y[dominio] / peso_total)
    linear = np.zeros(len(y))
    linear[dominio] = w[dominio] * (y[dominio] - p) / peso_total
    se = np.sqrt(variancia_wr(linear, estrato, h)[0, 0])
    limites = expit(logit(p) + np.array([-1, 1]) * critico * se / (p * (1 - p)))
    return {"n": int(dominio.sum()), "positivos": int(y[dominio].sum()), "estimativa": p,
            "ic95": limites.tolist(), "erro_padrao": float(se)}


def regressao(x, y, w, dominio, estrato, h, critico):
    """Pseudoverossimilhança e sanduíche a partir do escore por PSU."""
    pesos = w[dominio] / w[dominio].mean()

    def objetivo(beta):
        eta = x @ beta
        return pesos @ (np.logaddexp(0, eta) - y * eta), x.T @ (pesos * (expit(eta) - y))

    def hessiana(beta):
        p = expit(x @ beta)
        return x.T @ ((pesos * p * (1 - p))[:, None] * x)

    inicio = np.zeros(x.shape[1])
    inicio[0] = logit(np.average(y, weights=pesos))
    fit = minimize(objetivo, inicio, jac=True, hess=hessiana, method="trust-exact",
                   options={"gtol": 1e-7})
    grad = float(np.max(np.abs(objetivo(fit.x)[1])))
    if grad / len(y) > 1e-8 or not np.isfinite(fit.x).all():
        raise ValueError(f"Ajuste sem convergência. Gradiente máximo: {grad}")
    bread = hessiana(fit.x)
    inverse = np.linalg.solve(bread, np.eye(x.shape[1]))
    scores = np.zeros((len(w), x.shape[1]))
    scores[dominio] = x * (pesos * (y - expit(x @ fit.x)))[:, None]
    cov = inverse @ variancia_wr(scores, estrato, h) @ inverse
    se = np.sqrt(np.diag(cov))
    return fit.x, np.exp(np.column_stack([fit.x - critico * se, fit.x + critico * se])), float(np.linalg.cond(bread))


def ajustar(frame, target, colunas, dominio, w, estrato, h, critico):
    dados = frame.loc[dominio]
    categorias = pd.get_dummies(dados[colunas].astype(int).astype("category"), drop_first=True, dtype=float)
    if colunas != [TELA]:
        categorias["idade_centrada"] = dados.SC_AGE_YEARS.astype(float) - 12
    x = np.column_stack([np.ones(len(dados)), categorias.to_numpy()])
    beta, limites, condicao = regressao(x, dados[target].to_numpy(float), w, dominio, estrato, h, critico)
    centrado = x[:, 1:] - np.average(x[:, 1:], weights=w[dominio], axis=0)
    cov = centrado.T @ (centrado * w[dominio, None])
    escala = np.sqrt(np.diag(cov))
    correlacao = cov / np.outer(escala, escala)
    vifs = np.diag(np.linalg.inv(correlacao))
    return {"n": len(dados), "condicao_hessiana": condicao, "vif_maximo": float(vifs.max()),
            "coluna_vif_maximo": str(categorias.columns[vifs.argmax()]),
            "categorias": {nome.rsplit("_", 1)[1]: {"or": float(np.exp(beta[i])), "ic95": limites[i].tolist()}
                           for i, nome in enumerate(categorias, 1) if nome.startswith(TELA + "_")}}


def analisar(frame):
    estrato, niveis = pd.factorize(frame.FIPSST + ":" + frame.STRATUM)
    h = len(niveis)
    w = frame.FWC.to_numpy() / len(ANOS)
    critico = t.ppf(0.975, len(frame) - h)
    idade = frame.SC_AGE_YEARS.between(6, 17).to_numpy()
    elegiveis = frame.loc[idade].copy()
    perfil = []
    for ano, sub in elegiveis.groupby("ano"):
        perfil.append({"ano": int(ano), "n": len(sub), "idade_12_17": int(sub.SC_AGE_YEARS.ge(12).sum()),
                       "sexo_feminino": int(sub.SC_SEX.eq(2).sum()), "tela_4h": int(sub[TELA].eq(5).sum()),
                       "tela_conhecida": int(sub[TELA].notna().sum()),
                       "faltantes": {c: int(sub[c].isna().sum()) for c in [TELA, *ROTINA, *TARGETS]}})
    resultados = {}
    for target in TARGETS:
        y = frame[target].to_numpy(float, na_value=np.nan)
        conhecido = idade & frame[target].notna().to_numpy()
        tela = frame[TELA].to_numpy(float, na_value=np.nan)
        completo = conhecido & frame[[TELA, *DEMOG, *ROTINA]].notna().all(axis=1).to_numpy()
        dados = {"prevalencias": {
            str(c): resumo_proporcao(y, w, conhecido & (tela == c), estrato, h, critico) for c in range(1, 6)
        }, "estratos_etarios": {}, "modelos": {}}
        for minimo, maximo in ((6, 11), (12, 17)):
            faixa = frame.SC_AGE_YEARS.between(minimo, maximo).to_numpy()
            dados["estratos_etarios"][f"{minimo}-{maximo}"] = {
                str(c): resumo_proporcao(y, w, conhecido & faixa & (tela == c), estrato, h, critico)
                for c in (1, 5)}
        for nome, vars_, dominio in [
            ("bruto", [TELA], completo),
            ("demografico", [TELA, *DEMOG], completo),
            ("completo", [TELA, *DEMOG, *ROTINA], completo),
            ("sem_2024", [TELA, *DEMOG, *ROTINA], completo & frame.ano.lt(2024).to_numpy())
        ]:
            if nome == "sem_2024":
                janela = frame.ano.lt(2024).to_numpy()
                codigos, estratos = pd.factorize((frame.FIPSST + ":" + frame.STRATUM)[janela])
                graus = int(janela.sum()) - len(estratos)
                dados["modelos"][nome] = ajustar(frame.loc[janela], target, vars_, dominio[janela],
                                                w[janela] * 5 / 4, codigos, len(estratos), t.ppf(.975, graus))
            else:
                dados["modelos"][nome] = ajustar(frame, target, vars_, dominio, w, estrato, h, critico)
        resultados[target] = dados
    return {"anos": list(ANOS), "psus": len(frame), "estratos": h, "graus": len(frame) - h,
            "perfil_amostral": perfil, "desfechos": resultados}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", default="data/processed/manifesto.json")
    parser.add_argument("--dados", default="Dados")
    parser.add_argument("--saida", default="artigo/resultados_reproducao/desenho_nsch.json")
    args = parser.parse_args()
    manifesto, frame = load_dataset(args.manifesto)
    hashes = {fonte["ano"]: fonte["sha256"] for fonte in manifesto["fontes"]}
    resultado = analisar(juntar_desenho(frame, args.dados, hashes))
    resultado["dataset_sha256"] = manifesto["sha256"]
    resultado["csv_sha256"] = hashes
    destino = safe_output(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("x", encoding="utf-8") as stream:
        json.dump(resultado, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
