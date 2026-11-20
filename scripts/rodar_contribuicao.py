"""Executa a análise de contribuição incremental (Pesquisa 1) mostrando uma barra de progresso.

Uso no PowerShell, a partir da raiz do projeto:

    .\\.venv\\Scripts\\python.exe scripts\\rodar_contribuicao.py
    .\\.venv\\Scripts\\python.exe scripts\\rodar_contribuicao.py --output reports\\modelagem\\v4_contribuicao_reexecucao

A rotina não sobrescreve resultados existentes: para reexecutar, informe uma nova pasta em --output.
Os demais argumentos são os mesmos de `python -m mindscreen.contribuicao` (--manifesto, --config, --sem-barra).
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mindscreen.contribuicao import main  # noqa: E402

if __name__ == "__main__":
    main()
