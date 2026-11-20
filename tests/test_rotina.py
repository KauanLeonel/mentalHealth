from datetime import date

import pytest

from mindscreen.rotina import ATIVIDADES, criar_registro, historico, registrar


def test_registro_preserva_ausencia_e_permite_zero():
    registro = criar_registro(date(2024, 1, 1), 0, None, [ATIVIDADES[0]], hoje=date(2024, 1, 2))
    assert registro["tela_horas"] == 0
    assert registro["sono_horas"] is None
    assert historico([registro]).iloc[0]["sono_horas"] is None


@pytest.mark.parametrize("tela,sono", [(-1, None), (25, 8), (float("nan"), 8), (True, 8), (None, None)])
def test_registro_rejeita_valores_invalidos(tela, sono):
    with pytest.raises(ValueError):
        criar_registro(date(2024, 1, 1), tela, sono, hoje=date(2024, 1, 2))


def test_data_e_atividades_sao_validadas():
    with pytest.raises(ValueError):
        criar_registro(date(2024, 1, 3), 1, None, hoje=date(2024, 1, 2))
    with pytest.raises(ValueError):
        criar_registro(date(2024, 1, 1), 1, None, ["inválido"], hoje=date(2024, 1, 2))


def test_atualiza_por_data_sem_modificar_lista_original():
    a = criar_registro(date(2024, 1, 1), 1, None, hoje=date(2024, 1, 2))
    b = criar_registro(date(2024, 1, 2), 2, None, hoje=date(2024, 1, 2))
    substituto = criar_registro(date(2024, 1, 1), 3, None, hoje=date(2024, 1, 2))
    original = [a, b]
    resultado = registrar(original, substituto)
    assert [x["tela_horas"] for x in resultado] == [3, 2]
    assert original[0]["tela_horas"] == 1
