"""Regras puras para um diário voluntário e temporário de rotina."""
from datetime import date, datetime
from math import isfinite

import pandas as pd

ATIVIDADES = ("Brincadeiras ou jogos", "Atividade física", "Leitura ou estudos",
              "Convivência com família ou amigos", "Descanso", "Outra atividade")
COMBINADOS = ("Conversar sobre o conteúdo visto", "Reservar tempo para outras atividades",
              "Combinar momentos sem telas", "Revisar juntos as configurações de privacidade")
PERGUNTAS = ("O que você mais gostou de fazer hoje, com ou sem telas?",
             "Houve algo que você gostaria de fazer e não encontrou tempo?",
             "Como podemos organizar a rotina juntos para a próxima semana?")


def criar_registro(dia, tela, sono, atividades=(), hoje=None):
    """Valida valores informados; não interpreta hábitos nem usa dados clínicos."""
    if not isinstance(dia, date) or isinstance(dia, datetime) or dia > (hoje or date.today()):
        raise ValueError("Informe uma data válida que não esteja no futuro.")
    valores = []
    for valor in (tela, sono):
        if valor is None:
            valores.append(None)
            continue
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor) or not 0 <= valor <= 24:
            raise ValueError("As durações devem estar entre 0 e 24 horas.")
        valores.append(float(valor))
    if all(v is None for v in valores) and not atividades:
        raise ValueError("Informe pelo menos um item da rotina.")
    if any(a not in ATIVIDADES for a in atividades) or len(set(atividades)) != len(atividades):
        raise ValueError("Atividade inválida ou repetida.")
    return {"data": dia.isoformat(), "tela_horas": valores[0], "sono_horas": valores[1],
            "atividades": list(atividades)}


def registrar(registros, novo):
    """Um registro por data; substituir uma data não altera as demais."""
    resultado = [r for r in registros if r["data"] != novo["data"]]
    return sorted([*resultado, novo], key=lambda r: r["data"])


def historico(registros):
    """Retorna dados numéricos sem preencher registros ausentes com zero."""
    frame = pd.DataFrame(registros, columns=["data", "tela_horas", "sono_horas", "atividades"])
    if not frame.empty:
        frame["data"] = pd.to_datetime(frame["data"])
    return frame
