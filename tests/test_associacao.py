"""Associação descritiva com fixture sintética exclusiva para teste."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from mindscreen.associacao import run


def test_or_referencia_casos_completos_e_exclusao_2024():
    rng = np.random.default_rng(42)
    n = 500
    frame = pd.DataFrame({"ano": np.repeat([2020, 2021, 2022, 2023, 2024], n // 5),
                          "SC_AGE_YEARS": rng.integers(6, 18, n), "SCREENTIME": np.tile([1, 2, 3, 4, 5], n // 5),
                          "SC_SEX": rng.integers(1, 3, n), "HOURSLEEP": rng.integers(1, 8, n),
                          "PHYSACTIV": rng.integers(1, 5, n), "MAKEFRIEND": rng.integers(1, 4, n),
                          "depressao_atual": rng.integers(0, 2, n), "ansiedade_atual": rng.integers(0, 2, n)})
    frame.loc[frame.ano.eq(2024), "depressao_atual"] = 99
    frame.loc[0, "HOURSLEEP"] = np.nan
    with patch("mindscreen.associacao.load_dataset", return_value=({"sha256": "fixture"}, frame)), \
         patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"), patch.object(pd.DataFrame, "to_csv"):
        result = run(Path("fixture"), Path("reports/fixture-nao-gravada"))
    assert len(result["odds_ratios"]) == 8
    for row in result["odds_ratios"]:
        assert row["referencia"] == 1
        assert row["n_casos_completos"] == 399
        assert np.isfinite(row["odds_ratio_ajustada_amostral"])
    for detail in result["detalhes"].values():
        assert detail["n_desenvolvimento"] == 400
        assert detail["intervalos_confianca"] is None
        assert detail["pesos"] is False
