"""Regras do plano familiar, resumo, reflexões, avaliação do protótipo e exportação."""
from datetime import date
import json

import pytest

from mindscreen.rotina import (ATIVIDADES, PERGUNTAS, adicionar_objetivo, criar_avaliacao, criar_objetivo, criar_registro,
                               exportar, nova_atividade, progresso_objetivos, registrar_reflexao, resumo_periodo)


def _dia(d, tela=None, sono=None, atividades=(), **kw):
    return criar_registro(date(2024, 1, d), tela, sono, atividades, hoje=date(2024, 1, 31), **kw)


def test_pergunta_do_texto_e_resposta_sobre_tela_atrapalhar():
    assert "O uso de telas está atrapalhando alguma atividade que você gostaria de fazer?" in PERGUNTAS
    registro = _dia(1, tela_atrapalhou="Sim")
    assert registro["tela_atrapalhou"] == "Sim" and registro["tela_horas"] is None
    with pytest.raises(ValueError):
        _dia(1, tela=1, tela_atrapalhou="Talvez")
    with pytest.raises(ValueError):
        _dia(1, tela=1, quem="Vizinho")


def test_atividade_da_familia_e_validada_e_aceita_no_registro():
    nova = nova_atividade("  Tocar   violão ")
    assert nova == "Tocar violão"
    with pytest.raises(ValueError):
        nova_atividade("atividade física")
    with pytest.raises(ValueError):
        nova_atividade("x" * 41)
    with pytest.raises(ValueError):
        _dia(1, atividades=[nova])
    assert _dia(1, atividades=[nova], permitidas=(*ATIVIDADES, nova))["atividades"] == [nova]


def test_resumo_usa_apenas_dias_informados_e_periodo():
    registros = [_dia(1, tela=10), _dia(25, tela=2, sono=8, atividades=[ATIVIDADES[1]]),
                 _dia(31, tela=4, atividades=[ATIVIDADES[1]], tela_atrapalhou="Sim")]
    resumo = resumo_periodo(registros, fim=date(2024, 1, 31), dias=7)
    assert resumo["dias_com_registro"] == 2
    assert resumo["tela"] == {"media": 3.0, "dias_informados": 2}
    assert resumo["sono"] == {"media": 8.0, "dias_informados": 1}
    assert resumo["atividades"] == {ATIVIDADES[1]: 2}
    assert resumo["tela_atrapalhou"]["Sim"] == 1
    assert resumo_periodo([], fim=date(2024, 1, 31))["tela"]["media"] is None


def test_objetivos_escolhidos_pela_familia_e_progresso_sem_contar_ausentes():
    tela = criar_objetivo("tela_max", 2)
    sono = criar_objetivo("sono_min", 9)
    atividade = criar_objetivo("atividade_dias", 2, ATIVIDADES[1])
    assert tela["descricao"] == "Até 2 h de tela recreativa por dia"
    objetivos = adicionar_objetivo(adicionar_objetivo(adicionar_objetivo([], tela), sono), atividade)
    with pytest.raises(ValueError):
        adicionar_objetivo(objetivos, criar_objetivo("tela_max", 2))
    for args in [("tela_max", 0), ("tela_max", 25), ("atividade_dias", 8, ATIVIDADES[1]), ("atividade_dias", 2.5, ATIVIDADES[1]),
                 ("atividade_dias", 2, "inexistente"), ("outro", 1), ("tela_max", True), ("sono_min", None)]:
        with pytest.raises(ValueError):
            criar_objetivo(*args)
    registros = [_dia(29, tela=1, atividades=[ATIVIDADES[1]]), _dia(30, tela=3), _dia(31, sono=9.5, atividades=[ATIVIDADES[1]])]
    linhas = {l["objetivo"]: l for l in progresso_objetivos(registros, objetivos, fim=date(2024, 1, 31))["linhas"]}
    assert (linhas[tela["descricao"]]["dias_informados"], linhas[tela["descricao"]]["dias_alcancados"]) == (2, 1)
    assert (linhas[sono["descricao"]]["dias_informados"], linhas[sono["descricao"]]["dias_alcancados"]) == (1, 1)
    assert linhas[atividade["descricao"]]["dias_alcancados"] == 2 and linhas[atividade["descricao"]]["alcancado"] is True


def test_reflexao_avaliacao_e_exportacao():
    reflexoes = registrar_reflexao([], PERGUNTAS[0], "  Sim, a leitura  ", dia=date(2024, 1, 2))
    assert reflexoes[0]["resposta"] == "Sim, a leitura"
    with pytest.raises(ValueError):
        registrar_reflexao([], "Outra pergunta", "x")
    with pytest.raises(ValueError):
        registrar_reflexao([], PERGUNTAS[0], "   ")
    notas = {"graficos_compreensiveis": 4, "plano_util": 5, "facil_de_usar": 3}
    avaliacao = criar_avaliacao(notas, "Talvez", "ok")
    for args in [({**notas, "plano_util": 6}, "Sim"), ({"plano_util": 5}, "Sim"), (notas, None)]:
        with pytest.raises(ValueError):
            criar_avaliacao(*args)
    dados = json.loads(exportar([_dia(1, tela=1)], [criar_objetivo("tela_max", 2)], ["Fazer refeições sem telas"], reflexoes, avaliacao))
    assert dados["formato"] == "mindscreen-rotina-v1"
    assert dados["registros"][0]["tela_horas"] == 1 and dados["avaliacao_prototipo"]["voltaria"] == "Talvez"
