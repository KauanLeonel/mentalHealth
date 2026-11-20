# Modelos, explicabilidade e contribuição preditiva de SCREENTIME

Cinco folds estratificados idênticos por target em 2020–2023; seleção da família por ROC AUC CV; limiar de cada modelo escolhido pelo máximo F1 nas previsões fora do fold de 2020–2023 e congelado antes do teste. Teste: todos os elegíveis de 2024, com exclusão apenas do target indeterminado. Métricas amostrais não ponderadas.

PR-AUC operacionalizada por Average Precision (AP), sem interpolação linear.

F1, recall e precisão usam o limiar de cada modelo escolhido na validação cruzada de 2020–2023 (máximo F1 fora do fold), sem consultar 2024. As métricas são amostrais e não ponderadas; intervalos de 95% vêm de bootstrap pareado dos registros de 2024 e não incorporam o desenho complexo da pesquisa. O modelo escolhido é o de maior ROC AUC na validação cruzada de desenvolvimento, mesmo que outro tenha desempenho temporal superior.

## Comparação por desfecho

### depressao_atual
- Selecionado em A por CV: xgboost. ROC AUC 2024: 0.838808; PR-AUC/AP: 0.327247; F1: 0.377160; limiar 0.1751 (recall 0.5077, precisão 0.3000).
- Selecionado em B por CV: xgboost. ROC AUC 2024: 0.834562; PR-AUC/AP: 0.322299; F1: 0.380846.
- Comparando a mesma família xgboost, A − B: ROC AUC +0.004247; PR-AUC/AP +0.004948; F1 -0.003687.
- IC 95% bootstrap (1000 reamostras): ROC AUC A [0.8318; 0.8465]; A − B ROC AUC [+0.0027; +0.0057]; A − B AP [+0.0009; +0.0087].
- O IC 95% bootstrap da diferença de ROC AUC A − B fica inteiramente acima de zero: o ganho preditivo de SCREENTIME é pequeno, mas distinguível de zero nesta amostra. F1 no limiar escolhido por CV não melhorou.
- Maiores atribuições globais médias absolutas de SHAP: SC_AGE_YEARS, MAKEFRIEND, SCREENTIME.
- SHAP da classe 1, método TreeExplainer interventional (margem), unidade log-odds da classe 1, 1000 observações de 2024 e 100 referências de desenvolvimento.
- Erro máximo da verificação de aditividade: 3.8480048e-06.
- Categoria SCREENTIME 1: contribuição SHAP média -0.209022 (62 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 2: contribuição SHAP média -0.349912 (122 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 3: contribuição SHAP média -0.076608 (262 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 4: contribuição SHAP média +0.045351 (200 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 5: contribuição SHAP média +0.336932 (344 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME ausente: contribuição SHAP média +0.021341 (10 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.

### ansiedade_atual
- Selecionado em A por CV: xgboost. ROC AUC 2024: 0.760638; PR-AUC/AP: 0.449776; F1: 0.462464; limiar 0.2330 (recall 0.5425, precisão 0.4030).
- Selecionado em B por CV: xgboost. ROC AUC 2024: 0.757732; PR-AUC/AP: 0.447682; F1: 0.461844.
- Comparando a mesma família xgboost, A − B: ROC AUC +0.002906; PR-AUC/AP +0.002094; F1 +0.000620.
- IC 95% bootstrap (1000 reamostras): ROC AUC A [0.7538; 0.7670]; A − B ROC AUC [+0.0014; +0.0044]; A − B AP [+0.0006; +0.0037].
- O IC 95% bootstrap da diferença de ROC AUC A − B fica inteiramente acima de zero: o ganho preditivo de SCREENTIME é pequeno, mas distinguível de zero nesta amostra.
- Maiores atribuições globais médias absolutas de SHAP: MAKEFRIEND, SC_AGE_YEARS, SC_SEX.
- SHAP da classe 1, método TreeExplainer interventional (margem), unidade log-odds da classe 1, 1000 observações de 2024 e 100 referências de desenvolvimento.
- Erro máximo da verificação de aditividade: 1.5430493e-06.
- Categoria SCREENTIME 1: contribuição SHAP média -0.291077 (63 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 2: contribuição SHAP média -0.180326 (141 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 3: contribuição SHAP média -0.090645 (256 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 4: contribuição SHAP média +0.033397 (234 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME 5: contribuição SHAP média +0.180071 (298 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.
- Categoria SCREENTIME ausente: contribuição SHAP média -0.203101 (8 observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.

## Calibração das pontuações

Método escolhido por modelo pelo menor Brier nas previsões fora do fold de 2020–2023 (calibração cruzada); limiar escolhido depois, sobre as pontuações calibradas. Os números de 2024 abaixo são descritivos e não orientaram nenhuma escolha. brier_skill > 0 indica Brier melhor que prever a prevalência observada; intercepto e inclinação de Cox ideais: 0 e 1; ECE em bins de quantis.

### depressao_atual
- logistic (método isotonica): Brier 0.1685 → 0.0536 (Brier de prever a prevalência: 0.0634); brier_skill -1.656 → +0.156; média prevista 0.358 → 0.071 (observada 0.068); ECE 0.290 → 0.004; inclinação de Cox 0.93 → 0.98.
- random_forest (método sigmoide): Brier 0.1668 → 0.0536 (Brier de prever a prevalência: 0.0634); brier_skill -1.630 → +0.156; média prevista 0.360 → 0.071 (observada 0.068); ECE 0.292 → 0.004; inclinação de Cox 1.08 → 0.99.
- xgboost ★ (método sigmoide): Brier 0.0534 → 0.0534 (Brier de prever a prevalência: 0.0634); brier_skill +0.158 → +0.158; média prevista 0.071 → 0.071 (observada 0.068); ECE 0.004 → 0.003; inclinação de Cox 0.98 → 0.99.

### ansiedade_atual
- logistic (método isotonica): Brier 0.1936 → 0.1208 (Brier de prever a prevalência: 0.1435); brier_skill -0.349 → +0.158; média prevista 0.432 → 0.158 (observada 0.174); ECE 0.259 → 0.016; inclinação de Cox 0.96 → 0.96.
- random_forest (método sigmoide): Brier 0.1921 → 0.1206 (Brier de prever a prevalência: 0.1435); brier_skill -0.338 → +0.160; média prevista 0.432 → 0.158 (observada 0.174); ECE 0.258 → 0.015; inclinação de Cox 1.03 → 0.97.
- xgboost ★ (método sigmoide): Brier 0.1930 → 0.1203 (Brier de prever a prevalência: 0.1435); brier_skill -0.345 → +0.162; média prevista 0.431 → 0.158 (observada 0.174); ECE 0.257 → 0.015; inclinação de Cox 0.99 → 0.97.

## Associação ajustada
OR condicional da amostra em casos completos, sem pesos, erros padrão ou IC. Categoria de referência: menos de 1 hora. Ajuste simultâneo por idade, sexo, sono, atividade física, amizade e ano. Não estima risco relativo, efeito causal ou inferência para população. Covariáveis contemporâneas podem ser mediadoras ou consequências do desfecho; o ajuste não elimina confundimento.

- depressao_atual, categoria 2 vs 1: OR 0.9667 (n=124795).
- depressao_atual, categoria 3 vs 1: OR 1.2152 (n=124795).
- depressao_atual, categoria 4 vs 1: OR 1.3739 (n=124795).
- depressao_atual, categoria 5 vs 1: OR 1.7891 (n=124795).
- ansiedade_atual, categoria 2 vs 1: OR 1.1338 (n=124299).
- ansiedade_atual, categoria 3 vs 1: OR 1.2723 (n=124299).
- ansiedade_atual, categoria 4 vs 1: OR 1.4305 (n=124299).
- ansiedade_atual, categoria 5 vs 1: OR 1.6534 (n=124299).

## Limitações

SHAP explica a função do modelo e sua referência de desenvolvimento; não é causalidade, efeito de intervenção ou diagnóstico. Atribuições dependem da correlação entre atributos, agrupamento de one-hot e background. Compare rankings entre modelos; magnitudes em escalas diferentes não são diretamente comparáveis.
As magnitudes SHAP em log-odds e em probabilidade não devem ser comparadas diretamente entre modelos.
A ablation mede desempenho incremental sob duas buscas comparáveis; não mede efeito causal da exposição. Diferenças pequenas ou discordantes entre métricas não demonstram ganho robusto. O teste de 2024 não deve ser reutilizado para ajustar decisões após observar estes resultados.
Transparência: a revisão do protocolo (scale_pos_weight no XGBoost e limiar por CV) foi motivada pelo baixo recall observado na primeira avaliação de 2024. As escolhas em si usam apenas 2020–2023, mas 2024 deixou de ser um teste completamente cego; a execução anterior está preservada em models/experimentos_v1_limiar05 e reports/modelagem/v1_limiar05.
As pontuações foram calibradas pós-hoc com previsões fora do fold de 2020–2023 (método escolhido pelo menor Brier na validação cruzada). Elas aproximam a frequência amostral não ponderada do relato na pesquisa entre perfis semelhantes; não são probabilidade clínica individual. O SHAP continua explicando a pontuação antes da calibração, que é monotônica e não altera a ordenação.
Resultados dependem do relato de responsáveis na pesquisa dos Estados Unidos e não são automaticamente transportáveis a indivíduos ou à população brasileira.
O universo e algumas instruções variaram entre edições; consulte docs/harmonizacao.md. Ausência de dados pode introduzir seleção. Os resultados não estabelecem que o uso de telas provoca depressão ou ansiedade.
