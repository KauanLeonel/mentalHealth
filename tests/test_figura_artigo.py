import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ARQUIVO = Path(__file__).resolve().parents[1] / "artigo" / "gerar_figura.py"
spec = importlib.util.spec_from_file_location("figura_artigo", ARQUIVO)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_leitura_e_geracao_da_figura():
    linhas = [{"target": t, "categoria_screentime": c, "referencia": 1,
               "odds_ratio_ajustada_amostral": 1 + c / 10}
              for t in ("depressao_atual", "ansiedade_atual") for c in range(2, 6)]
    with patch.object(Path, "read_text", return_value=json.dumps({"odds_ratios": linhas})):
        assert mod.carregar_or("dados.json")[("ansiedade_atual", 5)] == 1.5
        with patch.object(Path, "mkdir"), patch.object(mod.Image.Image, "save") as salvar:
            mod.gerar("dados.json", "figura.png")
            salvar.assert_called_once()
    linhas.pop()
    with patch.object(Path, "read_text", return_value=json.dumps({"odds_ratios": linhas})):
        with pytest.raises(ValueError, match="incompleto"):
            mod.carregar_or("dados.json")
