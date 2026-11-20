"""Regras puras para um diário voluntário e temporário de rotina, plano familiar e avaliação do protótipo.

Nada aqui interpreta saúde: os cálculos apenas resumem o que a própria família informou e comparam com os
objetivos que ela mesma escolheu. Valores não informados permanecem ausentes.
"""
from datetime import date, datetime, timedelta
import json
from math import isfinite

import pandas as pd

ATIVIDADES = ("Brincadeiras ou jogos", "Atividade física", "Leitura ou estudos",
              "Convivência com família ou amigos", "Descanso", "Outra atividade")
COMBINADOS = ("Conversar sobre o conteúdo visto", "Reservar tempo para outras atividades",
              "Combinar momentos sem telas", "Revisar juntos as configurações de privacidade",
              "Deixar as telas fora do quarto na hora de dormir", "Fazer refeições sem telas")
PERGUNTAS = ("O uso de telas está atrapalhando alguma atividade que você gostaria de fazer?",
             "O que você mais gostou de fazer hoje, com ou sem telas?",
             "Houve algo que você gostaria de fazer e não encontrou tempo?",
             "Como podemos organizar a rotina juntos para a próxima semana?")
RESPOSTAS_ATRAPALHOU = ("Sim", "Não", "Não sei")
QUEM_REGISTRA = ("Responsável", "Criança ou adolescente", "Juntos")
TIPOS_OBJETIVO = {"tela_max": "Até {valor:g} h de tela recreativa por dia",
                  "sono_min": "Pelo menos {valor:g} h de sono por noite",
                  "atividade_dias": "“{atividade}” em pelo menos {valor:g} dias da semana"}
AVALIACAO = {"graficos_compreensiveis": "Consegui entender os gráficos do histórico.",
             "plano_util": "O plano em família foi útil para a nossa conversa.",
             "facil_de_usar": "Foi fácil registrar a rotina."}
ESCALA = (1, 2, 3, 4, 5)
VOLTARIA = ("Sim", "Talvez", "Não")
MAX_TEXTO = 500


def _texto(valor, campo, maximo=MAX_TEXTO, obrigatorio=False):
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise ValueError(f"{campo}: texto inválido.")
    valor = " ".join(valor.split())
    if obrigatorio and not valor:
        raise ValueError(f"{campo}: preencha o campo.")
    if len(valor) > maximo:
        raise ValueError(f"{campo}: use no máximo {maximo} caracteres.")
    return valor


def nova_atividade(nome, existentes=ATIVIDADES):
    """Atividade escolhida pela família; evita duplicatas ignorando maiúsculas e espaços."""
    nome = _texto(nome, "Atividade", maximo=40, obrigatorio=True)
    if nome.casefold() in {a.casefold() for a in existentes}:
        raise ValueError("Essa atividade já está na lista.")
    return nome


def criar_registro(dia, tela, sono, atividades=(), hoje=None, permitidas=ATIVIDADES, tela_atrapalhou=None, quem=None):
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
    if tela_atrapalhou is not None and tela_atrapalhou not in RESPOSTAS_ATRAPALHOU:
        raise ValueError("Resposta inválida sobre o uso de telas.")
    if quem is not None and quem not in QUEM_REGISTRA:
        raise ValueError("Informe quem fez o registro a partir da lista.")
    if all(v is None for v in valores) and not atividades and tela_atrapalhou is None:
        raise ValueError("Informe pelo menos um item da rotina.")
    if any(a not in permitidas for a in atividades) or len(set(atividades)) != len(atividades):
        raise ValueError("Atividade inválida ou repetida.")
    return {"data": dia.isoformat(), "tela_horas": valores[0], "sono_horas": valores[1],
            "atividades": list(atividades), "tela_atrapalhou": tela_atrapalhou, "quem": quem}


def registrar(registros, novo):
    """Um registro por data; substituir uma data não altera as demais."""
    resultado = [r for r in registros if r["data"] != novo["data"]]
    return sorted([*resultado, novo], key=lambda r: r["data"])


COLUNAS = ["data", "tela_horas", "sono_horas", "atividades", "tela_atrapalhou", "quem"]


def historico(registros):
    """Retorna dados numéricos sem preencher registros ausentes com zero."""
    frame = pd.DataFrame([{c: r.get(c) for c in COLUNAS} for r in registros], columns=COLUNAS)
    if not frame.empty:
        frame["data"] = pd.to_datetime(frame["data"])
    return frame


def _janela(registros, fim, dias):
    inicio = fim - timedelta(days=dias - 1)
    return [r for r in registros if inicio.isoformat() <= r["data"] <= fim.isoformat()], inicio


def resumo_periodo(registros, fim=None, dias=7):
    """Resumo descritivo do que foi informado no período; médias usam só os dias com o valor preenchido."""
    fim = fim or date.today()
    janela, inicio = _janela(registros, fim, dias)
    def media(campo):
        valores = [r[campo] for r in janela if r.get(campo) is not None]
        return {"media": sum(valores) / len(valores) if valores else None, "dias_informados": len(valores)}
    contagem = {}
    for r in janela:
        for a in r.get("atividades", []):
            contagem[a] = contagem.get(a, 0) + 1
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "dias_no_periodo": dias, "dias_com_registro": len(janela),
            "tela": media("tela_horas"), "sono": media("sono_horas"),
            "atividades": dict(sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))),
            "tela_atrapalhou": {resp: sum(r.get("tela_atrapalhou") == resp for r in janela) for resp in RESPOSTAS_ATRAPALHOU}}


def criar_objetivo(tipo, valor, atividade=None, permitidas=ATIVIDADES):
    """Objetivo escolhido pela família. Os valores são decisão dela; o sistema não sugere números."""
    if tipo not in TIPOS_OBJETIVO:
        raise ValueError("Tipo de objetivo inválido.")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor):
        raise ValueError("Informe um número para o objetivo.")
    limite = 7 if tipo == "atividade_dias" else 24
    if not 0 < valor <= limite or (tipo == "atividade_dias" and float(valor) != int(valor)):
        raise ValueError(f"O valor deve ser maior que zero e no máximo {limite}" + (" dias (número inteiro)." if limite == 7 else " horas."))
    if tipo == "atividade_dias":
        if atividade not in permitidas:
            raise ValueError("Escolha uma atividade da lista.")
    else:
        atividade = None
    valor = int(valor) if tipo == "atividade_dias" else float(valor)
    return {"tipo": tipo, "valor": valor, "atividade": atividade, "descricao": TIPOS_OBJETIVO[tipo].format(valor=valor, atividade=atividade)}


def adicionar_objetivo(objetivos, novo):
    if any(o["descricao"] == novo["descricao"] for o in objetivos):
        raise ValueError("Esse objetivo já está no plano.")
    return [*objetivos, novo]


def progresso_objetivos(registros, objetivos, fim=None, dias=7):
    """Quantos dias informados atenderam a cada objetivo. Dias sem a informação não contam como falha."""
    fim = fim or date.today()
    janela, inicio = _janela(registros, fim, dias)
    linhas = []
    for o in objetivos:
        if o["tipo"] == "atividade_dias":
            feitos = sum(o["atividade"] in r.get("atividades", []) for r in janela)
            linhas.append({"objetivo": o["descricao"], "dias_informados": len(janela), "dias_alcancados": feitos,
                           "meta_dias": o["valor"], "alcancado": feitos >= o["valor"]})
            continue
        campo = "tela_horas" if o["tipo"] == "tela_max" else "sono_horas"
        valores = [r[campo] for r in janela if r.get(campo) is not None]
        ok = [v <= o["valor"] if o["tipo"] == "tela_max" else v >= o["valor"] for v in valores]
        linhas.append({"objetivo": o["descricao"], "dias_informados": len(valores), "dias_alcancados": sum(ok),
                       "meta_dias": None, "alcancado": None})
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "linhas": linhas}


def registrar_reflexao(reflexoes, pergunta, resposta, dia=None):
    if pergunta not in PERGUNTAS:
        raise ValueError("Pergunta inválida.")
    resposta = _texto(resposta, "Resposta", obrigatorio=True)
    return [*reflexoes, {"data": (dia or date.today()).isoformat(), "pergunta": pergunta, "resposta": resposta}]


def criar_avaliacao(notas, voltaria, comentario=""):
    """Avaliação voluntária do protótipo (pergunta de pesquisa 2): compreensão, utilidade e intenção de retorno."""
    if set(notas) != set(AVALIACAO) or any(n not in ESCALA for n in notas.values()):
        raise ValueError("Responda às afirmações com uma nota de 1 a 5.")
    if voltaria not in VOLTARIA:
        raise ValueError("Informe se voltaria a usar o protótipo.")
    return {"notas": dict(notas), "voltaria": voltaria, "comentario": _texto(comentario, "Comentário"),
            "data": date.today().isoformat()}


def exportar(registros=(), objetivos=(), combinados=(), reflexoes=(), avaliacao=None):
    """JSON gerado sob demanda para a própria família baixar; o aplicativo não o guarda."""
    return json.dumps({"formato": "mindscreen-rotina-v1", "gerado_em": date.today().isoformat(),
                       "registros": list(registros), "objetivos": list(objetivos), "combinados": list(combinados),
                       "reflexoes": list(reflexoes), "avaliacao_prototipo": avaliacao}, ensure_ascii=False, indent=2)
