"""Relatório de execução e memória somente quando solicitado via --junitxml."""

import json
from pathlib import Path
from time import perf_counter

START = perf_counter()


def pytest_sessionfinish(session, exitstatus):
    if not getattr(session.config.option, "xmlpath", None):
        return
    from mindscreen.ambiente import peak_memory_mb
    from mindscreen.dados_validados import safe_output
    output = safe_output(Path(session.config.option.xmlpath).parent)
    output.mkdir(parents=True, exist_ok=True)
    terminal = session.config.pluginmanager.get_plugin("terminalreporter")
    results = {name: len(items) for name, items in terminal.stats.items() if name}
    (output / "testes_execucao.json").write_text(json.dumps({"coletados": session.testscollected, "resultado_saida": int(exitstatus), "resultados": results,
                                                          "duracao_s": round(perf_counter() - START, 3), "pico_memoria_processo_testes_mb": peak_memory_mb()}, indent=2), encoding="utf-8")
