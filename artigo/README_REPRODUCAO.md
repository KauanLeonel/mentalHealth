# Reprodução do artigo

Na raiz do repositório, em PowerShell, com ambiente existente e arquivos locais `Dados/` e `data/processed/`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_desenho_nsch.py tests/test_figura_artigo.py tests/test_rotina.py tests/test_rotina_interface.py
.\.venv\Scripts\python.exe -m mindscreen.desenho_nsch --saida artigo/resultados_reproducao/desenho_nsch_nova_execucao.json
.\.venv\Scripts\python.exe artigo/gerar_figura.py
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

A rotina de associação escreve na pasta indicada; escolha uma pasta nova para preservar saídas existentes. O manifesto valida o SHA-256 do Parquet. Para regenerar harmonização sem substituir produtos existentes consulte `docs/harmonizacao.md` e use `--saida` e `--relatorios` em diretórios novos. Os CSVs são dados públicos NSCH disponíveis no [Census](https://www.census.gov/programs-surveys/nsch/data/datasets.html); a exportação local e seu histórico precisam ser preservados e autenticados. Não se altera `data/raw`.

A análise complementar combina as colunas de desenho dos CSVs com o Parquet e verifica os respectivos hashes no manifesto. O JSON publicado é `artigo/resultados_reproducao/desenho_nsch.json`. Ele registra prevalências, denominadores, IC95%, análise de sensibilidade e VIF. O gerador lê o JSON publicado e a associação v2 em `reports/modelagem/v2_limiar_cv/associacao/associacao.json`. Grava os gráficos em `artigo/figuras/` com Pillow. A análise de desenho foi executada com SciPy 1.18.1 e não sobrescreve saídas existentes.

A tabela preditiva usa `reports/modelagem/v2_limiar_cv/avaliacao/metricas_2024.csv`. A calibração complementar usa `reports/modelagem/v3_calibrada/calibracao/calibracao_2024.csv`. Para conferir essas métricas com os modelos existentes, carregue os registros de `models/experimentos/` e `models/experimentos_calibrados/` por meio de `mindscreen.artefatos.load_model`. Use registros de 2024 com o desfecho determinado, os preditores e limiares do registro e `binary_metrics` de `mindscreen.avaliacao`. A comparação reutiliza modelos já ajustados.

Ambiente registrado em `reports/revisao/ambiente.json`: Python 3.14.0, pandas 3.1.1, numpy 2.5.4, scikit-learn 1.9.1 e pyarrow 26.0.1. Dependências fixadas constam em `configs/requirements-lock.txt`; verificar versões efetivas no ambiente em uso.

Os arquivos `sbc-template.sty` e `sbc.bst` fornecidos em `modelo/` foram copiados sem alteração para `artigo/`, junto ao documento principal. Com uma distribuição LaTeX e BibTeX instalada, execute em `artigo/`:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Os executáveis LaTeX e BibTeX não foram encontrados no ambiente local. No Overleaf, importe `artigo_mindscreen_revisao_cientifica_overleaf.zip` e selecione `main.tex` como documento principal, com pdfLaTeX. O pacote inclui o gráfico ponderado em sua subpasta. Confira os avisos, a legibilidade das tabelas e a última página. Consulte `pendencias_para_submissao.md` antes de submeter.
