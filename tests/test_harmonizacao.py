"""Regras científicas e integridade com fixtures sintéticas identificadas como teste."""

import json
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from mindscreen.dados_validados import check_predictors, load_dataset
from mindscreen.harmonizacao import COMPONENTS, build_target, category, harmonize_frame, sha256, verify_edition


@pytest.mark.parametrize("history,current,expected", [
    ("2", "", 0), ("2.0", ".L", 0), ("2", "2", 0),
    ("1", "1", 1), ("1", "2", 0), ("1", "", None),
    ("1", ".M", None), ("", "1", None), ("", "2", None),
    ("9", "2", None), ("2", "1", None), ("2", "9", None),
    ("2", ".M", None), ("2", ".N", None), ("2", ".D", None),
])
def test_target_documentado_nao_converte_incerteza_em_negativo(history, current, expected):
    target, _ = build_target(pd.Series([history]), pd.Series([current]))
    assert pd.isna(target.iloc[0]) if expected is None else target.iloc[0] == expected


def test_categorias_preservam_motivos_sem_adivinhar_recusa():
    raw = pd.Series(["1.0", " 2 ", "", ".L", ".M", ".N", ".D", "9", "1.5", "NA"])
    values, status = category(raw, [1, 2])
    assert values.iloc[:2].tolist() == [1, 2]
    assert values.iloc[2:].isna().all()
    assert status.tolist() == ["respondido", "respondido", "ausente_sem_motivo_csv", "salto_logico_declarado",
                               "resposta_invalida_declarada", "inaplicavel_declarado", "suprimido_confidencialidade",
                               "codigo_nao_documentado", "codigo_nao_documentado", "codigo_nao_documentado"]
    assert raw.iloc[0] == "1.0"


def fixture_frame():
    # Não representa participantes ou estatísticas do NSCH.
    return pd.DataFrame({"HHID": ["a", "b", "c", "d"], "FIPSST": ["01"] * 4,
                         "STRATUM": ["1", "2A", "1", "2A"], "FORMTYPE": ["T1", "T2", "T3", "T3"],
                         "FWC": ["10", "20", "30", "40"], "SC_AGE_YEARS": ["5", "6", "12", "17"],
                         "SC_SEX": ["1", "2", "1", "2"], "SCREENTIME": ["", "1", "2", "3"],
                         "K2Q32A": ["2", "2", "1", ""], "K2Q32B": ["", "", "1", ""],
                         "K2Q33A": ["1", "1", "1", "2"], "K2Q33B": ["2", "", "2", ""]})


def fixture_rules():
    return {"faixa_etaria": [6, 17], "dominios": {"SCREENTIME": [1, 2, 3, 4, 5], "SC_SEX": [1, 2]},
            "preditores_numericos": ["SC_AGE_YEARS"], "preditores_categoricos": ["SCREENTIME", "SC_SEX"],
            "edicoes": {"2020": {"sim": 1, "nao": 2, "registros": 4, "sexo_contagens": [2, 2],
                                   "sexo_pesos": [40, 60], "screentime_contagens": [1, 1, 1, 1, 0, 0]}}}


def test_restricao_etaria_targets_independentes_e_contagens():
    source, rules = fixture_frame(), fixture_rules()
    original = source.copy(deep=True)
    result, components, flows = harmonize_frame(source, 2020, rules)
    pd.testing.assert_frame_equal(source, original)
    assert result["SC_AGE_YEARS"].tolist() == [6, 12, 17]
    assert result["depressao_atual"].notna().sum() == 2
    assert result["ansiedade_atual"].notna().sum() == 2
    assert result.loc[result.HHID.eq("b"), "depressao_atual"].iloc[0] == 0
    assert pd.isna(result.loc[result.HHID.eq("b"), "ansiedade_atual"].iloc[0])
    assert set(result.id_registro) == set(components.id_registro)
    assert all(v not in result for pair in COMPONENTS.values() for v in pair)
    for target in COMPONENTS:
        n = {r["decisao"]: r["registros"] for r in flows if r["target"] == target}
        assert n["entrada_original"] == n["excluidos_fora_faixa_etaria"] + n["mantidos_faixa_etaria"]
        assert n["mantidos_faixa_etaria"] == n["target_indeterminado"] + n["target_determinado"]
        assert n["target_determinado"] == n["target_positivo"] + n["target_negativo"]


def test_controle_oficial_bloqueia_pesos_e_edicoes_alterados():
    frame, rules = fixture_frame(), fixture_rules()
    assert all(c["aprovada"] for c in verify_edition(frame, 2020, rules))
    for column, value in [("FWC", "1000"), ("SCREENTIME", "5"), ("STRATUM", "9"), ("FORMTYPE", "T3")]:
        changed = frame.copy()
        changed.loc[0, column] = value
        with pytest.raises(ValueError):
            verify_edition(changed, 2020, rules)
    with pytest.raises(ValueError):
        verify_edition(frame.iloc[:-1], 2020, rules)


def test_status_componentes_e_pesos_ajustados_nao_sao_preditores():
    for variable in ["depressao_atual_status", "ansiedade_atual_status", "SCREENTIME_status", "FWC_media_anual_periodo", "FORMTYPE", "id_registro"]:
        with pytest.raises(ValueError):
            check_predictors([], ["SCREENTIME", variable])


def test_artefatos_reais_se_existirem_passam_no_contrato():
    path = Path("data/processed/manifesto.json")
    if not path.exists():
        pytest.skip("Dataset analítico ainda não gerado")
    manifest, frame = load_dataset(path)
    assert len(frame) == manifest["registros"]
    assert sorted(frame.ano.unique().tolist()) == manifest["anos"]
    assert frame.id_registro.is_unique
    quality = json.loads(Path(manifest["documentacao_validacao"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert quality["originais_inalterados"] is True
    for source in manifest["fontes"]:
        assert sha256(source["arquivo"]) == source["sha256"]
    assert frame.SC_AGE_YEARS.between(6, 17).all()
    assert frame.FWC.gt(0).all()
    pd.testing.assert_series_equal(frame.FWC_media_anual_periodo, frame.FWC / len(manifest["anos"]), check_names=False)
    rules = json.loads(Path("configs/harmonizacao.json").read_text(encoding="utf-8"))
    for name, domain in rules["dominios"].items():
        assert frame[name].dropna().isin(domain).all()
    archive = pd.read_parquet(path.parent / "componentes_targets.parquet")
    joined = frame.set_index("id_registro")
    for year, group in archive.groupby("ano"):
        year_rules = rules["edicoes"][str(year)]
        for target, (history, current) in COMPONENTS.items():
            actual, _ = build_target(group[history], group[current], year_rules["sim"], year_rules["nao"])
            expected = joined.loc[group.id_registro, target].reset_index(drop=True)
            pd.testing.assert_series_equal(actual.reset_index(drop=True), expected, check_names=False)
