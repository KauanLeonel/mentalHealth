# Pesquisa 1: contribuição incremental do tempo de tela (v4)

## Por que o uso dos dados mudou

O projeto deixou de buscar uma previsão individual de ansiedade ou depressão e passou a apoiar a reflexão familiar sobre a rotina digital (ver `docs/rotina-digital.md`). As versões v1–v3 respondiam a "quão bem um classificador separa relatos positivos e negativos em 2024?", tinham 2024 como teste e salvavam modelos para um simulador. Os próprios resultados delas (ΔROC AUC de SCREENTIME por volta de 0,004 para depressão e 0,003 para ansiedade, em `reports/modelagem/v3_calibrada/avaliacao/ablation.csv`) indicaram que a pergunta mais útil é outra:

> Qual é a contribuição incremental do tempo de tela, além de outras características de rotina, para a classificação exploratória de relatos atuais de ansiedade e depressão na NSCH?

A v4 (`python -m mindscreen.contribuicao`) responde a essa pergunta. As versões anteriores foram preservadas.

| Aspecto | v1–v3 | v4 |
|---|---|---|
| Objetivo | Classificador por pessoa | Medir quanto cada fator de rotina acrescenta |
| Uso dos anos | Desenvolvimento em 2020–2023, teste em 2024 | Validação deixando um ano fora em 2020–2024: cada edição é prevista por modelos ajustados nas outras quatro |
| Comparação | A (com tela) contra B (sem tela) | Os quatro fatores de rotina, avaliados do mesmo modo |
| Hiperparâmetros | Busca em grade | Fixos e definidos antes da execução (ver abaixo) |
| Incerteza | Bootstrap pareado em 2024 | Bootstrap pareado estratificado por ano, mais diferenças por edição e por faixa etária |
| Pesos | Não usados | AUC ponderada por FWC como sensibilidade; percentuais descritivos ponderados |
| Artefatos | Modelos `.joblib` | Nenhum modelo salvo; apenas métricas e resumos |

Motivos:

- **2024 deixou de ser cego.** Ele foi examinado nas revisões do protocolo. Tratá-lo como teste único dava uma falsa impressão de avaliação independente. Prever cada edição a partir das outras mostra se a contribuição se repete entre anos.
- **O tempo de tela precisa ser lido em contexto.** O produto trata a tela como parte da rotina. Por isso sono, atividade física e dificuldade com amizades passam pela mesma comparação, e a contribuição da tela é comparada com a deles.
- **Não salvar modelos** impede reutilizar um classificador individual no aplicativo, como recomenda a mudança de escopo.

## Protocolo

Configuração: `configs/contribuicao.json`. Código: `src/mindscreen/contribuicao.py`.

1. **População.** Registros de 6–17 anos de 2020–2024 do dataset harmonizado e validado (`data/processed/manifesto.json`). Para cada target, ficam de fora apenas os registros com target indeterminado. Preditores ausentes são imputados dentro do pipeline: mediana para a idade e a categoria `__AUSENTE__` para as categóricas. Assim, todos os conjuntos usam os mesmos registros.
2. **Conjuntos de preditores.** Base: idade e sexo. Fatores de rotina: SCREENTIME, HOURSLEEP, PHYSACTIV e MAKEFRIEND. Para cada fator *F* são comparados:
   - *isolado*: base + *F* contra base;
   - *incremental*: rotina completa contra rotina completa sem *F*. Para *F* = SCREENTIME, essa comparação equivale aos experimentos A e B.
   A configuração é recusada se base + fatores não corresponder exatamente aos preditores aprovados no manifesto.
3. **Validação.** Para cada ano *a*, o pipeline (imputação, codificação e modelo) é ajustado nos demais anos e prevê *a*. As pontuações fora do ano são reunidas.
4. **Modelos.** Principal: regressão logística (`C = 1`, sem pesos de classe), por ser interpretável e porque a v2 mostrou desempenho próximo ao das árvores. Sensibilidade: XGBoost (`max_depth = 3`, `learning_rate = 0,1`, 200 árvores, sem `scale_pos_weight`). Esses valores foram fixados a partir das escolhas da v2 em 2020–2023 e não são reajustados.
5. **Métricas.** ROC AUC, ROC AUC ponderada por FWC, average precision e Brier, por edição e agregadas.
6. **Contribuição.** ΔAUC = AUC(com *F*) − AUC(sem *F*), calculada nos mesmos registros. O IC 95% é o percentil de 1000 reamostras de registros, estratificadas por ano. A tabela traz também o ΔAUC de cada edição, o número de edições com Δ > 0, o ΔAUC por faixa etária (6–11 e 12–17, com IC), o ΔAUC ponderado e a Δ average precision.
7. **Perfil da rotina.** Percentual ponderado de cada categoria dos fatores de rotina, por faixa etária, em 2020–2024 (`FWC_media_anual_periodo`) e por edição (`FWC`). São estimativas pontuais, sem intervalos.
8. **Resumo para famílias.** `resumo_familias.json` monta frases a partir dos números calculados (modelo principal, comparação incremental). Nenhum valor é digitado à mão. O app lê esse arquivo somente quando o SHA-256 do dataset coincide com o do manifesto.

## Saídas (`reports/modelagem/v4_contribuicao/`)

`metricas.csv`, `contribuicoes.csv`, `perfil_rotina.csv`, `contribuicao.json` (protocolo, configuração, população e versões), `resumo_familias.json` e `interpretacao.md`. A rotina recusa sobrescrever uma pasta que já tenha resultados.

```powershell
# com barra de progresso (etapas concluídas, tempo decorrido e estimativa do restante)
.\.venv\Scripts\python.exe scripts\rodar_contribuicao.py --output reports\modelagem\v4_contribuicao_reexecucao

# equivalente via módulo; --sem-barra imprime uma linha por etapa (útil em logs)
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mindscreen.contribuicao --output reports\modelagem\v4_contribuicao_reexecucao
```

A execução completa tem 72 etapas: 2 targets × 2 modelos × (10 conjuntos ajustados + 8 comparações com bootstrap).

## Como ler os resultados

- A ROC AUC é a chance de o modelo ordenar um relato positivo acima de um negativo. Um ΔAUC de 0,004 equivale a 0,4 ponto percentual nessa chance.
- Um intervalo que não inclui zero não torna a diferença relevante. O tamanho importa, e por isso o resultado é comparado com o dos outros fatores.
- Nenhuma contribuição indica causa. Sono, atividade física e amizades são medidos ao mesmo tempo que o desfecho e podem ser consequência dele.

## Limitações

- O bootstrap reamostra registros e é condicional aos modelos ajustados. Não incorpora estratos e conglomerados da NSCH nem a variabilidade do ajuste.
- A AUC ponderada usa FWC apenas como sensibilidade e não constitui inferência de desenho complexo.
- Os hiperparâmetros vêm da v2, escolhida em 2020–2023. Nenhum ano é completamente cego.
- O item SCREENTIME teve redação diferente em 2024 (exclusão explícita de tarefas escolares). A diferença por edição ajuda a observar, mas não a corrigir, essa mudança.
- Os desfechos são relatos de responsáveis nos EUA sobre diagnósticos informados por profissionais. Não foram validados clinicamente nem para famílias brasileiras.
