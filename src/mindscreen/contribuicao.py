"""Pesquisa 1: contribuição incremental do tempo de tela além de outras características de rotina.

Pergunta: qual é a contribuição incremental do tempo de tela, além de idade, sexo, sono, atividade física e
dificuldade com amizades, para a classificação exploratória de relatos atuais de ansiedade e depressão na NSCH?

Protocolo (configuração em configs/contribuicao.json; decisões em docs/contribuicao-incremental.md):
- validação deixando um ano fora (2020–2024): cada edição é prevista por modelos ajustados nas demais;
- todos os fatores de rotina são avaliados da mesma forma, para que o tempo de tela seja lido em contexto:
  isolado (base + fator contra base) e incremental (rotina completa contra rotina completa sem o fator);
- comparações pareadas nos mesmos registros; IC por bootstrap estratificado por ano;
- hiperparâmetros fixados antes da execução; nenhuma escolha é feita a partir destes resultados.
Nenhum modelo é persistido: o produto desta etapa é a medida de contribuição, não um classificador individual.
"""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

from mindscreen.dados_validados import TARGETS, load_dataset, safe_output

SAIDA_PADRAO = Path("reports/modelagem/v4_contribuicao")
ARQUIVOS = ("metricas.csv", "contribuicoes.csv", "perfil_rotina.csv", "contribuicao.json", "resumo_familias.json", "interpretacao.md")
ROTULOS = {"SCREENTIME": "tempo de tela", "HOURSLEEP": "sono", "PHYSACTIV": "atividade física",
           "MAKEFRIEND": "dificuldade com amizades", "SC_AGE_YEARS": "idade", "SC_SEX": "sexo",
           "depressao_atual": "depressão atual", "ansiedade_atual": "ansiedade atual"}
LIMITES = (
    "Associação e capacidade de ordenação não indicam causa: os dados são transversais e o tempo de tela pode ser consequência, e não causa, do relato.",
    "Os desfechos são relatos de responsáveis, nos Estados Unidos, sobre condições atuais informadas por profissionais; dependem de acesso a diagnóstico, recordação e disposição para informar.",
    "Os modelos não foram validados clinicamente nem para famílias brasileiras e não são usados para prever condições de pessoas no aplicativo.",
    "As categorias de tempo de tela são estimativas de um dia típico, informadas pelo responsável, e a redação do item mudou entre edições.",
    "Os intervalos reamostram registros e não incorporam estratos e conglomerados do desenho amostral; a AUC ponderada é apenas uma análise de sensibilidade.",
    "Os hiperparâmetros vêm de escolhas anteriores em 2020–2023, e 2024 já havia sido examinado em versões anteriores do protocolo; não há conjunto completamente cego.",
)


class BarraProgresso:
    """Barra de progresso em texto (sem dependências), compatível com PowerShell e terminais POSIX.

    Cada chamada `barra(mensagem)` marca o início de uma etapa; `definir_total` é chamado por `run`.
    """

    def __init__(self, stream=None, largura=30, relogio=time.monotonic):
        self.stream, self.largura, self.relogio = stream or sys.stderr, largura, relogio
        self.total, self.concluidas, self.inicio, self._ultimo = None, 0, None, 0

    def definir_total(self, total):
        self.total, self.concluidas, self.inicio = int(total), 0, self.relogio()

    @staticmethod
    def _tempo(segundos):
        segundos = int(round(segundos))
        return f"{segundos // 3600:d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"

    def _linha(self, mensagem):
        decorrido = self.relogio() - self.inicio
        fracao = self.concluidas / self.total if self.total else 0
        cheio = int(self.largura * fracao)
        restante = self._tempo(decorrido / self.concluidas * (self.total - self.concluidas)) if self.concluidas else "--:--:--"
        return (f"[{'#' * cheio}{'.' * (self.largura - cheio)}] {self.concluidas}/{self.total} ({fracao:4.0%}) "
                f"decorrido {self._tempo(decorrido)} | restante ~{restante} | {mensagem}")

    def _escrever(self, linha, final=False):
        self.stream.write("\r" + linha.ljust(self._ultimo) + ("\n" if final else ""))
        self.stream.flush()
        self._ultimo = len(linha)

    def __call__(self, mensagem):
        if self.total is None:
            self.definir_total(0)
        if self.inicio is not None and self._ultimo:
            self.concluidas = min(self.concluidas + 1, self.total)
        self._escrever(self._linha(mensagem))

    def concluir(self, mensagem="concluído"):
        self.concluidas = self.total
        self._escrever(self._linha(mensagem), final=True)


def total_etapas(config):
    """Ajustes (conjuntos × anos agrupados por conjunto) e comparações com bootstrap, por target e modelo."""
    return len(TARGETS) * len(config["modelos"]) * (len(conjuntos(config)) + len(comparacoes(config)))


def validar_config(config, manifest):
    aprovados = set(manifest["preditores_numericos"]) | set(manifest["preditores_categoricos"])
    base, fatores = list(config["base"]), list(config["fatores_rotina"])
    if not base or not fatores or set(base) & set(fatores) or len(set(fatores)) != len(fatores):
        raise ValueError("Base e fatores de rotina devem ser listas não vazias e disjuntas")
    if set(base) | set(fatores) != aprovados:
        raise ValueError("Base + fatores de rotina devem corresponder exatamente aos preditores aprovados no manifesto")
    if config["fator_foco"] not in fatores:
        raise ValueError("O fator em foco deve ser um dos fatores de rotina")
    if config["modelo_principal"] not in config["modelos"] or not set(config["modelos"]) <= {"logistic", "xgboost", "random_forest"}:
        raise ValueError("Modelos inválidos na configuração")
    if sorted(config["anos"]) != config["anos"] or len(config["anos"]) < 2:
        raise ValueError("A validação por ano exige ao menos dois anos em ordem")
    if not 0 < config["nivel_confianca"] < 1 or config["bootstrap"] < 1:
        raise ValueError("Bootstrap e nível de confiança inválidos")


def conjuntos(config):
    """Conjuntos de preditores comparados; nomes estáveis usados nas tabelas."""
    base, fatores = list(config["base"]), list(config["fatores_rotina"])
    sets = {"base": base}
    sets.update({f"base+{f}": base + [f] for f in fatores})
    sets["rotina_completa"] = base + fatores
    sets.update({f"rotina_completa-{f}": base + [x for x in fatores if x != f] for f in fatores})
    return sets


def comparacoes(config):
    rows = []
    for f in config["fatores_rotina"]:
        rows.append({"fator": f, "tipo": "isolado", "com": f"base+{f}", "sem": "base"})
        rows.append({"fator": f, "tipo": "incremental", "com": "rotina_completa", "sem": f"rotina_completa-{f}"})
    return rows


def auc_ponderada(y, scores, weights=None, grupos=None):
    """ROC AUC com pesos (empates contam 1/2); equivale a roc_auc_score(sample_weight=...).

    `grupos` é o retorno de np.unique(scores, return_inverse=True) e pode ser reutilizado no bootstrap.
    """
    y = np.asarray(y).astype(bool)
    w = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
    inverse, k = grupos if grupos is not None else _grupos(scores)
    pos = np.bincount(inverse, weights=w * y, minlength=k)
    neg = np.bincount(inverse, weights=w * ~y, minlength=k)
    total_pos, total_neg = pos.sum(), neg.sum()
    if total_pos <= 0 or total_neg <= 0:
        return float("nan")
    below = np.cumsum(neg) - neg
    return float((pos * (below + 0.5 * neg)).sum() / (total_pos * total_neg))


def _grupos(scores):
    unique, inverse = np.unique(np.asarray(scores, dtype=float), return_inverse=True)
    return inverse, len(unique)


def bootstrap_delta(y, com, sem, estratos=None, n=1000, seed=42, level=0.95):
    """IC percentil da diferença pareada de AUC (com − sem), reamostrando registros dentro de cada estrato."""
    y = np.asarray(y).astype(int)
    estratos = np.zeros(len(y)) if estratos is None else np.asarray(estratos)
    indices = [np.flatnonzero(estratos == s) for s in np.unique(estratos)]
    g_com, g_sem = _grupos(com), _grupos(sem)
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n):
        draw = np.concatenate([idx[rng.integers(0, len(idx), len(idx))] for idx in indices])
        w = np.bincount(draw, minlength=len(y)).astype(float)
        delta = auc_ponderada(y, com, w, g_com) - auc_ponderada(y, sem, w, g_sem)
        if np.isfinite(delta):
            deltas.append(delta)
    if not deltas:
        raise ValueError("Nenhuma reamostra válida no bootstrap")
    deltas = np.asarray(deltas)
    low, high = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return {"ic_inf": float(np.percentile(deltas, low)), "ic_sup": float(np.percentile(deltas, high)),
            "prop_delta_positivo": float((deltas > 0).mean()), "reamostras_validas": len(deltas)}


def prever_deixando_um_ano_fora(manifest, data, target, predictors, model_name, config):
    """Pontuações fora do ano: para cada edição, ajusta nas demais e prevê a edição deixada de fora."""
    from mindscreen.avaliacao import positive_probability
    from mindscreen.treinamento import make_pipeline
    scores = np.full(len(data), np.nan)
    params = {f"model__{k}": v for k, v in config["modelos"][model_name].items()}
    for year in config["anos"]:
        test = data["ano"].eq(year).to_numpy()
        train = ~test
        if not test.any() or data.loc[train, target].nunique() != 2:
            raise ValueError(f"{target}/{year}: treino ou teste sem as duas classes")
        pipe, features = make_pipeline(manifest, model_name, {"semente": config["semente"]}, predictors=predictors)
        pipe.set_params(**params)
        pipe.fit(data.loc[train, features], data.loc[train, target].astype(int))
        scores[test] = positive_probability(pipe, data.loc[test, features])
    if np.isnan(scores).any():
        raise ValueError("Registros sem pontuação: verifique os anos configurados")
    return scores


def _faixas(idades, faixas):
    rotulos = np.full(len(idades), "", dtype=object)
    for nome, (lo, hi) in faixas.items():
        rotulos[(idades >= lo) & (idades <= hi)] = nome
    return rotulos


def contribuicoes_alvo(manifest, data, target, config, scores_por_modelo=None, progresso=print):
    """Métricas por conjunto/ano e contribuições pareadas para um target (registros com target definido)."""
    from sklearn.metrics import average_precision_score, brier_score_loss
    y = data[target].astype(int).to_numpy()
    anos = data["ano"].to_numpy()
    pesos = data[config["peso_amostral"]].astype(float).to_numpy()
    faixas = _faixas(data["SC_AGE_YEARS"].astype(float).to_numpy(), config["faixas_etarias"])
    sets, metric_rows, contrib_rows = conjuntos(config), [], []
    level, n_boot = config["nivel_confianca"], config["bootstrap"]
    for model_name in config["modelos"]:
        scores = {}
        for set_name, predictors in sets.items():
            if scores_por_modelo is not None:
                scores[set_name] = scores_por_modelo[model_name][set_name]
            else:
                progresso(f"{target} / {model_name} / {set_name}")
                scores[set_name] = prever_deixando_um_ano_fora(manifest, data, target, predictors, model_name, config)
            for periodo in [*config["anos"], "todos"]:
                mask = np.ones(len(y), bool) if periodo == "todos" else anos == periodo
                metric_rows.append({"target": target, "modelo": model_name, "conjunto": set_name, "preditores": "+".join(predictors),
                                    "ano_avaliado": periodo, "n": int(mask.sum()), "positivos": int(y[mask].sum()),
                                    "roc_auc": auc_ponderada(y[mask], scores[set_name][mask]),
                                    "roc_auc_ponderada": auc_ponderada(y[mask], scores[set_name][mask], pesos[mask]),
                                    "average_precision": float(average_precision_score(y[mask], scores[set_name][mask])),
                                    "brier": float(brier_score_loss(y[mask], scores[set_name][mask]))})
        for comp in comparacoes(config):
            progresso(f"{target} / {model_name} / bootstrap {comp['fator']} ({comp['tipo']})")
            com, sem = scores[comp["com"]], scores[comp["sem"]]
            auc_com, auc_sem = auc_ponderada(y, com), auc_ponderada(y, sem)
            row = {"target": target, "modelo": model_name, **comp, "auc_com": auc_com, "auc_sem": auc_sem, "delta_auc": auc_com - auc_sem}
            row.update({f"delta_auc_{k}": v for k, v in bootstrap_delta(y, com, sem, anos, n_boot, config["semente"], level).items()})
            row["delta_auc_ponderada"] = auc_ponderada(y, com, pesos) - auc_ponderada(y, sem, pesos)
            row["delta_average_precision"] = float(average_precision_score(y, com) - average_precision_score(y, sem))
            por_ano = [auc_ponderada(y[anos == a], com[anos == a]) - auc_ponderada(y[anos == a], sem[anos == a]) for a in config["anos"]]
            row.update({f"delta_auc_{a}": d for a, d in zip(config["anos"], por_ano)})
            row["anos_delta_positivo"] = int(sum(d > 0 for d in por_ano))
            for nome in config["faixas_etarias"]:
                mask = faixas == nome
                row[f"delta_auc_faixa_{nome}"] = auc_ponderada(y[mask], com[mask]) - auc_ponderada(y[mask], sem[mask])
                ci = bootstrap_delta(y[mask], com[mask], sem[mask], anos[mask], n_boot, config["semente"], level)
                row[f"delta_auc_faixa_{nome}_ic_inf"], row[f"delta_auc_faixa_{nome}_ic_sup"] = ci["ic_inf"], ci["ic_sup"]
            contrib_rows.append(row)
    return metric_rows, contrib_rows


def perfil_rotina(frame, manifest, config):
    """Distribuição ponderada (estimativa pontual) de cada fator de rotina por faixa etária e período."""
    peso = config["peso_descritivo_periodo"]
    idades = frame["SC_AGE_YEARS"].astype(float).to_numpy()
    faixas = _faixas(idades, config["faixas_etarias"])
    rows = []
    periodos = [("2020–2024", np.ones(len(frame), bool), peso)] + [(str(a), frame["ano"].eq(a).to_numpy(), "FWC") for a in config["anos"]]
    for var in config["fatores_rotina"]:
        labels = manifest.get("rotulos", {}).get(var, {})
        for periodo, mask_periodo, coluna_peso in periodos:
            for nome in config["faixas_etarias"]:
                sub = frame.loc[mask_periodo & (faixas == nome), [var, coluna_peso]]
                valid = sub.loc[sub[var].notna()]
                total = float(valid[coluna_peso].sum())
                for code, group in valid.groupby(var):
                    rows.append({"variavel": var, "rotulo_variavel": ROTULOS[var], "periodo": periodo, "faixa_etaria": nome,
                                 "categoria": int(code), "rotulo_categoria": labels.get(str(int(code)), str(code)),
                                 "n_amostral": len(group), "n_nao_informado_faixa": int(sub[var].isna().sum()),
                                 "percentual_ponderado": 100 * float(group[coluna_peso].sum()) / total if total else float("nan"),
                                 "peso": coluna_peso})
    return pd.DataFrame(rows)


def _num(x, casas=3):
    return f"{x:.{casas}f}".replace(".", ",")


def resumo_familias(contrib, metrics, config):
    """Frases em linguagem simples montadas a partir dos números calculados (nenhum valor é digitado à mão)."""
    principal, foco = config["modelo_principal"], config["fator_foco"]
    blocos = []
    for target in TARGETS:
        inc = contrib.loc[contrib.target.eq(target) & contrib.modelo.eq(principal) & contrib.tipo.eq("incremental")]
        inc = inc.sort_values("delta_auc", ascending=False).reset_index(drop=True)
        row = inc.loc[inc.fator.eq(foco)].iloc[0]
        posicao = int(inc.index[inc.fator.eq(foco)][0]) + 1
        completo = metrics.loc[metrics.target.eq(target) & metrics.modelo.eq(principal) & metrics.conjunto.eq("rotina_completa") & metrics.ano_avaliado.eq("todos")].iloc[0]
        outros = [f"{ROTULOS[r.fator]}: {_num(r.delta_auc)}" for r in inc.itertuples() if r.fator != foco]
        inclui_zero = row.delta_auc_ic_inf <= 0 <= row.delta_auc_ic_sup
        frases = [
            f"Com idade, sexo e os demais fatores de rotina já considerados, acrescentar o {ROTULOS[foco]} mudou a ROC AUC em {_num(row.delta_auc)} "
            f"(IC {int(config['nivel_confianca'] * 100)}%: {_num(row.delta_auc_ic_inf)} a {_num(row.delta_auc_ic_sup)}).",
            f"Isso equivale a cerca de {_num(row.delta_auc * 100, 1)} ponto percentual na chance de o modelo ordenar um relato positivo acima de um negativo.",
            f"Na mesma comparação, a contribuição dos outros fatores foi — {'; '.join(outros)}. O {ROTULOS[foco]} ficou em {posicao}º lugar entre {len(inc)} fatores.",
            f"A diferença foi positiva em {int(row.anos_delta_positivo)} de {len(config['anos'])} edições avaliadas separadamente.",
            ("O intervalo inclui zero, então os dados não permitem afirmar que o tempo de tela acrescente algo além dos demais fatores."
             if inclui_zero else "O intervalo não inclui zero, mas o tamanho da diferença é o que importa: compare-o com o dos outros fatores."),
        ]
        blocos.append({"target": target, "rotulo": ROTULOS[target], "frases": frases, "delta_auc": float(row.delta_auc),
                       "ic": [float(row.delta_auc_ic_inf), float(row.delta_auc_ic_sup)], "posicao_entre_fatores": posicao,
                       "auc_rotina_completa": float(completo.roc_auc)})
    return {"pergunta": "Quanto o tempo de tela acrescenta, além de outras características da rotina, à ordenação de relatos atuais de ansiedade e depressão na NSCH?",
            "modelo": principal, "blocos": blocos, "limites": list(LIMITES),
            "mensagem_principal": "Tempo de tela é uma parte da rotina, observada junto com sono, atividade física e convivência. Os resultados descrevem padrões de uma pesquisa e não dizem o que acontece com uma criança específica."}


def interpretacao(payload, contrib):
    principal = payload["configuracao"]["modelo_principal"]
    linhas = ["# Contribuição incremental do tempo de tela (v4)", "", f"Pergunta: {payload['resumo']['pergunta']}", "",
              f"Protocolo: {payload['protocolo']}", "", "## Resultados (modelo principal: " + principal + ")", ""]
    for bloco in payload["resumo"]["blocos"]:
        linhas += [f"### {bloco['rotulo'].capitalize()}", "", *[f"- {f}" for f in bloco["frases"]], ""]
    linhas += ["## Tabela de contribuições incrementais", "", "| target | modelo | fator | ΔAUC | IC inf | IC sup | ΔAUC ponderada | anos > 0 |", "|---|---|---|---|---|---|---|---|"]
    for r in contrib.loc[contrib.tipo.eq("incremental")].itertuples():
        linhas.append(f"| {r.target} | {r.modelo} | {r.fator} | {r.delta_auc:.4f} | {r.delta_auc_ic_inf:.4f} | {r.delta_auc_ic_sup:.4f} | {r.delta_auc_ponderada:.4f} | {r.anos_delta_positivo} |")
    linhas += ["", "## Limites", "", *[f"- {l}" for l in LIMITES], ""]
    return "\n".join(linhas)


def run(manifest_path, config_path, output, progresso=print):
    manifest, frame = load_dataset(manifest_path)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    validar_config(config, manifest)
    for coluna in (config["peso_amostral"], config["peso_descritivo_periodo"]):
        if coluna not in frame.columns or frame[coluna].isna().any() or (frame[coluna] <= 0).any():
            raise ValueError(f"Peso {coluna} ausente ou inválido")
    output = safe_output(output)
    if any((output / name).exists() for name in ARQUIVOS):
        raise FileExistsError("Já existem resultados no destino; escolha outra pasta para preservá-los")
    frame = frame.loc[frame["ano"].isin(config["anos"])]
    if hasattr(progresso, "definir_total"):
        progresso.definir_total(total_etapas(config))
    metrics, contrib, populacao = [], [], {}
    for target in TARGETS:
        data = frame.loc[frame[target].notna()].reset_index(drop=True)
        populacao[target] = {"registros": len(data), "excluidos_target_ausente": int(frame[target].isna().sum()),
                             "positivos": int(data[target].sum()), "por_ano": {str(k): int(v) for k, v in data["ano"].value_counts().sort_index().items()}}
        m, c = contribuicoes_alvo(manifest, data, target, config, progresso=progresso)
        metrics += m
        contrib += c
    metrics, contrib = pd.DataFrame(metrics), pd.DataFrame(contrib)
    perfil = perfil_rotina(frame, manifest, config)
    resumo = resumo_familias(contrib, metrics, config)
    payload = {"dataset_sha256": manifest["sha256"], "criado_utc": datetime.now(timezone.utc).isoformat(), "configuracao": config,
               "conjuntos": conjuntos(config), "comparacoes": comparacoes(config), "populacao": populacao,
               "protocolo": ("Validação deixando um ano fora (cada edição de 2020–2024 prevista por modelos ajustados nas demais); "
                             "imputação e codificação ajustadas apenas no treino de cada partição; hiperparâmetros fixos definidos antes da execução; "
                             "comparações pareadas nos mesmos registros; ROC AUC das pontuações agrupadas fora do ano; "
                             "IC percentil por bootstrap de registros estratificado por ano, condicional aos modelos ajustados; "
                             "AUC ponderada por FWC como sensibilidade, sem variância de desenho complexo. Nenhum modelo é salvo."),
               "versoes": {p: version(p) for p in ("pandas", "numpy", "scikit-learn", "xgboost")},
               "resumo": resumo, "limites": list(LIMITES)}
    output.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output / "metricas.csv", index=False, encoding="utf-8-sig")
    contrib.to_csv(output / "contribuicoes.csv", index=False, encoding="utf-8-sig")
    perfil.to_csv(output / "perfil_rotina.csv", index=False, encoding="utf-8-sig")
    (output / "contribuicao.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "resumo_familias.json").write_text(json.dumps({"dataset_sha256": manifest["sha256"], **resumo}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "interpretacao.md").write_text(interpretacao(payload, contrib), encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/contribuicao.json"))
    parser.add_argument("--output", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--sem-barra", action="store_true", help="Imprime uma linha por etapa em vez da barra (útil em logs)")
    args = parser.parse_args(argv)
    progresso = (lambda m: print(m, flush=True)) if args.sem_barra else BarraProgresso()
    try:
        run(args.manifesto, args.config, args.output, progresso=progresso)
    except (FileNotFoundError, FileExistsError, ValueError, ImportError) as exc:
        if isinstance(progresso, BarraProgresso) and progresso._ultimo:
            progresso.stream.write("\n")
        parser.exit(1, f"Análise de contribuição não executada: {exc}\n")
    if isinstance(progresso, BarraProgresso):
        progresso.concluir()
    print(f"Resultados em {args.output}")


if __name__ == "__main__":
    main()
