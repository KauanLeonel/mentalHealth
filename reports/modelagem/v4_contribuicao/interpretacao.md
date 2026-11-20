# Contribuição incremental do tempo de tela (v4)

Pergunta: Quanto o tempo de tela acrescenta, além de outras características da rotina, à ordenação de relatos atuais de ansiedade e depressão na NSCH?

Protocolo: Validação deixando um ano fora (cada edição de 2020–2024 prevista por modelos ajustados nas demais); imputação e codificação ajustadas apenas no treino de cada partição; hiperparâmetros fixos definidos antes da execução; comparações pareadas nos mesmos registros; ROC AUC das pontuações agrupadas fora do ano; IC percentil por bootstrap de registros estratificado por ano, condicional aos modelos ajustados; AUC ponderada por FWC como sensibilidade, sem variância de desenho complexo. Nenhum modelo é salvo.

## Resultados (modelo principal: logistic)

### Depressão atual

- Com idade, sexo e os demais fatores de rotina já considerados, acrescentar o tempo de tela mudou a ROC AUC em 0,003 (IC 95%: 0,002 a 0,004).
- Isso equivale a cerca de 0,3 ponto percentual na chance de o modelo ordenar um relato positivo acima de um negativo.
- Na mesma comparação, a contribuição dos outros fatores foi — dificuldade com amizades: 0,073; sono: 0,004; atividade física: 0,002. O tempo de tela ficou em 3º lugar entre 4 fatores.
- A diferença foi positiva em 5 de 5 edições avaliadas separadamente.
- O intervalo não inclui zero, mas o tamanho da diferença é o que importa: compare-o com o dos outros fatores.

### Ansiedade atual

- Com idade, sexo e os demais fatores de rotina já considerados, acrescentar o tempo de tela mudou a ROC AUC em 0,003 (IC 95%: 0,003 a 0,004).
- Isso equivale a cerca de 0,3 ponto percentual na chance de o modelo ordenar um relato positivo acima de um negativo.
- Na mesma comparação, a contribuição dos outros fatores foi — dificuldade com amizades: 0,109; sono: 0,001; atividade física: 0,000. O tempo de tela ficou em 2º lugar entre 4 fatores.
- A diferença foi positiva em 5 de 5 edições avaliadas separadamente.
- O intervalo não inclui zero, mas o tamanho da diferença é o que importa: compare-o com o dos outros fatores.

## Tabela de contribuições incrementais

| target | modelo | fator | ΔAUC | IC inf | IC sup | ΔAUC ponderada | anos > 0 |
|---|---|---|---|---|---|---|---|
| depressao_atual | logistic | SCREENTIME | 0.0029 | 0.0023 | 0.0037 | 0.0016 | 5 |
| depressao_atual | logistic | HOURSLEEP | 0.0041 | 0.0035 | 0.0049 | 0.0046 | 5 |
| depressao_atual | logistic | PHYSACTIV | 0.0023 | 0.0017 | 0.0029 | 0.0023 | 5 |
| depressao_atual | logistic | MAKEFRIEND | 0.0726 | 0.0693 | 0.0759 | 0.0725 | 5 |
| depressao_atual | xgboost | SCREENTIME | 0.0028 | 0.0020 | 0.0035 | 0.0011 | 5 |
| depressao_atual | xgboost | HOURSLEEP | 0.0048 | 0.0040 | 0.0056 | 0.0053 | 5 |
| depressao_atual | xgboost | PHYSACTIV | 0.0027 | 0.0021 | 0.0033 | 0.0021 | 5 |
| depressao_atual | xgboost | MAKEFRIEND | 0.0695 | 0.0661 | 0.0727 | 0.0693 | 5 |
| ansiedade_atual | logistic | SCREENTIME | 0.0032 | 0.0026 | 0.0037 | 0.0027 | 5 |
| ansiedade_atual | logistic | HOURSLEEP | 0.0015 | 0.0010 | 0.0019 | 0.0016 | 5 |
| ansiedade_atual | logistic | PHYSACTIV | 0.0003 | 0.0001 | 0.0006 | -0.0002 | 4 |
| ansiedade_atual | logistic | MAKEFRIEND | 0.1086 | 0.1052 | 0.1119 | 0.1155 | 5 |
| ansiedade_atual | xgboost | SCREENTIME | 0.0027 | 0.0020 | 0.0034 | 0.0028 | 5 |
| ansiedade_atual | xgboost | HOURSLEEP | 0.0019 | 0.0013 | 0.0024 | 0.0023 | 5 |
| ansiedade_atual | xgboost | PHYSACTIV | 0.0013 | 0.0008 | 0.0017 | 0.0010 | 5 |
| ansiedade_atual | xgboost | MAKEFRIEND | 0.1011 | 0.0977 | 0.1042 | 0.1069 | 5 |

## Limites

- Associação e capacidade de ordenação não indicam causa: os dados são transversais e o tempo de tela pode ser consequência, e não causa, do relato.
- Os desfechos são relatos de responsáveis, nos Estados Unidos, sobre condições atuais informadas por profissionais; dependem de acesso a diagnóstico, recordação e disposição para informar.
- Os modelos não foram validados clinicamente nem para famílias brasileiras e não são usados para prever condições de pessoas no aplicativo.
- As categorias de tempo de tela são estimativas de um dia típico, informadas pelo responsável, e a redação do item mudou entre edições.
- Os intervalos reamostram registros e não incorporam estratos e conglomerados do desenho amostral; a AUC ponderada é apenas uma análise de sensibilidade.
- Os hiperparâmetros vêm de escolhas anteriores em 2020–2023, e 2024 já havia sido examinado em versões anteriores do protocolo; não há conjunto completamente cego.
