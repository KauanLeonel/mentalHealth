"""Protótipo de rotina digital; regras e validação estão em mindscreen.rotina."""
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import plotly.express as px
import streamlit as st
from mindscreen.rotina import ATIVIDADES, COMBINADOS, PERGUNTAS, criar_registro, historico, registrar

st.set_page_config(page_title="MindScreen | Rotina digital", page_icon="🌱", layout="wide")


def limpar_sessao():
    for key in ("registros_rotina", "plano_salvo", "combinados", "dia", "tela", "sono", "atividades"):
        st.session_state.pop(key, None)


def inicio():
    st.title("Uma rotina digital que faça sentido para sua família")
    st.write("Observe o dia a dia, converse sobre o que é importante e construa pequenos combinados em conjunto.")
    st.info("Este é um protótipo de pesquisa e ainda não foi avaliado com famílias. Ele não faz diagnósticos nem prevê condições de saúde.")
    st.subheader("Como usar")
    st.write("1. Registre o que quiser sobre um dia.  2. Explore seu histórico.  3. Escolha combinados e converse sobre eles.")
    st.caption("Os registros são voluntários, ficam na sessão em memória e podem desaparecer ao recarregar, desconectar ou reiniciar o aplicativo. Não são gravados pelo aplicativo em arquivos ou banco de dados. Evite inserir dados em dispositivos compartilhados.")


def diario():
    st.title("Diário de rotina")
    st.write("Preencha apenas o que fizer sentido. Tempo de tela refere-se ao uso recreativo estimado no dia; sono refere-se à noite anterior.")
    with st.form("registro"):
        dia = st.date_input("Data do registro", value=date.today(), max_value=date.today(), key="dia")
        c1, c2 = st.columns(2)
        tela = c1.number_input("Tempo recreativo de tela (horas)", min_value=0.0, max_value=24.0, value=None, step=0.5, placeholder="Opcional", key="tela")
        sono = c2.number_input("Sono na noite anterior (horas)", min_value=0.0, max_value=24.0, value=None, step=0.5, placeholder="Opcional", key="sono")
        atividades = st.multiselect("O que também fez nesse dia?", ATIVIDADES, key="atividades")
        salvar = st.form_submit_button("Guardar na sessão", type="primary")
    if salvar:
        try:
            item = criar_registro(dia, tela, sono, atividades)
            st.session_state["registros_rotina"] = registrar(st.session_state.get("registros_rotina", []), item)
            st.success("Registro guardado nesta sessão. Se já havia um registro para a data, ele foi atualizado.")
        except ValueError as exc:
            st.error(str(exc))
    st.caption("Não inclua nomes ou outras informações pessoais. Uma duração não informada continua vazia; zero significa que você informou zero.")


def ver_historico():
    st.title("Meu histórico nesta sessão")
    registros = st.session_state.get("registros_rotina", [])
    if not registros:
        st.info("Você ainda não adicionou registros. Use o Diário de rotina para começar.")
        return
    frame = historico(registros)
    for coluna, titulo, cor in [("tela_horas", "Tempo recreativo de tela", "#4c6fa5"), ("sono_horas", "Sono na noite anterior", "#6b8c65")]:
        pontos = frame.dropna(subset=[coluna])
        if not pontos.empty:
            fig = px.scatter(pontos, x="data", y=coluna, title=titulo, labels={"data": "Data", coluna: "Horas"}, color_discrete_sequence=[cor])
            fig.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(fig, width="stretch")
    tabela = frame.copy()
    tabela["data"] = tabela["data"].dt.strftime("%d/%m/%Y")
    tabela["atividades"] = tabela["atividades"].map(lambda xs: ", ".join(xs) if xs else "Não informado")
    tabela = tabela.rename(columns={"data": "Data", "tela_horas": "Tela (h)", "sono_horas": "Sono (h)", "atividades": "Atividades"})
    st.dataframe(tabela, hide_index=True, width="stretch")
    st.caption("Os pontos representam apenas os dias e valores informados. Eles não demonstram causas, tendências gerais ou diagnósticos.")


def plano():
    st.title("Plano em família")
    st.write("Conversem e escolham juntos o que desejam experimentar. Os combinados podem mudar quando deixarem de fazer sentido.")
    if "combinados" not in st.session_state:
        st.session_state["combinados"] = st.session_state.get("plano_salvo", [])
    def guardar_plano():
        st.session_state["plano_salvo"] = st.session_state["combinados"][:]
    st.multiselect("Combinados que queremos experimentar", COMBINADOS, key="combinados", on_change=guardar_plano)
    st.subheader("Perguntas para conversar")
    for pergunta in PERGUNTAS:
        st.write("• " + pergunta)
    st.link_button("Conhecer o plano de mídia familiar da AAP (em inglês)", "https://www.healthychildren.org/English/family-life/Media/Pages/How-to-Make-a-Family-Media-Use-Plan.aspx")


def pesquisa():
    st.title("A pesquisa por trás do projeto")
    st.write("O estudo explora dados da National Survey of Children’s Health dos Estados Unidos de 2020 a 2024. A pesquisa reúne relatos de responsáveis e não acompanha as mesmas crianças ao longo do tempo.")
    st.write("Os resultados de associação existentes são exploratórios e não ponderados. As análises de classificação foram avaliadas em 2024 após uma revisão de protocolo e não fundamentam uma previsão individual neste aplicativo.")
    st.write("O diário do aplicativo foi criado para reflexão: seus registros não fazem parte da NSCH e ainda não foram avaliados em um estudo com famílias.")
    st.link_button("Conhecer os dados oficiais da NSCH", "https://www.census.gov/programs-surveys/nsch/data/datasets.html")


def main():
    with st.sidebar:
        st.header("🌱 MindScreen")
        pagina = st.radio("Navegação", ["Início", "Diário de rotina", "Histórico", "Plano em família", "Pesquisa"])
        st.divider()
        st.button("Apagar dados desta sessão", on_click=limpar_sessao)
        st.caption("Os dados do diário são temporários e não ficam salvos para a próxima sessão.")
    {"Início": inicio, "Diário de rotina": diario, "Histórico": ver_historico, "Plano em família": plano, "Pesquisa": pesquisa}[pagina]()


main()
