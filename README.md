# MindScreen AI

Projeto acadêmico para analisar a associação entre tempo de exposição a telas e indicadores de saúde mental de crianças e adolescentes nos microdados do National Survey of Children's Health (NSCH), edições de 2020 a 2024. `SCREENTIME` é a variável principal de interesse. Os dois problemas de classificação binária serão independentes: presença atual de depressão e presença atual de ansiedade. Estão previstos Logistic Regression, Random Forest e XGBoost, com interface futura em Streamlit.

O projeto contém auditoria, harmonização, análise exploratória e pipelines de treinamento. A interface Streamlit permanece para uma etapa futura. Associação não implica causalidade e previsões não devem ser apresentadas como diagnósticos médicos.

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
- `app/`: futura interface Streamlit.
- `data/raw/`, `data/interim/`, `data/processed/`: dados originais, intermediários e processados, respectivamente.
- `configs/`: regras de harmonização e configurações de treinamento; `docs/`: decisões e documentação metodológica.
- `models/`, `reports/`: artefatos de modelos e relatórios.
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
