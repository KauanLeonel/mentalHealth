# Modelos, explicabilidade e contribuição preditiva de SCREENTIME

Cinco folds estratificados idênticos por target em 2020–2023; limiar fixo 0.5; seleção por ROC AUC CV. Teste: todos os elegíveis de 2024, com exclusão apenas do target indeterminado. Métricas amostrais não ponderadas.

PR-AUC operacionalizada por Average Precision (AP), sem interpolação linear; área trapezoidal também registrada separadamente.

F1 usa limiar predefinido 0,5. As métricas são amostrais, não ponderadas, sem intervalos de confiança. O modelo escolhido é o de maior ROC AUC na validação cruzada de desenvolvimento, mesmo que outro tenha desempenho temporal superior.

## Comparação por desfecho

### depressao_atual
- Selecionado em A por CV: xgboost. ROC AUC 2024: 0.838808; PR-AUC/AP: 0.327247; F1: 0.158677.
- Selecionado em B por CV: xgboost. ROC AUC 2024: 0.834562; PR-AUC/AP: 0.322299; F1: 0.160352.
- Comparando a mesma família xgboost, A − B: ROC AUC +0.004247; PR-AUC/AP +0.004948; F1 -0.001675.
- SCREENTIME apresentou incremento pontual de ROC AUC temporal nesta comparação; sua relevância e incerteza não foram estabelecidas por um teste inferencial. F1 no limiar fixo não melhorou.
- SHAP indisponível para o modelo selecionado; consultar registro de compatibilidade.

### ansiedade_atual
- Selecionado em A por CV: xgboost. ROC AUC 2024: 0.761347; PR-AUC/AP: 0.450584; F1: 0.290643.
- Selecionado em B por CV: xgboost. ROC AUC 2024: 0.757765; PR-AUC/AP: 0.447106; F1: 0.275070.
- Comparando a mesma família xgboost, A − B: ROC AUC +0.003582; PR-AUC/AP +0.003478; F1 +0.015573.
- SCREENTIME apresentou incremento pontual de ROC AUC temporal nesta comparação; sua relevância e incerteza não foram estabelecidas por um teste inferencial.
- SHAP indisponível para o modelo selecionado; consultar registro de compatibilidade.

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
Os scores dos classificadores não foram calibrados. O simulador apresenta o rótulo de pesquisa e a pontuação bruta, sem alegar probabilidade clínica validada. Resultados dependem do relato de responsáveis na pesquisa dos Estados Unidos e não são automaticamente transportáveis a indivíduos ou à população brasileira.
O universo e algumas instruções variaram entre edições; consulte docs/harmonizacao.md. Ausência de dados pode introduzir seleção. Os resultados não estabelecem que o uso de telas provoca depressão ou ansiedade.
