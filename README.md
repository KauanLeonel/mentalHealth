# MindScreen AI

Projeto acadêmico que investiga rotina digital e apresenta um protótipo de reflexão familiar. A pesquisa preservada analisa, de forma exploratória, tempo de tela e relatos de ansiedade e depressão na National Survey of Children's Health (NSCH), edições de 2020 a 2024. O protótipo não faz previsões individuais nem diagnósticos.

O projeto se organiza em duas perguntas:

1. **Pesquisa com a base atual** — qual é a contribuição incremental do tempo de tela, além de outras características de rotina, para a classificação exploratória de relatos atuais de ansiedade e depressão na NSCH? (`python -m mindscreen.contribuicao`, ver `docs/contribuicao-incremental.md`)
2. **Pesquisa com o produto** — uma plataforma de acompanhamento da rotina digital ajuda famílias a compreender seus hábitos e construir planos considerados úteis por elas? (estudo próprio ainda não realizado, ver `docs/estudo-com-usuarios.md`)

O aplicativo permite registrar voluntariamente tempo recreativo de tela, sono e atividades (inclusive as definidas pela família), ver o histórico da sessão, escolher combinados e objetivos familiares, responder perguntas de reflexão, ler conteúdo educativo com fontes, conhecer em linguagem simples os achados da pesquisa e avaliar o protótipo. Os dados permanecem apenas em memória durante a sessão e podem desaparecer ao recarregar ou desconectar; o aplicativo não os grava em arquivos ou banco de dados. Ainda não foi avaliado com famílias. O código e as análises anteriores permanecem disponíveis para pesquisa; associação não implica causalidade.

## Abrir o protótipo

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

O protótipo funciona sem carregar os microdados ou os classificadores. A interface anterior de pesquisa foi preservada em `app/pesquisa_streamlit.py` e não integra o fluxo familiar. Consulte `docs/rotina-digital.md` e `artigo/main.tex` para decisões e limitações.

## Instalação no Windows (PowerShell)

Requer Python 3.11 ou superior e acesso às dependências do projeto.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Caso utilize outra versão compatível, substitua `py -3.11` pelo interpretador desejado. Se a política local impedir a ativação, execute diretamente `.\.venv\Scripts\python.exe` nos comandos Python.

## Verificação e testes

```powershell
mindscreen
python -m mindscreen --version
python -m pytest
```

A CLI verifica a execução do pacote, não a disponibilidade de todas as dependências ou a validade dos dados.

## Organização

- `src/mindscreen/`: pacote Python, CLI e lógica de negócio.
- `app/`: protótipo familiar e interface de pesquisa preservada.
- `data/raw/`, `data/interim/`, `data/processed/`: dados originais, intermediários e processados, respectivamente.
- `configs/`: regras de harmonização e configurações de treinamento; `docs/`: decisões e documentação metodológica.
- `models/`, `reports/`: artefatos de modelos e relatórios (organização de `reports/` em `reports/README.md`).
- `tests/`: testes automatizados.

Os arquivos NSCH já existentes na raiz e em `Dados/` foram preservados. Antes de usar os microdados, planeje sua organização sem modificar arquivos existentes em `data/raw/`. Arquivos de dados e artefatos gerados são ignorados pelo Git, mas arquivos já rastreados continuam rastreados.

## Dados analíticos

A rotina abaixo lê os CSVs em `Dados/`, verifica controles publicados pelo Census, restringe a população a 6–17 anos, harmoniza categorias e constrói targets independentes. Preserva os originais e gera o manifesto automaticamente:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mindscreen.harmonizacao
```

Saídas em `data/processed/`: `dataset.parquet`, datasets por desfecho, arquivo separado dos componentes dos targets e `manifesto.json`. Os relatórios de qualidade, fluxo e disponibilidade ficam em `reports/harmonizacao/`. A validação é técnica e automatizada, com limitações registradas em `docs/harmonizacao.md`. Resultados anteriores não são sobrescritos; para reproduzir em novas pastas use `--saida data/processed/nova_execucao --relatorios reports/harmonizacao/nova_execucao`.

Para auditar os CSVs existentes em `Dados/` (ou arquivos SAS/Stata em outro diretório), execute:

```powershell
python -m mindscreen.auditoria --raw Dados --output reports/auditoria
```

Consulte `docs/auditoria-metodologia.md` para as limitações e fontes. A auditoria não valida automaticamente os arquivos nem produz dataset analítico.

As rotinas de análise exploratória e treinamento exigem um dataset analítico validado e um manifesto de integridade. O contrato e os comandos estão em `docs/analise-e-treinamento.md`.

Para converter os CSVs de `Dados/` para Parquet intermediário, sem alterar os originais:

```powershell
python -m mindscreen.converter
```

Os arquivos ficam em `data/interim/parquet/`. A conversão preserva os campos como texto, não valida nem harmoniza os dados e não constrói targets. Para outra pasta, use `--entrada CAMINHO --saida CAMINHO`; o comando não sobrescreve saídas existentes.
