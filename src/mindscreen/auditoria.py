"""Inventário conservador; nomes e rótulos não comprovam compatibilidade."""

import argparse
import csv
import json
from pathlib import Path
from collections import Counter

from mindscreen.importacao import YEARS, discover, read_file

PRIORITY = "SCREENTIME SC_SEX SC_AGE_YEARS MAKEFRIEND PHYSACTIV HOURSLEEP ENGAGECONCERN BODYIMAGE BULLIED_R BULLY K7Q70_R K7Q84_R K7Q83_R K7Q85_R K7Q82_R K2Q32A K2Q32B K2Q33A K2Q33B FWC".split()


def audit_csv(path: Path, year: int | None):
    """Lê CSV em fluxo, sem inferir tipos ou interpretar códigos como ausentes."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        names = next(reader)
        if not names or len(set(names)) != len(names):
            raise ValueError("Cabeçalho vazio ou nomes de colunas duplicados")
        empty = [0] * len(names)
        indexes = {i: Counter() for i, name in enumerate(names) if name.upper() in PRIORITY and name.upper() != "FWC"}
        rows = 0
        for row in reader:
            if len(row) != len(names):
                raise ValueError(f"Linha {reader.line_num}: quantidade de campos inconsistente")
            rows += 1
            for i, value in enumerate(row):
                if not value.strip():
                    empty[i] += 1
            for i, counts in indexes.items():
                if row[i].strip():
                    counts[row[i]] += 1
        columns = [{"arquivo": str(path), "ano": year, "variavel": name, "tipo": "texto CSV (tipo original não informado)",
                    "rotulo": None, "categorias_metadados": "{}", "valores_especiais_metadados": "[]"} for name in names]
        missing = [{"arquivo": str(path), "ano": year, "variavel": name, "ausentes_sistema": empty[i],
                    "observacao": "Campos vazios; códigos especiais exigem revisão do dicionário."} for i, name in enumerate(names)]
        values = [{"arquivo": str(path), "ano": year, "variavel": names[i], "valor": value, "contagem": count}
                  for i, counts in indexes.items() for value, count in sorted(counts.items())]
        return rows, columns, missing, values


def audit(raw: Path) -> dict:
    candidates = discover(raw)
    files, columns, missing, errors, values = [], [], [], [], []
    for candidate in candidates:
        entry = {"arquivo": str(candidate.path), "ano": candidate.year,
                 "indicio_topical": candidate.topical_hint, "indicio_enhanced": candidate.enhanced_hint,
                 "validado": False, "registros": None, "colunas": None}
        try:
            if candidate.path.suffix.lower() == ".csv":
                rows, csv_columns, csv_missing, csv_values = audit_csv(candidate.path, candidate.year)
                entry.update(registros=rows, colunas=len(csv_columns))
                columns.extend(csv_columns)
                missing.extend(csv_missing)
                values.extend(csv_values)
                files.append(entry)
                continue
            df, meta = read_file(candidate.path)
            entry.update(registros=len(df), colunas=len(df.columns))
            for name in df.columns:
                labels = getattr(meta, "variable_value_labels", {}).get(name, {})
                columns.append({"arquivo": str(candidate.path), "ano": candidate.year, "variavel": name,
                                "tipo": str(df[name].dtype), "rotulo": getattr(meta, "column_names_to_labels", {}).get(name),
                                "categorias_metadados": json.dumps(labels, ensure_ascii=False, default=str),
                                "valores_especiais_metadados": json.dumps(getattr(meta, "missing_user_values", {}).get(name, []), ensure_ascii=False, default=str)})
                missing.append({"arquivo": str(candidate.path), "ano": candidate.year, "variavel": name,
                                "ausentes_sistema": int(df[name].isna().sum()),
                                "observacao": "Não inclui necessariamente valores especiais; revisar dicionário e metadados."})
        except Exception as exc:
            errors.append({"arquivo": str(candidate.path), "erro": f"{type(exc).__name__}: {exc}"})
        files.append(entry)
    availability = []
    for year in YEARS:
        for variable in PRIORITY:
            found = any(c["ano"] == year and c["variavel"].upper() == variable for c in columns)
            has_read = any(f["ano"] == year and f["colunas"] is not None for f in files)
            status = "Necessita revisão metodológica" if found else ("Ausente" if has_read else "Ano não auditado")
            availability.append({"ano": year, "variavel": variable, "classificacao": status})
    matrix = []
    for name in sorted({c["variavel"] for c in columns} | set(PRIORITY)):
        row = {"variavel": name}
        for year in YEARS:
            read = any(f["ano"] == year and f["colunas"] is not None for f in files)
            row[str(year)] = ("presente" if any(c["ano"] == year and c["variavel"] == name for c in columns)
                              else "ausente" if read else "não auditado")
        matrix.append(row)
    return {"arquivos": files, "colunas": columns, "faltantes": missing, "disponibilidade": availability,
            "matriz": matrix, "erros": errors, "valores_prioritarios": values,
            "anos_sem_arquivo": [y for y in YEARS if not any(c.year == y for c in candidates)],
            "aviso": "Indícios de nome não comprovam procedência, versão ou compatibilidade; nenhuma edição está validada automaticamente."}


def write_reports(report: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "auditoria.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    schemas = {"arquivos": ["arquivo", "ano", "indicio_topical", "indicio_enhanced", "validado", "registros", "colunas"],
               "colunas": ["arquivo", "ano", "variavel", "tipo", "rotulo", "categorias_metadados", "valores_especiais_metadados"],
               "faltantes": ["arquivo", "ano", "variavel", "ausentes_sistema", "observacao"],
               "disponibilidade": ["ano", "variavel", "classificacao"], "matriz": ["variavel", *map(str, YEARS)],
               "erros": ["arquivo", "erro"], "valores_prioritarios": ["arquivo", "ano", "variavel", "valor", "contagem"]}
    for name, fields in schemas.items():
        with (out / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(report[name])
    lines = ["# Auditoria NSCH", "", report["aviso"], "", f"Arquivos candidatos: {len(report['arquivos'])}.",
             f"Anos sem arquivo candidato: {', '.join(map(str, report['anos_sem_arquivo'])) or 'nenhum'}.",
             f"Erros de leitura: {len(report['erros'])}.",
             "", "Nenhum arquivo é aprovado automaticamente. Revise procedência, dicionário por edição, códigos especiais, saltos e desenho amostral antes de qualquer harmonização."]
    (out / "auditoria.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventaria arquivos NSCH sem alterar os originais")
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("reports/auditoria"))
    args = parser.parse_args()
    raw, out = args.raw.resolve(), args.output.resolve()
    if out == raw or raw in out.parents:
        parser.error("Os relatórios não podem ser escritos em data/raw.")
    report = audit(raw)
    write_reports(report, out)
    print(f"Auditoria: {len(report['arquivos'])} arquivo(s); relatórios em {out}")


if __name__ == "__main__":
    main()
