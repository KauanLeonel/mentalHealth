"""Protótipo de rotina digital; regras em mindscreen.rotina, conteúdo em mindscreen.conteudo, gráficos em mindscreen.painel."""
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st

from mindscreen.analise_contribuicao import sobreposicao
from mindscreen.conteudo import caminho_resultados_pesquisa, carregar_conteudo, carregar_resultados_pesquisa
from mindscreen.painel import contribution_chart, routine_history_chart, routine_profile_chart, ROTINA_ROTULOS
from mindscreen.rotina import (ATIVIDADES, AVALIACAO, COMBINADOS, ESCALA, PERGUNTAS, QUEM_REGISTRA, RESPOSTAS_ATRAPALHOU,
                               TIPOS_OBJETIVO, VOLTARIA, adicionar_objetivo, criar_avaliacao, criar_objetivo, criar_registro,
                               exportar, historico, nova_atividade, progresso_objetivos, registrar, registrar_reflexao,
                               resumo_periodo)

st.set_page_config(page_title="MindScreen | Rotina digital", page_icon="🌱", layout="wide")

MANIFEST = ROOT / "data/processed/manifesto.json"
CHAVES = ("registros_rotina", "plano_salvo", "combinados", "objetivos", "atividades_familia", "reflexoes", "avaliacao_prototipo",
          "dia", "tela", "sono", "atividades", "atrapalhou", "quem", "nova_atividade")
PAGINAS = ["Início", "Diário de rotina", "Histórico", "Plano em família", "Saiba mais", "Pesquisa", "Avaliar o protótipo"]


def limpar_sessao():
    for key in CHAVES:
        st.session_state.pop(key, None)


def atividades():
    return (*ATIVIDADES, *st.session_state.get("atividades_familia", []))


def num(valor, casas=1):
    return "—" if valor is None else f"{valor:.{casas}f}".replace(".", ",")


def inicio():
    st.title("Uma rotina digital que faça sentido para sua família")
    st.write("Observe o dia a dia, converse sobre o que é importante e construa pequenos combinados em conjunto.")
    st.info("Este é um protótipo de pesquisa e ainda não foi avaliado com famílias. Ele não faz diagnósticos nem prevê condições de saúde.")
    st.subheader("Como usar")
    st.write("1. **Diário**: registre o que quiser sobre um dia — tela, sono, atividades.  \n"
             "2. **Histórico**: veja como o tempo de tela se encaixa no resto da rotina.  \n"
             "3. **Plano em família**: escolham juntos objetivos e combinados, e conversem sobre as perguntas.  \n"
             "4. **Saiba mais** e **Pesquisa**: entenda o que os dados mostram, seus limites e quando procurar um profissional.")
    st.caption("Os registros são voluntários, ficam na sessão em memória e podem desaparecer ao recarregar, desconectar ou reiniciar o aplicativo. "
               "Não são gravados pelo aplicativo em arquivos ou banco de dados. Evite inserir dados em dispositivos compartilhados.")


def diario():
    st.title("Diário de rotina")
    st.write("Preencha apenas o que fizer sentido. Tempo de tela refere-se ao uso recreativo estimado no dia; sono refere-se à noite anterior.")
    with st.form("registro"):
        dia = st.date_input("Data do registro", value=date.today(), max_value=date.today(), key="dia")
        c1, c2 = st.columns(2)
        tela = c1.number_input("Tempo recreativo de tela (horas)", min_value=0.0, max_value=24.0, value=None, step=0.5, placeholder="Opcional", key="tela")
        sono = c2.number_input("Sono na noite anterior (horas)", min_value=0.0, max_value=24.0, value=None, step=0.5, placeholder="Opcional", key="sono")
        feitas = st.multiselect("O que também fez nesse dia?", atividades(), key="atividades")
        atrapalhou = st.radio("O uso de telas atrapalhou alguma atividade que você gostaria de fazer hoje?", RESPOSTAS_ATRAPALHOU,
                              index=None, horizontal=True, key="atrapalhou")
        quem = st.radio("Quem está registrando?", QUEM_REGISTRA, index=None, horizontal=True, key="quem")
        salvar = st.form_submit_button("Guardar na sessão", type="primary")
    if salvar:
        try:
            item = criar_registro(dia, tela, sono, feitas, permitidas=atividades(), tela_atrapalhou=atrapalhou, quem=quem)
            st.session_state["registros_rotina"] = registrar(st.session_state.get("registros_rotina", []), item)
            st.success("Registro guardado nesta sessão. Se já havia um registro para a data, ele foi atualizado.")
        except ValueError as exc:
            st.error(str(exc))
    with st.expander("Incluir uma atividade importante para a família"):
        nome = st.text_input("Nome da atividade", max_chars=40, key="nova_atividade")
        if st.button("Adicionar atividade"):
            try:
                st.session_state["atividades_familia"] = [*st.session_state.get("atividades_familia", []), nova_atividade(nome, atividades())]
                st.success("Atividade incluída. Ela aparece na lista acima.")
            except ValueError as exc:
                st.error(str(exc))
    st.caption("Não inclua nomes ou outras informações pessoais. Uma duração não informada continua vazia; zero significa que você informou zero.")


def ver_historico():
    st.title("Meu histórico nesta sessão")
    registros = st.session_state.get("registros_rotina", [])
    if not registros:
        st.info("Você ainda não adicionou registros. Use o Diário de rotina para começar.")
        return
    objetivos = st.session_state.get("objetivos", [])
    resumo = resumo_periodo(registros)
    st.subheader("Últimos 7 dias")
    c1, c2, c3 = st.columns(3)
    c1.metric("Dias com registro", f"{resumo['dias_com_registro']} de {resumo['dias_no_periodo']}")
    c2.metric("Tela recreativa (média, h)", num(resumo["tela"]["media"]), help=f"Média dos {resumo['tela']['dias_informados']} dias em que a tela foi informada.")
    c3.metric("Sono (média, h)", num(resumo["sono"]["media"]), help=f"Média dos {resumo['sono']['dias_informados']} dias em que o sono foi informado.")
    frame = historico(registros)
    st.plotly_chart(routine_history_chart(frame, objetivos), width="stretch")
    contagem = resumo_periodo(registros, dias=(frame.data.max() - frame.data.min()).days + 1, fim=frame.data.max().date())["atividades"]
    if contagem:
        fig = px.bar(x=list(contagem.values()), y=list(contagem.keys()), orientation="h", title="Atividades registradas (dias)",
                     labels={"x": "Dias", "y": ""}, color_discrete_sequence=["#6b8c65"])
        fig.update_layout(template="plotly_white", height=300)
        st.plotly_chart(fig, width="stretch")
    tabela = frame.copy()
    tabela["data"] = tabela["data"].dt.strftime("%d/%m/%Y")
    tabela["atividades"] = tabela["atividades"].map(lambda xs: ", ".join(xs) if xs else "Não informado")
    tabela = tabela.fillna({"tela_atrapalhou": "Não informado", "quem": "Não informado"})
    tabela = tabela.rename(columns={"data": "Data", "tela_horas": "Tela (h)", "sono_horas": "Sono (h)", "atividades": "Atividades",
                                    "tela_atrapalhou": "Tela atrapalhou?", "quem": "Quem registrou"})
    st.dataframe(tabela, hide_index=True, width="stretch")
    if objetivos:
        st.subheader("Objetivos da família nos últimos 7 dias")
        progresso = pd.DataFrame(progresso_objetivos(registros, objetivos)["linhas"])
        progresso = progresso.rename(columns={"objetivo": "Objetivo", "dias_informados": "Dias com informação", "dias_alcancados": "Dias em que foi alcançado"})
        st.dataframe(progresso[["Objetivo", "Dias com informação", "Dias em que foi alcançado"]], hide_index=True, width="stretch")
        st.caption("Dias sem a informação não contam como dias em que o objetivo não foi alcançado. Os números servem para conversar, não para avaliar ninguém.")
    st.caption("Os pontos representam apenas os dias e valores informados. Eles não demonstram causas, tendências gerais ou diagnósticos.")


def plano():
    st.title("Plano em família")
    st.write("Conversem e escolham juntos o que desejam experimentar. Os objetivos e combinados podem mudar quando deixarem de fazer sentido.")
    if "combinados" not in st.session_state:
        st.session_state["combinados"] = st.session_state.get("plano_salvo", [])
    def guardar_plano():
        st.session_state["plano_salvo"] = st.session_state["combinados"][:]
    st.multiselect("Combinados que queremos experimentar", COMBINADOS, key="combinados", on_change=guardar_plano)

    st.subheader("Nossos objetivos")
    st.caption("Vocês escolhem os números. O aplicativo não recomenda valores e só compara com o que vocês registrarem.")
    with st.form("objetivo", clear_on_submit=True):
        tipo = st.selectbox("Tipo de objetivo", list(TIPOS_OBJETIVO), format_func=lambda t: {"tela_max": "Limite de tela recreativa por dia",
                            "sono_min": "Horas de sono por noite", "atividade_dias": "Dias por semana com uma atividade"}[t])
        c1, c2 = st.columns(2)
        valor = c1.number_input("Valor (horas ou dias)", min_value=0.0, max_value=24.0, value=None, step=0.5)
        atividade = c2.selectbox("Atividade (para objetivos de dias por semana)", atividades(), index=None)
        if st.form_submit_button("Incluir objetivo"):
            try:
                novo = criar_objetivo(tipo, valor, atividade, permitidas=atividades())
                st.session_state["objetivos"] = adicionar_objetivo(st.session_state.get("objetivos", []), novo)
            except ValueError as exc:
                st.error(str(exc))
    for i, objetivo in enumerate(st.session_state.get("objetivos", [])):
        c1, c2 = st.columns([5, 1])
        c1.write("• " + objetivo["descricao"])
        if c2.button("Remover", key=f"remover_{i}"):
            st.session_state["objetivos"] = [o for j, o in enumerate(st.session_state["objetivos"]) if j != i]
            st.rerun()

    st.subheader("Perguntas para conversar")
    with st.form("reflexao", clear_on_submit=True):
        pergunta = st.selectbox("Pergunta", PERGUNTAS)
        resposta = st.text_area("O que conversamos (opcional, fica só nesta sessão)", max_chars=500)
        if st.form_submit_button("Guardar reflexão"):
            try:
                st.session_state["reflexoes"] = registrar_reflexao(st.session_state.get("reflexoes", []), pergunta, resposta)
            except ValueError as exc:
                st.error(str(exc))
    for item in st.session_state.get("reflexoes", []):
        st.write(f"**{item['pergunta']}**  \n{item['resposta']}")
    st.link_button("Conhecer o plano de mídia familiar da AAP (em inglês)", "https://www.healthychildren.org/English/family-life/Media/Pages/How-to-Make-a-Family-Media-Use-Plan.aspx")


def saiba_mais():
    conteudo = carregar_conteudo()
    st.title("Saiba mais")
    st.info(conteudo["aviso"])
    for secao in conteudo["secoes"]:
        st.subheader(secao["titulo"])
        st.markdown("\n".join("- " + item for item in secao["itens"]))
        for chave in secao.get("fontes", []):
            fonte = conteudo["fontes"][chave]
            st.markdown(f"Fonte: [{fonte['nome']}]({fonte['url']})")


def pesquisa():
    st.title("A pesquisa por trás do projeto")
    st.write("O estudo explora dados da National Survey of Children’s Health dos Estados Unidos de 2020 a 2024. A pesquisa reúne relatos de responsáveis e não acompanha as mesmas crianças ao longo do tempo.")
    st.write("O artigo compara associações amostrais com uma análise complementar que considera o desenho da NSCH. A classificação de relatos foi avaliada em 2024 após uma revisão de protocolo. O diário funciona de forma independente dessas análises.")
    st.write("O estudo explora dados da National Survey of Children’s Health dos Estados Unidos de 2020 a 2024. A pesquisa reúne relatos de "
             "responsáveis e não acompanha as mesmas crianças ao longo do tempo.")
    try:
        resultados = carregar_resultados_pesquisa(caminho_resultados_pesquisa(ROOT), MANIFEST)
    except (FileNotFoundError, KeyError, ValueError):
        st.info("Os resultados da análise de contribuição ainda não foram gerados ou não correspondem aos dados atuais. "
                "Execute `python -m mindscreen.contribuicao` e consulte `docs/contribuicao-incremental.md`.")
        return
    resumo = resultados["resumo"]
    st.subheader("A pergunta")
    st.write(resumo["pergunta"])
    st.success(resumo["mensagem_principal"])
    sobre = sobreposicao(resultados["contribuicoes"])
    abas = st.tabs([b["rotulo"].capitalize() for b in resumo["blocos"]])
    for i, (aba, bloco) in enumerate(zip(abas, resumo["blocos"])):
        with aba:
            st.markdown("\n".join("- " + f for f in bloco["frases"]))
            tipo = st.radio("Contribuição de cada fator", ["incremental", "isolado"], horizontal=True, key=f"tipo_{i}",
                            format_func={"incremental": "Além dos demais fatores", "isolado": "Sozinho (só com idade e sexo)"}.get)
            st.plotly_chart(contribution_chart(resultados["contribuicoes"], bloco["target"], resumo["modelo"], tipo), width="stretch")
            s = sobre.loc[sobre.target.eq(bloco["target"]) & sobre.modelo.eq(resumo["modelo"]) & sobre.fator.eq("SCREENTIME")].iloc[0]
            st.write(f"Sozinho, o tempo de tela parece contribuir mais ({num(s.delta_isolado, 3)}). Quando sono, atividade física e amizades já estão "
                     f"no modelo, restam cerca de {s.fracao_que_permanece:.0%} dessa contribuição ({num(s.delta_incremental, 3)}): boa parte do que o tempo de tela "
                     "informa já aparece no restante da rotina. Isso não mostra qual hábito influencia qual.")
            st.caption("Cada ponto mostra quanto a capacidade de ordenação (ROC AUC) muda com o fator. "
                       "A linha horizontal é o intervalo de 95%. ROC AUC 0,5 é o acaso; 1 é a ordenação perfeita.")
    st.subheader("Como é a rotina de crianças e adolescentes na NSCH")
    variavel = st.selectbox("Fator de rotina", list(ROTINA_ROTULOS), format_func=ROTINA_ROTULOS.get)
    st.plotly_chart(routine_profile_chart(resultados["perfil"], variavel), width="stretch")
    st.caption("Percentuais ponderados pelos pesos da pesquisa (estimativas pontuais, sem intervalos). Descrevem crianças e adolescentes de 6 a 17 anos "
               "nos Estados Unidos e não servem de referência para avaliar uma família específica.")
    st.subheader("Limites destes achados")
    st.markdown("\n".join("- " + l for l in resumo["limites"]))
    st.write("O diário do aplicativo foi criado para reflexão: seus registros não fazem parte da NSCH e ainda não foram avaliados em um estudo com famílias.")
    st.link_button("Conhecer os dados oficiais da NSCH", "https://www.census.gov/programs-surveys/nsch/data/datasets.html")


def avaliar():
    st.title("Avaliar o protótipo")
    st.write("Sua opinião ajuda a decidir se vale a pena continuar desenvolvendo o protótipo. As respostas ficam só nesta sessão; "
             "se quiser compartilhá-las com a equipe, baixe o arquivo abaixo e envie por um canal combinado com a pesquisa.")
    with st.form("avaliacao"):
        notas = {chave: st.select_slider(texto + " (1 = discordo totalmente, 5 = concordo totalmente)", options=ESCALA, value=3, key=f"nota_{chave}")
                 for chave, texto in AVALIACAO.items()}
        voltaria = st.radio("Você voltaria a usar o protótipo?", VOLTARIA, index=None, horizontal=True)
        comentario = st.text_area("Comentário (opcional)", max_chars=500)
        if st.form_submit_button("Guardar avaliação"):
            try:
                st.session_state["avaliacao_prototipo"] = criar_avaliacao(notas, voltaria, comentario)
                st.success("Avaliação guardada nesta sessão.")
            except ValueError as exc:
                st.error(str(exc))


def main():
    with st.sidebar:
        st.header("🌱 MindScreen")
        pagina = st.radio("Navegação", PAGINAS)
        st.divider()
        st.button("Apagar dados desta sessão", on_click=limpar_sessao)
        st.download_button("Baixar meus dados (JSON)", file_name="mindscreen_rotina.json", mime="application/json",
                           data=exportar(st.session_state.get("registros_rotina", []), st.session_state.get("objetivos", []),
                                         st.session_state.get("plano_salvo", []), st.session_state.get("reflexoes", []),
                                         st.session_state.get("avaliacao_prototipo")))
        st.caption("Os dados do diário são temporários e não ficam salvos para a próxima sessão. O arquivo é gerado só quando você o baixa.")
    {"Início": inicio, "Diário de rotina": diario, "Histórico": ver_historico, "Plano em família": plano,
     "Saiba mais": saiba_mais, "Pesquisa": pesquisa, "Avaliar o protótipo": avaliar}[pagina]()


main()
