"""Harmonização NSCH baseada em regras documentadas, sem alterar as fontes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from mindscreen.auditoria import PRIORITY
from mindscreen.dados_validados import TARGETS, check_predictors, safe_output
from mindscreen.importacao import YEARS, discover

COMPONENTS = {"depressao_atual": ("K2Q32A", "K2Q32B"), "ansiedade_atual": ("K2Q33A", "K2Q33B")}
ADMIN = ["HHID", "FIPSST", "STRATUM", "FORMTYPE", "FWC"]
SPECIAL = {".L": "salto_logico_declarado", ".M": "resposta_invalida_declarada",
           ".N": "inaplicavel_declarado", ".D": "suprimido_confidencialidade"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(folder):
    folder = Path(folder)
    return {str(p.resolve()): sha256(p) for p in sorted(folder.rglob("*")) if p.is_file()} if folder.exists() else {}


def category(series, domain):
    """Retorna códigos inteiros anuláveis e motivo observável, sem adivinhar recusa."""
    import pandas as pd
    text = series.astype("string").fillna("").str.strip()
    number = pd.to_numeric(text, errors="coerce")
    valid = number.isin(domain)
    status = pd.Series("codigo_nao_documentado", index=series.index, dtype="string")
    status.loc[text.eq("") | text.eq(".")] = "ausente_sem_motivo_csv"
    for code, label in SPECIAL.items():
        status.loc[text.str.upper().eq(code)] = label
    status.loc[valid] = "respondido"
    return number.where(valid).astype("Int16"), status


def build_target(history, current, yes=1, no=2):
    """Histórico negativo usa o salto; inconsistências e incertezas ficam anuláveis."""
    import pandas as pd
    h, hs = category(history, [yes, no])
    c, cs = category(current, [yes, no])
    target = pd.Series(pd.NA, index=history.index, dtype="Int8")
    status = pd.Series("historico_indeterminado", index=history.index, dtype="string")
    positive_history = h.eq(yes).fillna(False)
    negative_history = h.eq(no).fillna(False)
    skipped = cs.isin(["ausente_sem_motivo_csv", "salto_logico_declarado"])
    negative_skip = negative_history & skipped
    negative_explicit = negative_history & c.eq(no).fillna(False)
    target.loc[negative_skip | negative_explicit] = 0
    status.loc[negative_skip] = "negativo_por_salto_logico"
    status.loc[negative_explicit] = "negativo_historico_e_atual"
    status.loc[negative_history & ~(negative_skip | negative_explicit)] = "resposta_inconsistente_ou_invalida"
    status.loc[positive_history] = "atual_indeterminado"
    for code, binary, label in [(yes, 1, "positivo_atual"), (no, 0, "negativo_atual")]:
        mask = positive_history & c.eq(code).fillna(False)
        target.loc[mask] = binary
        status.loc[mask] = label
    return target, status


def verify_edition(frame, year, rules):
    """Compara contagens e pesos publicados; não autentica o arquivo byte a byte."""
    import numpy as np
    import pandas as pd
    expected = rules["edicoes"][str(year)]
    required = set(ADMIN + ["SC_AGE_YEARS", "SC_SEX", "SCREENTIME", *[v for pair in COMPONENTS.values() for v in pair]])
    required.update(rules["preditores_numericos"] + rules["preditores_categoricos"])
    absent = required - set(frame.columns)
    if absent:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(absent)}")
    if len(frame) != expected["registros"]:
        raise ValueError("Número de registros difere da edição oficial")
    age = pd.to_numeric(frame["SC_AGE_YEARS"], errors="coerce")
    if not age.isin(range(18)).all():
        raise ValueError("Idade ausente, não inteira ou fora de 0–17")
    form = pd.Series(np.select([age.le(5), age.le(11)], ["T1", "T2"], default="T3"), index=frame.index)
    if not frame["FORMTYPE"].eq(form).all():
        raise ValueError("FORMTYPE não corresponde à faixa etária")
    if frame["HHID"].eq("").any() or frame["HHID"].duplicated().any():
        raise ValueError("HHID vazio ou duplicado dentro da edição")
    if not frame["STRATUM"].isin(["1", "2A"]).all() or not frame["FIPSST"].str.fullmatch(r"\d{2}").all():
        raise ValueError("Estrato ou código estadual inválido")
    weights = pd.to_numeric(frame["FWC"], errors="coerce")
    if not (np.isfinite(weights) & weights.gt(0)).all():
        raise ValueError("FWC ausente, não finito ou não positivo")
    sex, _ = category(frame["SC_SEX"], [1, 2])
    checks = []
    for code, n, total in zip([1, 2], expected["sexo_contagens"], expected["sexo_pesos"]):
        observed_n, observed_total = int(sex.eq(code).sum()), float(weights.loc[sex.eq(code)].sum())
        passed = observed_n == n and abs(observed_total - total) <= 1
        checks.append({"ano": year, "checagem": f"SC_SEX={code}", "n_observado": observed_n, "n_oficial": n,
                       "soma_FWC_observada": observed_total, "soma_FWC_oficial_arredondada": total, "aprovada": passed})
    screen, screen_status = category(frame["SCREENTIME"], [1, 2, 3, 4, 5])
    observed = [int(screen.isna().sum()), *[int(screen.eq(code).sum()) for code in range(1, 6)]]
    if observed != expected["screentime_contagens"] or screen_status.eq("codigo_nao_documentado").any():
        raise ValueError("Frequências de SCREENTIME diferem das frequências oficiais")
    if not all(check["aprovada"] for check in checks):
        raise ValueError("Frequências ou pesos por sexo divergem da publicação oficial (tolerância de arredondamento: 1)")
    return checks


def harmonize_frame(frame, year, rules):
    """Retém todos os elegíveis por idade; não faz imputação nem seleção pelo target."""
    import pandas as pd
    low, high = rules["faixa_etaria"]
    age = pd.to_numeric(frame["SC_AGE_YEARS"], errors="coerce")
    eligible = age.between(low, high)
    selected = frame.loc[eligible].copy()
    result = selected[ADMIN].copy()
    result["ano"] = year
    result["id_registro"] = str(year) + ":" + selected["HHID"].astype("string")
    result["SC_AGE_YEARS"] = age.loc[eligible].astype("Int8")
    result["FWC"] = pd.to_numeric(selected["FWC"], errors="raise")
    for name, domain in rules["dominios"].items():
        if name not in selected:
            result[name] = pd.Series(pd.NA, index=selected.index, dtype="Int16")
            result[name + "_status"] = "variavel_ausente_na_edicao"
            continue
        codes, status = category(selected[name], domain)
        if status.eq("codigo_nao_documentado").any():
            raise ValueError(f"{name}: categorias não documentadas: {selected.loc[status.eq('codigo_nao_documentado'), name].unique().tolist()}")
        result[name], result[name + "_status"] = codes, status
    components = selected[[v for pair in COMPONENTS.values() for v in pair]].copy()
    components.insert(0, "id_registro", result["id_registro"])
    components.insert(1, "ano", year)
    flow = []
    for target, (history, current) in COMPONENTS.items():
        result[target], result[target + "_status"] = build_target(selected[history], selected[current],
                                                                 rules["edicoes"][str(year)]["sim"], rules["edicoes"][str(year)]["nao"])
        for variable in [history, current]:
            _, components[variable + "_status"] = category(selected[variable], [1, 2])
        for decision, count in [("entrada_original", len(frame)), ("excluidos_fora_faixa_etaria", int((~eligible).sum())),
                                ("mantidos_faixa_etaria", len(selected)), ("target_indeterminado", int(result[target].isna().sum())),
                                ("target_determinado", int(result[target].notna().sum())), ("target_positivo", int(result[target].eq(1).sum())),
                                ("target_negativo", int(result[target].eq(0).sum())),
                                ("screentime_ausente_mantido", int(result["SCREENTIME"].isna().sum()))]:
            flow.append({"ano": year, "target": target, "decisao": decision, "registros": count})
    return result, components, flow


def availability(year, names, rules):
    rows = []
    for variable in PRIORITY:
        status, reason = "Disponível e compatível", "Domínio confirmado na lista oficial para a população de 6–17 anos"
        if variable not in names:
            status, reason = "Ausente", "Coluna ausente no CSV"
        elif variable in ["ENGAGECONCERN", "BODYIMAGE"]:
            status, reason = "Necessita revisão metodológica", "Não incluída nesta versão analítica; aplicabilidade e comparabilidade ainda não aprovadas"
        elif variable in ["SCREENTIME", "BULLIED_R", "BULLY"] or variable == "MAKEFRIEND" and year < 2022:
            status = "Disponível com diferenças"
            reason = "Ver diferenças de redação/documentação ou universo em docs/harmonizacao.md; categorias mantidas sem imputação"
        rows.append({"ano": year, "variavel": variable, "classificacao": status, "motivo": reason,
                     "preditor_inicial": variable in rules["preditores_numericos"] + rules["preditores_categoricos"]})
    return rows


def run(entrada, output, reports, config):
    import pandas as pd
    entrada, output, reports = Path(entrada).resolve(), safe_output(output), safe_output(reports)
    for destination in [output, reports]:
        if destination == entrada or entrada in destination.parents:
            raise ValueError("Saídas devem ficar fora da pasta de entrada")
    planned = [output / name for name in ["dataset.parquet", "componentes_targets.parquet", "dataset_depressao.parquet", "dataset_ansiedade.parquet", "manifesto.json"]]
    report_files = [reports / name for name in ["qualidade.json", "qualidade.md", "fluxo.csv", "faltantes.csv", "distribuicoes.csv", "disponibilidade.csv", "edicoes.csv"]]
    if any(p.exists() for p in planned + report_files):
        raise FileExistsError("Há saídas anteriores. Escolha novas pastas com --saida e --relatorios; arquivos existentes não serão sobrescritos")
    rules = json.loads(Path(config).read_text(encoding="utf-8"))
    check_predictors(rules["preditores_numericos"], rules["preditores_categoricos"])
    before = {**snapshot(entrada), **snapshot("data/raw")}
    frames, components, flows, reviews, edition_log, fingerprints = [], [], [], [], [], []
    sources = []
    candidates = [c for c in discover(entrada) if c.path.suffix.lower() == ".csv"]
    for year in YEARS:
        choices = [c for c in candidates if c.year == year and c.topical_hint]
        if len(choices) != 1:
            edition_log.append({"ano": year, "validado": False, "motivo": "Arquivo ausente" if not choices else "Mais de um candidato: seleção ambígua"})
            continue
        source = choices[0].path
        try:
            frame = pd.read_csv(source, dtype=str, keep_default_na=False, skip_blank_lines=False, encoding="utf-8-sig")
            checks = verify_edition(frame, year, rules)
            result, component, flow = harmonize_frame(frame, year, rules)
            frames.append(result)
            components.append(component)
            flows.extend(flow)
            reviews.extend(availability(year, frame.columns, rules))
            fingerprints.extend(checks)
            sources.append({"ano": year, "arquivo": str(source), "sha256": sha256(source), "enhanced_indicio_nome": choices[0].enhanced_hint,
                            "lista_oficial": rules["fontes"]["listas"].format(ano=year), "frequencias_oficiais": rules["fontes"]["frequencias"].format(ano=year)})
            edition_log.append({"ano": year, "validado": True, "motivo": "Esquema, categorias, frequência de SCREENTIME e contagens/pesos por sexo compatíveis com publicação oficial", "originais": len(frame), "analiticos": len(result)})
        except (ValueError, OSError, KeyError) as exc:
            edition_log.append({"ano": year, "validado": False, "motivo": str(exc)})
    reports.mkdir(parents=True, exist_ok=True)
    if not frames:
        (reports / "qualidade.json").write_text(json.dumps({"validado": False, "edicoes": edition_log}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise ValueError("Nenhuma edição passou na validação; consulte qualidade.json")
    dataset = pd.concat(frames, ignore_index=True)
    component_table = pd.concat(components, ignore_index=True)
    years = sorted(int(y) for y in dataset["ano"].unique())
    dataset["FWC_media_anual_periodo"] = dataset["FWC"] / len(years)
    if dataset["id_registro"].duplicated().any() or not dataset["SC_AGE_YEARS"].between(*rules["faixa_etaria"]).all():
        raise ValueError("Falha de integridade: identificador ou faixa etária")
    for name, domain in rules["dominios"].items():
        if not dataset[name].dropna().isin(domain).all():
            raise ValueError(f"Domínio inválido após harmonização: {name}")
    for target in TARGETS:
        if not dataset[target].dropna().isin([0, 1]).all():
            raise ValueError(f"Target inválido: {target}")
    after = {**snapshot(entrada), **snapshot("data/raw")}
    if before != after:
        raise ValueError("Arquivos de origem alterados durante a execução; validação interrompida")
    output.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(planned[0], index=False)
    component_table.to_parquet(planned[1], index=False)
    for target, path in zip(TARGETS, planned[2:4]):
        other = next(t for t in TARGETS if t != target)
        dataset.loc[dataset[target].notna()].drop(columns=[other, other + "_status"]).to_parquet(path, index=False)
    pd.DataFrame(flows).to_csv(reports / "fluxo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(reviews).to_csv(reports / "disponibilidade.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(edition_log).to_csv(reports / "edicoes.csv", index=False, encoding="utf-8-sig")
    missing_rows, distributions = [], []
    for year, group in dataset.groupby("ano"):
        for name in [*rules["dominios"], *TARGETS]:
            missing_rows.append({"ano": int(year), "variavel": name, "registros": len(group), "ausentes": int(group[name].isna().sum())})
            for value, count in group[name].value_counts(dropna=False).items():
                distributions.append({"ano": int(year), "variavel": name, "categoria": "ausente" if pd.isna(value) else int(value), "registros": int(count)})
    pd.DataFrame(missing_rows).to_csv(reports / "faltantes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(distributions).to_csv(reports / "distribuicoes.csv", index=False, encoding="utf-8-sig")
    limitations = ["Validação técnica automatizada; não é aprovação científica por orientador nem autenticação byte a byte do PUF original.",
                   "CSV não preserva necessariamente motivos de ausência: campo vazio não permite distinguir recusa de ausência não especificada.",
                   "SCREENTIME: a lista de 2024 explicita exclusão de tarefas escolares; as anteriores não trazem essa frase no item. A mudança documental não prova mudança de medição.",
                   "Bullying tem instrução adicional desde 2022; preservado para exploração, excluído dos preditores iniciais.",
                   "MAKEFRIEND mudou o universo em 2022; a restrição de 6–17 anos mantém aplicabilidade comum.",
                   "Comportamento/desempenho escolar preservados para descrição; não entram nos modelos iniciais por possível proximidade com sintomas e causalidade reversa.",
                   "ENGAGECONCERN e BODYIMAGE não incluídas na versão analítica; exigem revisão metodológica.",
                   "FWC é preservado; peso médio do período é FWC/número de edições incluídas. Desenho complexo e estimativas de variância ainda exigem método apropriado.",
                   "Associação não implica causalidade; respostas de responsável sobre diagnóstico informado por profissional não são diagnósticos produzidos pelo sistema."]
    report = {"validado": True, "versao_regras": rules["versao"], "anos": years, "registros": len(dataset), "edicoes": edition_log,
              "originais_inalterados": before == after, "fingerprints_publicados": fingerprints, "fluxo": flows,
              "status_targets": {target: {str(k): int(v) for k, v in dataset[target + "_status"].value_counts().items()} for target in TARGETS},
              "fontes": sources, "limitacoes": limitations}
    (reports / "qualidade.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Qualidade da harmonização NSCH", "", f"Registros de {rules['faixa_etaria'][0]}–{rules['faixa_etaria'][1]} anos: {len(dataset):,}.", "",
             "Contagens abaixo são amostrais, não ponderadas. Targets indeterminados permanecem ausentes no dataset principal.", "", "| Ano | Original | 6–17 anos |", "|---|---:|---:|"]
    lines.extend(f"| {e['ano']} | {e.get('originais', 'não validado')} | {e.get('analiticos', 'não incluído')} |" for e in edition_log)
    for target in TARGETS:
        lines.extend(["", f"## {target}", f"Positivos: {int(dataset[target].eq(1).sum())}; negativos: {int(dataset[target].eq(0).sum())}; indeterminados: {int(dataset[target].isna().sum())}."])
    lines.extend(["", "## Limitações", "", *[f"- {item}" for item in limitations]])
    (reports / "qualidade.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {"validado": True, "tipo_validacao": "tecnica_automatizada_com_regras_documentadas", "aprovado_por": f"Rotina MindScreen AI {rules['versao']} (não representa aprovação humana)",
                "documentacao_validacao": str((reports / "qualidade.md").resolve()), "metodologia": rules["metodologia"], "dataset": "dataset.parquet",
                "sha256": sha256(planned[0]), "classe_positiva": 1, "anos": years, "registros": len(dataset),
                "preditores_numericos": rules["preditores_numericos"], "preditores_categoricos": rules["preditores_categoricos"],
                "targets": list(TARGETS), "componentes_targets": COMPONENTS, "componentes_arquivo": "componentes_targets.parquet",
                "administrativas": ADMIN + ["id_registro", "ano", "FWC_media_anual_periodo"], "rotulos": rules["rotulos"],
                "sha256_regras": sha256(config), "fontes": sources, "limitacoes": limitations, "criado_utc": datetime.now(timezone.utc).isoformat()}
    planned[4].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("Dados"))
    parser.add_argument("--saida", type=Path, default=Path("data/processed"))
    parser.add_argument("--relatorios", type=Path, default=Path("reports/harmonizacao"))
    parser.add_argument("--config", type=Path, default=Path("configs/harmonizacao.json"))
    args = parser.parse_args()
    try:
        report = run(args.entrada, args.saida, args.relatorios, args.config)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"Harmonização interrompida: {exc}\n")
    print(f"Harmonização validada: {report['registros']} registros; anos {report['anos']}")
    print(f"Dataset e manifesto em {args.saida}; qualidade em {args.relatorios}")


if __name__ == "__main__":
    main()
