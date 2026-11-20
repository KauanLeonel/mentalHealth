# Análise da contribuição incremental do tempo de tela (v4)

Relatório gerado por `python -m mindscreen.analise_contribuicao` a partir das saídas de `mindscreen.contribuicao`. Nenhum modelo foi ajustado nesta etapa e todos os números foram lidos dos arquivos da versão.

**Pergunta.** Quanto o tempo de tela acrescenta, além de outras características da rotina, à ordenação de relatos atuais de ansiedade e depressão na NSCH?

**Protocolo.** Validação deixando um ano fora (cada edição de 2020–2024 prevista por modelos ajustados nas demais); imputação e codificação ajustadas apenas no treino de cada partição; hiperparâmetros fixos definidos antes da execução; comparações pareadas nos mesmos registros; ROC AUC das pontuações agrupadas fora do ano; IC percentil por bootstrap de registros estratificado por ano, condicional aos modelos ajustados; AUC ponderada por FWC como sensibilidade, sem variância de desenho complexo. Nenhum modelo é salvo.

## População analisada

| Desfecho | Registros | Positivos | Excluídos (desfecho indeterminado) | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|
| Depressão atual | 165378 | 11193 (7%) | 965 | 30498 | 30028 | 34147 | 33430 | 37275 |
| Ansiedade atual | 164701 | 26051 (16%) | 1642 | 30370 | 29906 | 34019 | 33278 | 37128 |

## 1. Resposta principal

**Depressão atual** (regressão logística)

- Com idade, sexo e os demais fatores de rotina já considerados, acrescentar o tempo de tela mudou a ROC AUC em 0,003 (IC 95%: 0,002 a 0,004).
- Isso equivale a cerca de 0,3 ponto percentual na chance de o modelo ordenar um relato positivo acima de um negativo.
- Na mesma comparação, a contribuição dos outros fatores foi — dificuldade com amizades: 0,073; sono: 0,004; atividade física: 0,002. O tempo de tela ficou em 3º lugar entre 4 fatores.
- A diferença foi positiva em 5 de 5 edições avaliadas separadamente.
- O intervalo não inclui zero, mas o tamanho da diferença é o que importa: compare-o com o dos outros fatores.

**Ansiedade atual** (regressão logística)

- Com idade, sexo e os demais fatores de rotina já considerados, acrescentar o tempo de tela mudou a ROC AUC em 0,003 (IC 95%: 0,003 a 0,004).
- Isso equivale a cerca de 0,3 ponto percentual na chance de o modelo ordenar um relato positivo acima de um negativo.
- Na mesma comparação, a contribuição dos outros fatores foi — dificuldade com amizades: 0,109; sono: 0,001; atividade física: 0,000. O tempo de tela ficou em 2º lugar entre 4 fatores.
- A diferença foi positiva em 5 de 5 edições avaliadas separadamente.
- O intervalo não inclui zero, mas o tamanho da diferença é o que importa: compare-o com o dos outros fatores.

Figuras: `figuras/<desfecho>_incremental.html`, `figuras/<desfecho>_auc_conjuntos.html`.

## 2. Sobreposição com os outros fatores de rotina

Contribuição de cada fator sozinho (acrescentado a idade e sexo) e depois de os demais fatores entrarem no modelo. A fração que permanece indica quanto da informação do fator não está contida nos outros. A correlação entre fatores não indica qual deles vem primeiro.

| Desfecho | Modelo | Fator | Δ isolado | Δ incremental | Fração que permanece |
|---|---|---|---|---|---|
| Ansiedade atual | logistic | Dificuldade com amizades | 0,1387 | 0,1086 | 78% |
| Ansiedade atual | logistic | Tempo de tela | 0,0206 | 0,0032 | 15% |
| Ansiedade atual | logistic | Sono | 0,0089 | 0,0015 | 17% |
| Ansiedade atual | logistic | Atividade física | 0,0193 | 0,0003 | 2% |
| Ansiedade atual | xgboost | Dificuldade com amizades | 0,1351 | 0,1011 | 75% |
| Ansiedade atual | xgboost | Tempo de tela | 0,0236 | 0,0027 | 12% |
| Ansiedade atual | xgboost | Sono | 0,0147 | 0,0019 | 13% |
| Ansiedade atual | xgboost | Atividade física | 0,0258 | 0,0013 | 5% |
| Depressão atual | logistic | Dificuldade com amizades | 0,1084 | 0,0726 | 67% |
| Depressão atual | logistic | Sono | 0,0170 | 0,0041 | 24% |
| Depressão atual | logistic | Tempo de tela | 0,0236 | 0,0029 | 12% |
| Depressão atual | logistic | Atividade física | 0,0287 | 0,0023 | 8% |
| Depressão atual | xgboost | Dificuldade com amizades | 0,1045 | 0,0695 | 66% |
| Depressão atual | xgboost | Sono | 0,0196 | 0,0048 | 25% |
| Depressão atual | xgboost | Tempo de tela | 0,0223 | 0,0028 | 13% |
| Depressão atual | xgboost | Atividade física | 0,0277 | 0,0027 | 10% |

- Depressão atual: sozinho, o tempo de tela acrescenta 0,0236 à ROC AUC de idade e sexo. Com os demais fatores já no modelo, acrescenta 0,0029, ou seja, 12% da contribuição isolada.

- Ansiedade atual: sozinho, o tempo de tela acrescenta 0,0206 à ROC AUC de idade e sexo. Com os demais fatores já no modelo, acrescenta 0,0032, ou seja, 15% da contribuição isolada.

Figura: `figuras/<desfecho>_isolado.html`.

## 3. Consistência entre edições

ΔAUC incremental do tempo de tela em cada edição prevista por modelos ajustados nas demais:

| Desfecho | Modelo | 2020 | 2021 | 2022 | 2023 | 2024 | Mínimo | Máximo | Edições > 0 |
|---|---|---|---|---|---|---|---|---|---|
| Ansiedade atual | logistic | 0,0047 | 0,0022 | 0,0035 | 0,0032 | 0,0037 | 0,0022 | 0,0047 | 5 de 5 |
| Ansiedade atual | xgboost | 0,0052 | 0,0019 | 0,0027 | 0,0016 | 0,0032 | 0,0016 | 0,0052 | 5 de 5 |
| Depressão atual | logistic | 0,0042 | 0,0019 | 0,0034 | 0,0018 | 0,0043 | 0,0018 | 0,0043 | 5 de 5 |
| Depressão atual | xgboost | 0,0044 | 0,0016 | 0,0033 | 0,0012 | 0,0042 | 0,0012 | 0,0044 | 5 de 5 |

A redação do item de tempo de tela mudou em 2024 (exclusão explícita de tarefas escolares). A tabela permite observar essa edição separadamente, mas não corrige a mudança.

Figura: `figuras/<desfecho>_por_ano.html`.

## 4. Robustez: modelos e pesos amostrais

| Desfecho | Fator | Δ logistic | posição logistic | Δ xgboost | posição xgboost | Δ ponderado (logistic) |
|---|---|---|---|---|---|---|
| Ansiedade atual | Sono | 0,0015 | 3º | 0,0019 | 3º | 0,0016 |
| Ansiedade atual | Dificuldade com amizades | 0,1086 | 1º | 0,1011 | 1º | 0,1155 |
| Ansiedade atual | Atividade física | 0,0003 | 4º | 0,0013 | 4º | -0,0002 |
| Ansiedade atual | Tempo de tela | 0,0032 | 2º | 0,0027 | 2º | 0,0027 |
| Depressão atual | Sono | 0,0041 | 2º | 0,0048 | 2º | 0,0046 |
| Depressão atual | Dificuldade com amizades | 0,0726 | 1º | 0,0695 | 1º | 0,0725 |
| Depressão atual | Atividade física | 0,0023 | 4º | 0,0027 | 4º | 0,0023 |
| Depressão atual | Tempo de tela | 0,0029 | 3º | 0,0028 | 3º | 0,0016 |

- Depressão atual: a ordem dos fatores é a mesma entre os modelos.

- Ansiedade atual: a ordem dos fatores é a mesma entre os modelos.

A AUC ponderada usa o peso FWC como análise de sensibilidade e não incorpora a variância do desenho amostral.

## 5. Faixas etárias

| Desfecho | Modelo | Faixa | ΔAUC do tempo de tela | IC 95% |
|---|---|---|---|---|
| Depressão atual | logistic | 6–11 | 0,0058 | 0,0033 a 0,0083 |
| Depressão atual | logistic | 12–17 | 0,0041 | 0,0031 a 0,0050 |
| Depressão atual | xgboost | 6–11 | 0,0046 | 0,0021 a 0,0073 |
| Depressão atual | xgboost | 12–17 | 0,0039 | 0,0028 a 0,0049 |
| Ansiedade atual | logistic | 6–11 | 0,0039 | 0,0025 a 0,0054 |
| Ansiedade atual | logistic | 12–17 | 0,0039 | 0,0031 a 0,0047 |
| Ansiedade atual | xgboost | 6–11 | 0,0030 | 0,0014 a 0,0046 |
| Ansiedade atual | xgboost | 12–17 | 0,0036 | 0,0028 a 0,0046 |

Dentro de cada faixa, a idade varia menos, e por isso as AUCs de cada faixa não são comparáveis com a AUC total. Compare as faixas entre si.

Figura: `figuras/<desfecho>_faixas.html`.

## 6. Perfil da rotina na NSCH (percentuais ponderados)

Estimativas pontuais com os pesos da pesquisa, para crianças e adolescentes de 6 a 17 anos nos EUA, sem intervalos. Não servem como referência para uma família específica.

**Tempo de tela**

| Categoria | 6–11 | 12–17 |
|---|---|---|
| Menos de 1 hora | 9,1% | 4,1% |
| 1 hora | 17,9% | 8,0% |
| 2 horas | 32,7% | 24,0% |
| 3 horas | 20,7% | 24,5% |
| 4 horas ou mais | 19,7% | 39,4% |

**Sono**

| Categoria | 6–11 | 12–17 |
|---|---|---|
| Menos de 6 horas | 0,6% | 2,1% |
| 6 horas | 1,4% | 6,2% |
| 7 horas | 5,6% | 17,8% |
| 8 horas | 28,9% | 41,5% |
| 9 horas | 32,8% | 22,3% |
| 10 horas | 26,2% | 8,4% |
| 11 horas ou mais | 4,6% | 1,8% |

**Atividade física**

| Categoria | 6–11 | 12–17 |
|---|---|---|
| 0 dias | 6,8% | 15,4% |
| 1–3 dias | 40,9% | 42,9% |
| 4–6 dias | 26,8% | 27,2% |
| Todos os dias | 25,6% | 14,4% |

**Dificuldade com amizades**

| Categoria | 6–11 | 12–17 |
|---|---|---|
| Nenhuma dificuldade | 79,1% | 73,4% |
| Um pouco de dificuldade | 16,9% | 20,9% |
| Muita dificuldade | 3,9% | 5,7% |

Tempo de tela na categoria mais alta (“4 horas ou mais”), por edição:

| Faixa | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 6–11 | 23,4% | 19,7% | 18,3% | 17,3% | 19,9% |
| 12–17 | 44,0% | 40,8% | 37,9% | 35,0% | 39,5% |

Figuras: `figuras/perfil_<variável>.html`, `figuras/tela_por_ano.html`.

## 7. Comparação com a versão anterior (v3)

A v3 avaliou modelos com e sem tempo de tela em 2024, com hiperparâmetros buscados em 2020–2023. A v4 usa validação deixando um ano fora em todas as edições. Os protocolos são diferentes; a comparação serve apenas para verificar se a ordem de grandeza se mantém.

| Desfecho | Modelo | ΔAUC v3 (teste 2024) | ΔAUC v4 (todas as edições) | ΔAUC v4 (só 2024) |
|---|---|---|---|---|
| Depressão atual | logistic | 0,0047 | 0,0029 | 0,0043 |
| Depressão atual | xgboost | 0,0042 | 0,0028 | 0,0042 |
| Ansiedade atual | logistic | 0,0037 | 0,0032 | 0,0037 |
| Ansiedade atual | xgboost | 0,0029 | 0,0027 | 0,0032 |

## Limites

- Associação e capacidade de ordenação não indicam causa: os dados são transversais e o tempo de tela pode ser consequência, e não causa, do relato.
- Os desfechos são relatos de responsáveis, nos Estados Unidos, sobre condições atuais informadas por profissionais; dependem de acesso a diagnóstico, recordação e disposição para informar.
- Os modelos não foram validados clinicamente nem para famílias brasileiras e não são usados para prever condições de pessoas no aplicativo.
- As categorias de tempo de tela são estimativas de um dia típico, informadas pelo responsável, e a redação do item mudou entre edições.
- Os intervalos reamostram registros e não incorporam estratos e conglomerados do desenho amostral; a AUC ponderada é apenas uma análise de sensibilidade.
- Os hiperparâmetros vêm de escolhas anteriores em 2020–2023, e 2024 já havia sido examinado em versões anteriores do protocolo; não há conjunto completamente cego.
