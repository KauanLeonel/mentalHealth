# Harmonização NSCH 2020–2024: versão inicial

Esta versão produz dados para análise de associação e classificação de respostas sobre condições atuais informadas por responsável. Não estima efeito causal do tempo de tela nem produz diagnóstico médico. As regras foram conferidas nas listas oficiais de cada edição, e a rotina compara frequências selecionadas e pesos com as publicações do Census. A validação do manifesto é técnica e automatizada; não representa aprovação humana pelo orientador nem autenticação byte a byte dos arquivos SAS/Stata originais.

## Fontes e conferência por edição

| Ano | Lista de variáveis | Frequências |
|---|---|---|
| 2020 | [Topical Variable List](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/2020-NSCH-Topical-Variable-List.pdf) | [Topical Frequencies](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/NSCH_2020_Topical_Frequencies.pdf) |
| 2021 | [Topical Variable List](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/2021-NSCH-Topical-Variable-List.pdf) | [Topical Frequencies](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/NSCH_2021_Topical_Frequencies.pdf) |
| 2022 | [Topical Variable List](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/2022-NSCH-Topical-Variable-List.pdf) | [Topical Frequencies](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/NSCH_2022_Topical_Frequencies.pdf) |
| 2023 | [Topical Variable List](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/2023-NSCH-Topical-Variable-List.pdf) | [Topical Frequencies](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/NSCH_2023_Topical_Frequencies.pdf) |
| 2024 | [Topical Variable List](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/2024-NSCH-Topical-Variable-List.pdf) | [Topical Frequencies](https://www2.census.gov/programs-surveys/nsch/technical-documentation/codebook/NSCH_2024_Topical_Frequencies.pdf) |

Os nomes, domínios, universo e saltos dos componentes de targets, SCREENTIME, sexo, idade, sono, atividade física, amizade, bullying e cinco itens K7 foram conferidos por edição. `configs/harmonizacao.json` registra os domínios usados, os códigos sim/não por ano e as frequências de controle. As listas consultadas para 2020–2023 são de 31/01/2025 e para 2024 de 06/10/2025. As tabelas publicadas podem ser atualizadas pelo Census: os controles desta versão não são baixados dinamicamente.

Critérios por arquivo: nome identificável de um único ano e instrumento topical, colunas obrigatórias, tamanho da edição, HHID único e preenchido, idade inteira entre 0 e 17 e FORMTYPE correspondente, FIPSST com dois dígitos, STRATUM em 1/2A, FWC positivo e finito. A distribuição completa de SCREENTIME e as contagens de sexo devem coincidir com as frequências oficiais; as somas de FWC por sexo devem coincidir até uma unidade por arredondamento dos totais publicados. Isso fornece evidência de compatibilidade do conteúdo e dos pesos com o PUF publicado, sem autenticação completa de procedência. Um arquivo ausente ou reprovado não interrompe as outras edições; não há seleção silenciosa entre duplicatas.

O [documento de aprimoramentos](https://www2.census.gov/programs-surveys/nsch/technical-documentation/NSCH_Enhancements_Technical_Document.pdf) descreve a convenção `nsch_YYYYe_topical` para arquivos enhanced. A letra `e` é apenas indício de nome; a checagem de pesos contra frequências publicadas é a evidência adicional usada para os arquivos antigos. O fato de os CSVs locais de 2022–2024 também conterem `e` não é interpretado como prova de um novo ciclo de aprimoramentos.

## População e diferenças entre edições

A população inicial é de 6–17 anos, comum às versões T2 (6–11) e T3 (12–17). SCREENTIME se aplica às três versões de questionário, mas HOURSLEEP, PHYSACTIV e bullying se aplicam a T2/T3; HOURSLEEP05 não substitui HOURSLEEP. MAKEFRIEND é para 3–17 anos em 2020/2021 e para T2/T3 a partir de 2022. Por isso a restrição de 6–17 mantém um universo comum sem confundir ausências estruturais nas crianças menores com não resposta.

SCREENTIME permanece categórica: 1 = menos de 1h, 2 = 1h, 3 = 2h, 4 = 3h, 5 = 4h ou mais, em dias de semana. A lista de 2024 explicita a exclusão de tempo de tarefas escolares, frase que não consta no item das listas anteriores consultadas. Essa diferença documental é registrada sem afirmar que prove mudança efetiva no instrumento. Não converter códigos em horas contínuas nem assumir identidade perfeita de medição entre os anos.

MAKEFRIEND mantém categorias 1 = nenhuma dificuldade, 2 = um pouco, 3 = muita dificuldade; a mudança de universo é resolvida pela faixa etária comum. HOURSLEEP usa sete categorias de menos de 6h a 11h ou mais em noites de semana; PHYSACTIV usa quatro categorias de dias com pelo menos 60 minutos de atividade na semana anterior. Os códigos não equivalem diretamente a horas ou dias numéricos.

As perguntas BULLIED_R e BULLY mantêm cinco categorias de frequência, mas desde 2022 há orientação para excluir irmãos e parceiros de relacionamento. São mantidas para exploração com ressalva e excluídas do conjunto inicial de preditores. Os itens K7Q70_R/K7Q82_R/K7Q83_R/K7Q84_R/K7Q85_R usam 1 = sempre, 2 = geralmente, 3 = às vezes, 4 = nunca. São preservados para descrição e excluídos do modelo inicial por proximidade com comportamento/sintomas e ambiguidade temporal. ENGAGECONCERN e BODYIMAGE, ausentes em 2020/2021, continuam fora do dataset analítico desta versão e marcadas para revisão quando presentes. Não foram atribuídos significados ou categorias a esses dois itens sem revisão adicional.

## Ausências e targets

O [relatório metodológico de 2020, seção Missing Values and Imputation](https://www2.census.gov/programs-surveys/nsch/technical-documentation/methodology/2020-NSCH-Methodology-Report.pdf) define `.L` como salto legítimo, `.M` como ausência por erro/resposta inválida, `.N` como fora do universo e `.D` como supressão por confidencialidade. Esses marcadores, se presentes, recebem status próprio e permanecem ausentes na coluna analítica. Um campo vazio ou ponto simples no CSV recebe `ausente_sem_motivo_csv`. Não se inventa recusa: quando sua informação foi perdida na exportação CSV, não é recuperável. Textos ou números não documentados não são convertidos em categorias válidas.

Nos cinco anos, K2Q32A/K2Q33A perguntam se um profissional de saúde alguma vez informou a condição; K2Q32B/K2Q33B perguntam sobre condição atual e saltam quando o histórico é 2 (não). Em cada edição: 1 = sim, 2 = não. K2Q33B usa a expressão “these problems” nas listas de 2023/2024, sem mudança dos códigos ou da referência à ansiedade. A interpretação permanece relato do responsável, e não diagnóstico produzido pelo sistema.

| Histórico A | Resposta atual B | Target | Status |
|---|---|---|---|
| 2 | vazio, ponto simples ou `.L` | 0 | negativo pelo salto documentado |
| 2 | 2 | 0 | negativo explícito; combinação registrada |
| 1 | 1 | 1 | positivo atual |
| 1 | 2 | 0 | negativo atual |
| 1 | ausente/especial/inválida | ausente | atual indeterminado |
| desconhecido/inválido | qualquer | ausente | histórico indeterminado |
| 2 | 1 ou código inválido/especial diferente do salto | ausente | inconsistente ou inválida |

Nenhum target indeterminado vira negativo. Não se exige determinação conjunta dos dois targets. O dataset principal mantém todos os elegíveis por idade, inclusive ausência de SCREENTIME e de um ou ambos os targets. Os datasets por desfecho excluem apenas a indeterminação do próprio target, depois da mesma restrição etária. `fluxo.csv` registra as decisões para cada ano e target; a quantidade com SCREENTIME ausente é informativa, não uma exclusão adicional.

## Papéis das variáveis e pesos

Os preditores iniciais, definidos pelas regras e não pelo desempenho de 2024, são idade, sexo, SCREENTIME, HOURSLEEP, PHYSACTIV e MAKEFRIEND. O manifesto declara as listas. Os componentes de ambos os targets ficam em `componentes_targets.parquet`, ligados por `id_registro`, e não no dataset principal. Gravidades e outros diagnósticos não são incluídos. Status de ausência e de construção dos targets são colunas de auditoria, proibidas como entradas do modelo. HHID, FIPSST, FORMTYPE, STRATUM, ano e pesos são administrativos.

FWC é preservado na escala anual. `FWC_media_anual_periodo` é FWC dividido pelo número de edições efetivamente incluídas, conforme o [guia do Census para estimativas plurianuais](https://www2.census.gov/programs-surveys/nsch/technical-documentation/methodology/NSCH-Guide-to-Multi-Year-Estimates.pdf), quando se deseja o tamanho populacional anual médio em um período combinado. Com os cinco anos incluídos, o divisor é 5. A coluna não transforma métricas de classificação em inferência populacional. FIPSST/STRATUM/HHID e ano são preservados para posterior especificação apropriada do desenho e da população/domínio de análise. Não se criam PSUs ou estratos derivados como se fossem oficiais; nenhum intervalo de confiança é calculado nesta rotina.

## Reprodução e artefatos

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mindscreen.harmonizacao
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_harmonizacao.py tests/test_dados_validados.py
```

Entradas padrão: CSVs em `Dados/`, incluindo subpastas. A rotina lê diretamente as fontes, sem depender das conversões intermediárias. Saídas padrão: `data/processed/` e `reports/harmonizacao/`. Não sobrescreve resultados anteriores; para uma nova execução use `--saida data/processed/nova_execucao --relatorios reports/harmonizacao/nova_execucao`. Originais e arquivos em data/raw têm SHA-256 conferido antes e depois. O manifesto é criado por último, somente depois das verificações. A geração de um manifesto não substitui revisão científica e as limitações continuam vinculadas a ele.
