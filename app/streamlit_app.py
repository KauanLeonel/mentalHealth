"""Interface de apresentação. Processamento e inferência pertencem a mindscreen."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st

from mindscreen.dados_validados import TARGETS, load_dataset
from mindscreen.harmonizacao import sha256
from mindscreen.inferencia import predict_profile
from mindscreen.painel import (LABELS, distribution_chart, filter_frame, json_result, load_figure,
                              outcome_by, overview)

st.set_page_config(page_title="MindScreen AI", page_icon="🧠", layout="wide")
st.markdown("""<style>
.block-container {max-width:1280px;padding-top:2rem;padding-bottom:3rem;}
div[data-testid="stMetric"] {background:white;border:1px solid #e4e7f0;border-radius:14px;padding:18px;}
h1 {letter-spacing:-0.035em;} h2 {letter-spacing:-0.02em;}
section[data-testid="stSidebar"] {border-right:1px solid #e4e7f0;}
</style>""", unsafe_allow_html=True)

MANIFEST = ROOT / "data/processed/manifesto.json"
REGISTRY = ROOT / "models/experimentos/registro.json"
FIGURES = ROOT / "reports/figures"
NOTICE = "Projeto acadêmico. As saídas são estimativas estatísticas de respostas declaradas por responsáveis na pesquisa norte-americana NSCH. A ferramenta não realiza diagnósticos e não é um instrumento clínico validado."


@st.cache_data(show_spinner="Carregando dados validados…", max_entries=1)
def cached_data(manifest_hash, dataset_hash):
    return load_dataset(MANIFEST)


def figure(name):
    path = FIGURES / (name + ".json")
    if path.exists():
        st.plotly_chart(load_figure(path), width="stretch")
    else:
        st.info("Esta figura ainda não foi gerada. Execute a rotina de análises.")


def result(name, manifest):
    return json_result(ROOT / "reports" / name, manifest["sha256"])


def page_overview(frame, manifest):
    st.caption("PESQUISA ACADÊMICA · NSCH 2020–2024")
    st.title("MindScreen AI")
    st.markdown("### Tempo de tela, saúde mental e evidências observacionais")
    st.write("Analisamos a associação entre exposição a telas e relatos atuais de depressão e ansiedade em crianças e adolescentes de 6 a 17 anos, com dois problemas independentes de classificação.")
    info = overview(frame)
    cols = st.columns(3)
    cols[0].metric("Registros analisados", f"{info['registros']:,}".replace(",", "."))
    cols[1].metric("Edições incluídas", len(info["anos"]))
    cols[2].metric("População do estudo", "6–17 anos")
    left, right = st.columns(2)
    with left:
        st.subheader("Dados e objetivos")
        st.write("Fonte: National Survey of Children’s Health, U.S. Census Bureau. O dataset harmonizado preserva ano, peso amostral e variáveis do desenho; respostas indeterminadas não são convertidas em negativas.")
        st.link_button("Documentação oficial do NSCH", "https://www.census.gov/programs-surveys/nsch.html")
    with right:
        st.subheader("Modelos e protocolo")
        st.write("Regressão logística, Random Forest e XGBoost, com DummyClassifier como referência. Desenvolvimento em 2020–2023; avaliação temporal em 2024. A escolha usa validação cruzada de desenvolvimento.")
    path = ROOT / "reports/resultados/resumo.json"
    if path.exists():
        summary = result("resultados/resumo.json", manifest)
        st.subheader("Resultados efetivamente obtidos")
        for target, item in summary["targets"].items():
            st.markdown(f"**{LABELS[target]} · {item['modelo_selecionado_A']}**")
            st.write(item["interpretacao"])
            st.caption(f"Diferença A − B na mesma família: ROC AUC {item['delta_mesma_familia_roc_auc']:+.4f}; PR-AUC/AP {item['delta_mesma_familia_pr_auc']:+.4f}.")
    else:
        st.info("Os resultados dos modelos ainda não foram gerados. Nenhuma métrica demonstrativa é apresentada.")
    st.warning("Associação não estabelece causalidade. Diferenças de redação e de universo entre edições estão documentadas no relatório metodológico.")


def page_eda(frame, manifest):
    st.title("Análise exploratória")
    st.caption("Contagens e proporções amostrais não ponderadas · sem intervalos de confiança populacionais")
    with st.expander("Filtros da amostra", expanded=True):
        cols = st.columns(3)
        years = cols[0].multiselect("Anos", [2020, 2021, 2022, 2023, 2024], default=[2020, 2021, 2022, 2023, 2024])
        ages = cols[1].slider("Faixa etária", 6, 17, (6, 17))
        sexes = cols[2].multiselect("Sexo informado", [1, 2], default=[1, 2], format_func=lambda x: manifest["rotulos"]["SC_SEX"][str(x)])
    filtered = filter_frame(frame, years, ages, sexes)
    st.metric("Registros após os filtros", f"{len(filtered):,}".replace(",", "."))
    if filtered.empty:
        st.info("Nenhum registro corresponde aos filtros.")
        return
    cols = st.columns(2)
    for index, name in enumerate(["SCREENTIME", "faixa_etaria", "SC_AGE_YEARS", "SC_SEX", "HOURSLEEP", "PHYSACTIV", "MAKEFRIEND"]):
        with cols[index % 2]:
            st.plotly_chart(distribution_chart(filtered, name, manifest), width="stretch")
    target = st.selectbox("Desfecho exploratório", TARGETS, format_func=lambda t: LABELS[t])
    st.plotly_chart(distribution_chart(filtered, target, manifest), width="stretch")
    variable = st.selectbox("Comparar o desfecho com", ["SCREENTIME", "ano", "SC_AGE_YEARS", "SC_SEX", "HOURSLEEP", "PHYSACTIV", "BULLIED_R", "BULLY", "MAKEFRIEND"], format_func=lambda t: LABELS.get(t, t))
    table = outcome_by(filtered, variable, target, manifest["rotulos"].get(variable))
    st.plotly_chart(px.bar(table, x=variable, y="proporcao_amostral", hover_data=["n", "positivos"], title="Proporção amostral com relato atual (target determinado)"), width="stretch")
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("O denominador exclui indeterminação do próprio target. Categorias ausentes do fator são exibidas separadamente. Pesos FWC são preservados no dataset; estas visualizações não aplicam ponderação nem inferência para desenho complexo.")


def page_models(manifest):
    st.title("Comparação dos modelos")
    evaluation = result("avaliacao/avaliacao.json", manifest)
    table = pd.DataFrame(evaluation["metricas"])
    target = st.selectbox("Desfecho", TARGETS, format_func=lambda t: LABELS[t])
    experiment = st.radio("Experimento", ["A", "B"], horizontal=True, format_func=lambda x: "A · com SCREENTIME" if x == "A" else "B · sem SCREENTIME")
    selected = table.loc[table.target.eq(target) & table.experimento.eq(experiment)]
    st.write(evaluation["protocolo"])
    st.caption(evaluation["pr_auc_definicao"])
    st.dataframe(selected[["modelo", "selecionado_cv", "roc_auc_cv", "roc_auc", "pr_auc", "precision", "recall", "f1", "specificity", "balanced_accuracy", "n"]], hide_index=True, width="stretch")
    chosen = selected.loc[selected.selecionado_cv, "modelo"].iloc[0]
    st.success(f"Modelo escolhido por validação cruzada em 2020–2023: {chosen}.")
    cols = st.columns(2)
    with cols[0]:
        figure(f"{experiment}_{target}_roc")
    with cols[1]:
        figure(f"{experiment}_{target}_pr")
    model = st.selectbox("Matriz de confusão do algoritmo", selected.modelo.tolist(), index=selected.modelo.tolist().index(chosen))
    figure(f"{experiment}_{target}_{model}_confusao")
    st.caption("Resultados de 2024 são descritivos do teste final. Não devem ser usados para escolher o modelo ou ajustar o limiar.")


def page_simulator(manifest):
    st.title("Simulador de pesquisa")
    st.warning(NOTICE)
    rules = json.loads((ROOT / "configs/harmonizacao.json").read_text(encoding="utf-8"))
    features = manifest["preditores_numericos"] + manifest["preditores_categoricos"]
    st.write("Escolha categorias do questionário para explorar a saída dos modelos. Nenhuma informação do formulário é gravada em arquivo ou usada para treinar modelos.")
    with st.form("perfil_pesquisa"):
        cols = st.columns(2)
        profile = {}
        for i, name in enumerate(features):
            with cols[i % 2]:
                if name == "SC_AGE_YEARS":
                    profile[name] = st.number_input("Idade em anos", min_value=6, max_value=17, value=12, step=1, key="perfil_" + name)
                else:
                    labels = manifest["rotulos"][name]
                    profile[name] = st.selectbox(LABELS.get(name, name), rules["dominios"][name], format_func=lambda x, lab=labels: lab[str(x)], key="perfil_" + name)
        submitted = st.form_submit_button("Executar simulação", type="primary")
    if submitted:
        predictions = predict_profile(profile, manifest, rules, REGISTRY)
        cols = st.columns(2)
        for col, (target, prediction) in zip(cols, predictions.items()):
            with col:
                st.subheader(LABELS[target])
                st.metric("Rótulo previsto na tarefa de pesquisa", str(prediction["classe_pesquisa"]))
                st.write(f"Pontuação bruta do classificador: **{prediction['score']:.4f}**")
                st.caption(f"Modelo: {prediction['modelo']}. Classe 1 corresponde ao relato de condição atual na pesquisa; classe 0 à ausência atual segundo as regras documentadas.")
        st.info("Pontuações não calibradas: não interprete os números como probabilidades individuais de doença. A classificação não determina se uma pessoa está clinicamente doente e não orienta condutas médicas.")


def page_explanations(manifest):
    st.title("Explicabilidade e contribuição do tempo de tela")
    summary = result("figures/explicabilidade.json", manifest)
    target = st.selectbox("Desfecho explicado", TARGETS, format_func=lambda t: LABELS[t])
    data = summary["targets"].get(target, {})
    if data.get("disponivel"):
        st.caption(f"Classe explicada: 1 · {data['metodo']} · {data['unidade']} · amostra de {data['n_amostra']} registros de avaliação")
        figure(target + "_importancia")
        figure(target + "_beeswarm")
        st.caption("No beeswarm, cada ponto é uma contribuição de um registro; azul representa valores menores e vermelho, maiores, dentro de cada variável. As cores de categorias são apenas ordenações dos códigos.")
        with st.expander("Contribuição individual de um registro real da avaliação"):
            figure(target + "_individual")
            st.json(data["exemplo"]["valores_questionario"])
        st.subheader("Categorias de SCREENTIME na amostra explicada")
        st.dataframe(pd.DataFrame(data["screentime"]), hide_index=True, width="stretch")
    else:
        st.info("SHAP não está disponível para este modelo. Consulte o relatório de compatibilidade.")
    st.write(summary["limitacoes"])
    st.subheader("Experimentos com e sem SCREENTIME")
    evaluation = result("avaliacao/avaliacao.json", manifest)
    ablation = pd.DataFrame(evaluation["ablation"])
    st.dataframe(ablation.loc[ablation.target.eq(target)], hide_index=True, width="stretch")
    figure(target + "_ablation")
    st.caption("Diferenças A − B com protocolos comparáveis. Valores positivos não constituem prova de ganho estatisticamente significativo ou de causalidade.")
    st.subheader("Associação logística ajustada")
    association = result("associacao/associacao.json", manifest)
    st.write(association["interpretacao"])
    table = pd.DataFrame(association["odds_ratios"])
    st.dataframe(table.loc[table.target.eq(target)], hide_index=True, width="stretch")
    figure("odds_ratios")


def main():
    with st.sidebar:
        st.markdown("## 🧠 MindScreen AI")
        st.caption("CIÊNCIA DE DADOS · SAÚDE MENTAL")
        page = st.radio("Navegação", ["Visão geral", "Análise exploratória", "Comparação dos modelos", "Simulador", "Explicabilidade"])
        st.divider()
        st.caption("NSCH · 2020–2024\n\nEstudo observacional acadêmico")
    try:
        descriptor = json.loads(MANIFEST.read_text(encoding="utf-8"))
        dataset = MANIFEST.parent / descriptor["dataset"]
        manifest, frame = cached_data(sha256(MANIFEST), sha256(dataset))
    except Exception:
        st.error("Dados analíticos indisponíveis ou integridade não confirmada. Execute a harmonização e consulte a documentação do projeto.")
        return
    try:
        if page == "Visão geral":
            page_overview(frame, manifest)
        elif page == "Análise exploratória":
            page_eda(frame, manifest)
        elif page == "Comparação dos modelos":
            page_models(manifest)
        elif page == "Simulador":
            page_simulator(manifest)
        else:
            page_explanations(manifest)
    except Exception:
        st.warning("Os artefatos desta página estão ausentes, incompatíveis ou com integridade não confirmada. Execute a rotina de análises e consulte os relatórios técnicos.")
    st.divider()
    st.caption(NOTICE)


main()
