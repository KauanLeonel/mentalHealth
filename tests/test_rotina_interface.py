from pathlib import Path
import tempfile
from uuid import uuid4


def test_fluxo_diario_plano_e_apagar(monkeypatch):
    def pasta_streamlit(*args, **kwargs):
        root = Path(".tmp").resolve()
        path = root / ("rotina-" + uuid4().hex)
        path.mkdir(parents=True)
        return str(path)

    with monkeypatch.context() as scope:
        scope.setattr(tempfile, "mkdtemp", pasta_streamlit)
        from streamlit.testing.v1 import AppTest
    script = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    app = AppTest.from_file(str(script), default_timeout=30).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Diário de rotina").run()
    app.number_input[0].set_value(2.5)
    next(button for button in app.button if button.label == "Guardar na sessão").click().run()
    assert not app.exception
    assert app.success
    app.sidebar.radio[0].set_value("Histórico").run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert app.dataframe[0].value.iloc[0]["Tela (h)"] == 2.5
    app.sidebar.radio[0].set_value("Plano em família").run()
    assert not app.exception
    app.multiselect[0].set_value(["Combinar momentos sem telas"]).run()
    assert app.multiselect[0].value == ["Combinar momentos sem telas"]
    app.sidebar.radio[0].set_value("Pesquisa").run()
    app.sidebar.radio[0].set_value("Plano em família").run()
    assert app.multiselect[0].value == ["Combinar momentos sem telas"]
    # Objetivo escolhido pela família aparece no plano e no progresso do histórico.
    app.selectbox[0].set_value("tela_max")
    app.number_input[0].set_value(2.0)
    next(button for button in app.button if button.label == "Incluir objetivo").click().run()
    assert not app.exception
    assert any("Até 2 h de tela recreativa por dia" in str(m.value) for m in app.markdown)
    app.sidebar.radio[0].set_value("Histórico").run()
    assert not app.exception
    assert len(app.dataframe) == 2
    for page in ["Saiba mais", "Pesquisa", "Avaliar o protótipo"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
    app.radio[0].set_value("Talvez")
    next(button for button in app.button if button.label == "Guardar avaliação").click().run()
    assert not app.exception
    assert app.session_state["avaliacao_prototipo"]["voltaria"] == "Talvez"
    app.sidebar.button[0].click().run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Histórico").run()
    assert not app.exception
    assert not app.dataframe
    assert "avaliacao_prototipo" not in app.session_state and "objetivos" not in app.session_state


def test_cards_e_voltar_navegam(monkeypatch):
    def pasta_streamlit(*args, **kwargs):
        path = Path(".tmp").resolve() / ("rotina-" + uuid4().hex)
        path.mkdir(parents=True)
        return str(path)

    with monkeypatch.context() as scope:
        scope.setattr(tempfile, "mkdtemp", pasta_streamlit)
        from streamlit.testing.v1 import AppTest
    script = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    app = AppTest.from_file(str(script), default_timeout=30).run()
    destinos = {"ir_diario": "Diário de rotina", "ir_plano": "Plano em família", "ir_historico": "Histórico", "ir_saiba": "Saiba mais"}
    for chave, pagina in destinos.items():
        app.button(key=chave).click().run()
        assert not app.exception
        assert app.sidebar.radio[0].value == pagina
        app.button(key="voltar").click().run()
        assert app.sidebar.radio[0].value == "Início"
