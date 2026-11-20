# Relatórios do MindScreen AI

Todos os relatórios são gerados pelos módulos de `src/mindscreen`. Nomes de pastas em português, minúsculas e com `_`.

```
reports/
├── auditoria/        auditoria dos dados brutos      (python -m mindscreen.auditoria)
├── harmonizacao/     qualidade e fluxo da harmonização (python -m mindscreen.harmonizacao)
├── exploratoria/     análise exploratória            (python -m mindscreen.exploratoria)
└── modelagem/        uma pasta por versão dos modelos
    ├── v1_limiar05/
    ├── v2_limiar_cv/
    ├── v3_calibrada/
    └── _avulsos/     execuções auxiliares sem versão de modelo registrada
```

## Estrutura padrão de cada versão em `modelagem/`

| Subpasta | Conteúdo | Gerado por |
|---|---|---|
| `avaliacao/` | `avaliacao.json`, `metricas_2024.csv`, `ablation.csv`, `intervalos_bootstrap.csv` | `mindscreen.experimentos` |
| `associacao/` | `associacao.json`, `odds_ratios.csv` | `mindscreen.associacao` |
| `figuras/` | gráficos Plotly (`.html` + `.json`), `explicabilidade.json` (SHAP), `plotly.min.js` | `mindscreen.explicabilidade`, `mindscreen.resultados` |
| `resultados/` | `interpretacao.md`, `resumo.json`, `resultados-treinamento.pdf` (e `.html`, quando houver) | `mindscreen.resultados`; PDF/HTML montados à parte |
| `calibracao/` | só em versões calibradas: `calibracao_cv.csv`, `calibracao_2024.csv`, `calibracao_curvas.json` e a avaliação dos modelos calibrados | `mindscreen.calibracao` |

Os quatro primeiros são gravados por `python -m mindscreen.analises --models <models/...> --reports reports/modelagem/<versao>`.

## Versões

| Pasta | Modelos | Descrição |
|---|---|---|
| `v1_limiar05/` | `models/experimentos_v1_limiar05` | Primeira execução: limiar fixo 0,5, XGBoost sem `scale_pos_weight`. Preservada para comparação. |
| `v2_limiar_cv/` | `models/experimentos` | Limiar escolhido na validação cruzada e balanceamento no XGBoost. Padrão de `mindscreen.analises`. |
| `v3_calibrada/` | `models/experimentos_calibrados` | Modelos da v2 com calibração de probabilidades. Usada pela interface (`configs/interface.json`). |

Diferenças de conteúdo entre versões refletem o que cada execução produziu e não foram preenchidas manualmente:

- `v1_limiar05`: sem `intervalos_bootstrap.csv` (o bootstrap foi adicionado depois); o SHAP falhou nessa execução (`disponivel: false` em `figuras/explicabilidade.json`), então não há gráficos de importância, beeswarm ou individual.
- `v2_limiar_cv`: sem `resultados-treinamento.html`.
- `v3_calibrada`: única com `calibracao/` e com figuras `*_calibracao`. Os arquivos de avaliação em `calibracao/` são idênticos aos de `avaliacao/`, porque `mindscreen.calibracao` também os grava.
- Os PDFs foram gerados antes da reorganização e podem citar caminhos antigos (`reports/avaliacao`, `reports/v3_calibrada`, `reports/_anterior_2026-11-19` etc.). A correspondência está na tabela abaixo.

## `_avulsos/`

- `shap_amostra_reduzida_2026-11-19/` (antiga `reports/explicabilidade_revisada`): SHAP do XGBoost do experimento A com amostra reduzida (128 registros, background de 64), gerado em 2026-11-19. O arquivo não registra se usa os modelos da v1 ou da v2, por isso não está atribuído a uma versão. Não é usado pela interface.

## Caminhos antigos

| Antes | Agora |
|---|---|
| `reports/_anterior_2026-11-19/` | `reports/modelagem/v1_limiar05/` |
| `reports/avaliacao/`, `associacao/`, `resultados/` | `reports/modelagem/v2_limiar_cv/...` |
| `reports/figures/` | `reports/modelagem/v2_limiar_cv/figuras/` |
| `reports/v3_calibrada/` (`figures/` → `figuras/`) | `reports/modelagem/v3_calibrada/` |
| `reports/avaliacao_calibrada/` | `reports/modelagem/v3_calibrada/calibracao/` |
| `reports/explicabilidade_revisada/` | `reports/modelagem/_avulsos/shap_amostra_reduzida_2026-11-19/` |
