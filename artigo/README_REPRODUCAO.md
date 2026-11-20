# Reprodução do artigo

Na raiz do repositório, em PowerShell, com ambiente existente e arquivos locais `Dados/` e `data/processed/`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe artigo/gerar_figura.py
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
.\.venv\Scripts\python.exe -c "from mindscreen.associacao import run; run('data/processed/manifesto.json','artigo/resultados_reproducao')"
```

A rotina de associação escreve na pasta indicada; escolha uma pasta nova para preservar saídas existentes. O manifesto valida o SHA-256 do Parquet. Para regenerar harmonização sem substituir produtos existentes consulte `docs/harmonizacao.md` e use `--saida` e `--relatorios` em diretórios novos. Os CSVs são dados públicos NSCH disponíveis no [Census](https://www.census.gov/programs-surveys/nsch/data/datasets.html); a exportação local e seu histórico precisam ser preservados e autenticados. Não se altera `data/raw`.

A figura lê `reports/associacao/associacao.json` e grava `artigo/figuras/associacao.png`; a geração exige Pillow. As métricas preditivas usam os modelos e registros em `models/experimentos/` e `reports/avaliacao/`, vinculados ao mesmo hash. Sua interpretação e a exposição prévia ao ano de 2024 constam em `metodologia_e_decisoes.md`.

Ambiente registrado em `reports/revisao/ambiente.json`: Python 3.14.0, pandas 3.1.1, numpy 2.5.4, scikit-learn 1.9.1 e pyarrow 26.0.1. Dependências fixadas constam em `configs/requirements-lock.txt`; verificar versões efetivas no ambiente em uso.

Os arquivos `sbc-template.sty` e `sbc.bst` fornecidos em `modelo/` foram copiados sem alteração para `artigo/`, junto ao documento principal. Com uma distribuição LaTeX e BibTeX instalada, execute em `artigo/`:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Não foi possível testar esta sequência neste ambiente: os executáveis LaTeX e BibTeX não foram encontrados. Para compilar no Overleaf, crie ou abra um projeto pela extensão Overleaf Workshop ou pelo site e inclua `main.tex`, `referencias.bib`, `sbc-template.sty`, `sbc.bst` e `figuras/associacao.png`, preservando a subpasta; selecione `main.tex` como documento principal e pdfLaTeX como compilador. A extensão instalada permite abrir e compilar projetos remotos, mas sua instalação isolada não vincula automaticamente esta pasta a um projeto. Confira a sincronização antes de compilar e revise o PDF e os avisos. Consultar `pendencias_para_submissao.md` antes de submeter.
