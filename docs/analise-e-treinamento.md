# Análise e treinamento: contrato e limitações

Os CSVs em `Dados/` são as fontes. A rotina `python -m mindscreen.harmonizacao` cria o dataset analítico e seu manifesto após aplicar as regras e verificações em `docs/harmonizacao.md`. Consulte `reports/harmonizacao/qualidade.md` para os anos efetivamente incluídos, as contagens e limitações. A validação do manifesto é técnica e automatizada, com preditores iniciais declarados; não representa aprovação humana pelo orientador. Não se deve marcar como validado um arquivo que não passou pelas verificações.

A rotina de harmonização gera o manifesto automaticamente. O esquema abaixo serve para entender seu contrato; não é necessário preenchê-lo manualmente. O caminho de `dataset` é relativo ao manifesto, e seu SHA-256 é calculado a partir do arquivo produzido. A documentação e o responsável devem apontar para uma validação real, explicitando quando é automatizada. O hash não comprova qualidade científica: ele vincula o manifesto aos bytes revisados. Os nomes das colunas devem corresponder exatamente ao Parquet. O dataset deve conter `ano`, `FWC`, `STRATUM`, `depressao_atual`, `ansiedade_atual` e as colunas de preditores aprovados; cada target deve ser 0, 1 ou ausente. As listas são uma autorização explícita de preditores, não uma seleção automática.

```json
{
  "validado": true,
  "aprovado_por": "responsável pela revisão",
  "documentacao_validacao": "referência da revisão metodológica",
  "dataset": "dataset.parquet",
  "sha256": "SHA-256 do arquivo validado",
  "classe_positiva": 1,
  "preditores_numericos": [],
  "preditores_categoricos": ["SCREENTIME"]
}
```

Adicione somente preditores revisados; a verificação automática barra as famílias de ambos os targets e nomes administrativos conhecidos, mas não consegue identificar todos os vazamentos indiretos. Preserve FWC e desenho no dataset, sem incluí-los como preditores. O exemplo é um esquema, não é uma aprovação de dados ou de preditores.

```powershell
python -m mindscreen.exploratoria --manifesto data/processed/manifesto.json
python -m mindscreen.treinamento --manifesto data/processed/manifesto.json --config configs/treinamento.json
```

A análise gera contagens e proporções amostrais não ponderadas, tabelas CSV e HTML Plotly, sem inferência populacional nem intervalos de confiança. Resultados descritivos de 2024 não devem orientar a escolha de modelos, preditores, thresholds ou hiperparâmetros. Consulte o guia do Census sobre desenho complexo antes de fazer inferência.

No treinamento, 2024 é reservado e não é usado para ajuste, seleção ou avaliação. Os modelos são escolhidos por ROC AUC média em cinco folds estratificados dos anos 2020–2023; imputação e codificação ocorrem dentro de cada fold. As opções de pesos de classe são comparadas para regressão logística, floresta e XGBoost; o limiar de decisão de cada modelo é escolhido pelas previsões fora do fold de 2020–2023 (ver `docs/explicabilidade-e-interface.md`). Os pesos amostrais não são usados no ajuste desta implementação inicial e não se afirma inferência populacional. Os modelos persistidos são as versões ajustadas no conjunto completo de desenvolvimento após busca. A avaliação temporal de 2024 ainda precisa ser implementada em etapa separada após congelar as escolhas. Nenhum resultado é diagnóstico ou prova de causalidade.

As versões instaladas dos quatro estimadores expõem `sample_weight` em `fit`; o log registra essa compatibilidade observada e confirma que o argumento não foi usado. Pesos de classe e pesos amostrais têm finalidades distintas, e a compatibilidade da API não valida inferência para o desenho complexo. O fluxo registra para cada target o número excluído por target ausente.

## Calibração das pontuações (pós-hoc)

Motivo: na versão 2, o Brier de 2024 da regressão logística e da floresta (`class_weight=balanced`) e o do XGBoost de ansiedade (`scale_pos_weight=5,51`) ficou pior que o do Dummy, porque as pontuações ficavam muito acima da prevalência. O limiar corrigia o recall, mas as pontuações não podiam ser lidas como frequências.

```powershell
python -m mindscreen.calibracao --manifesto data/processed/manifesto.json
```

Protocolo (`src/mindscreen/calibracao.py`, configuração em `configs/calibracao.json`):

1. Os pipelines de `models/experimentos` não são retreinados nem alterados: hiperparâmetros e seleção por ROC AUC continuam congelados.
2. Para cada modelo, as previsões fora do fold de 2020–2023 são refeitas com os mesmos cinco folds e a mesma semente do treinamento. A rotina confere se elas reproduzem o limiar registrado no treinamento e interrompe a execução se não reproduzirem.
3. Os métodos candidatos são `nenhum`, `sigmoide` (Platt sobre o logit) e `isotonica`. Cada um é avaliado por calibração cruzada: as pontuações do fold *k* são calibradas por um calibrador ajustado nos outros quatro folds. Escolhe-se o menor Brier.
4. O limiar maximiza o F1 nas pontuações calibradas fora do fold. O calibrador final é ajustado em todas as previsões fora do fold e salvo junto ao pipeline (`ModeloCalibrado`).
5. 2024 só é usado depois, para descrever o resultado. A avaliação também mostra 2024 sem calibração, para comparação, e nenhuma escolha é tomada a partir dela.

Saídas: `models/experimentos_calibrados/` (registro com `"calibrado": true`) e `reports/modelagem/v3_calibrada/calibracao/`, que contém `metricas_2024.csv`, `intervalos_bootstrap.csv`, `ablation.csv`, `calibracao_cv.csv` (métodos comparados em 2020–2023), `calibracao_2024.csv` (antes e depois) e `calibracao_curvas.json` (curvas de confiabilidade em bins de quantis). As métricas de calibração são Brier, Brier relativo à prevalência (`brier_skill`), log loss, média prevista contra prevalência, intercepto e inclinação de Cox, ECE e MCE.

Limitações: a calibração é monotônica, então ROC AUC, PR-AUC e ordenação ficam praticamente iguais (a isotônica pode criar empates). O SHAP continua explicando a pontuação bruta. A pontuação calibrada estima a frequência do relato na pesquisa, sem pesos amostrais, entre perfis semelhantes. Não é probabilidade individual de doença. Como 2024 já influenciou revisões anteriores do protocolo, ele não é um teste cego para esta etapa (ver `reports/modelagem/v2_limiar_cv/resultados`).

### Relatório e interface com os modelos calibrados

```powershell
python -m mindscreen.calibracao
python -m mindscreen.analises --models models/experimentos_calibrados --reports reports/modelagem/v3_calibrada --calibracao reports/modelagem/v3_calibrada/calibracao
```

`--reports` define a pasta da versão em `reports/modelagem/` (`avaliacao`, `associacao`, `figuras`, `resultados`); o padrão é `reports/modelagem/v2_limiar_cv`. A rotina recusa gravar relatórios de modelos calibrados em `reports/` ou em `reports/modelagem/v2_limiar_cv`, para não sobrescrever a versão 2. As classes persistidas ficam em `mindscreen.modelo_calibrado`, para que os artefatos possam ser carregados por qualquer processo.

A interface lê o registro de modelos e a pasta de relatórios de `configs/interface.json`. Para voltar à versão 2 sem calibração, use `{"registro": "models/experimentos/registro.json", "relatorios": "reports/modelagem/v2_limiar_cv"}`.
