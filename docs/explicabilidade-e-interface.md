# Experimentos, explicabilidade e interface

Execute os comandos a partir da raiz do repositório, no ambiente virtual instalado:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mindscreen.analises --treinar
.\.venv\Scripts\python.exe -m mindscreen.exploratoria --manifesto data/processed/manifesto.json --output reports/exploratoria
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

O primeiro comando reutiliza experimentos já concluídos quando dataset e configuração coincidem. Sem `--treinar`, exige modelos prontos e apenas reproduz avaliação, SHAP, associação e relatórios. Artefatos incompletos não são tratados como treinamento concluído. Os modelos ficam em `models/experimentos/A` e `B`; os relatórios ficam em `reports/modelagem/v2_limiar_cv/`: métricas em `avaliacao`, odds ratios em `associacao`, gráficos HTML/JSON em `figuras` e interpretação em `resultados` (estrutura descrita em `reports/README.md`). Ao compartilhar os HTMLs, inclua o arquivo `plotly.min.js` da mesma pasta. A interface usa JSON/Plotly e não depende de rede para carregar gráficos.

## Protocolo congelado antes da avaliação

A contém todos os preditores aprovados no manifesto. B retira somente SCREENTIME. Para cada target, as mesmas linhas de 2020–2023 e a mesma semente/folds estratificados são usadas em A e B. Cada família tem a mesma busca limitada de hiperparâmetros. Transformações são ajustadas dentro de cada fold. Os modelos finais são ajustados em todo o desenvolvimento após seleção de hiperparâmetros. A escolha entre famílias usa ROC AUC média na validação cruzada de desenvolvimento; o melhor no teste de 2024 não substitui essa escolha.

A regularização inicial de Random Forest usa `min_samples_leaf=10` para conter tamanho e variância, definida antes do primeiro treino real e aplicada igualmente em A/B. Somente a regressão logística padroniza variáveis numéricas. Esses ajustes substituem o esboço inicial que padronizava todos os modelos e deixava folhas com uma observação. Não foram motivados por desempenho em 2024. Imputadores mantêm colunas vazias nos folds; categorias inéditas são ignoradas na codificação. As configurações e versões são registradas nos logs.

Pesos de classe são opções de busca para regressão logística e floresta (`class_weight`) e, desde a versão 2, para XGBoost (`scale_pos_weight` ∈ {1, negativos/positivos do desenvolvimento do target}). `sample_weight` não é aplicado nesta versão. Pesos amostrais permanecem no dataset. Não se afirma que pesos de classe corrijam o desenho amostral ou que o ajuste produza inferência populacional.

2024 é avaliado integralmente após excluir apenas a indeterminação do target em questão. O limiar de cada modelo (exceto o dummy, que mantém 0,5) é o que maximiza F1 nas previsões fora do fold do melhor estimador, nos mesmos cinco folds de 2020–2023; ele é gravado no log de treinamento e no registro e aplicado sem alteração a F1, precisão, recall, matriz de confusão e ao simulador. As curvas e AUCs usam scores contínuos da classe 1. PR-AUC é operacionalizada por Average Precision (AP) ([documentação do Scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)); a área trapezoidal foi removida porque, para um classificador constante, produzia valores próximos de 0,5 que não correspondem à prevalência. A curva gráfica pode ser reduzida a até 500 pontos para apresentação, mas as métricas usam todos os pontos.

Intervalos de 95% (`reports/modelagem/v2_limiar_cv/avaliacao/intervalos_bootstrap.csv`) vêm de 1.000 reamostras bootstrap pareadas dos registros de 2024 (mesmas reamostras para A e B), por percentil, sem pesos amostrais nem estratos; não representam incerteza populacional sob o desenho complexo.

### Revisão do protocolo (versão 2, 2026-11-19)

A primeira execução (limiar fixo 0,5, XGBoost sem `scale_pos_weight`) está preservada em `models/experimentos_v1_limiar05` e `reports/modelagem/v1_limiar05`. A revisão foi motivada pelo baixo recall do XGBoost selecionado observado em 2024 (9% em depressão), resultado de pontuações não compensadas pelo desbalanceamento cruzarem pouco o limiar 0,5. As novas escolhas usam somente 2020–2023, mas, por transparência, 2024 deixou de ser um teste totalmente cego para esta decisão de protocolo. Nenhuma outra alteração (preditores, famílias, folds, semente) foi feita. Comparações entre versões devem citar essa limitação.

## SHAP

O background é amostrado de 2020–2023, e os registros explicados de 2024, com semente fixa. Os limites padrão são 64 registros de referência e 128 explicados por target, para controlar custo. A seleção de amostras usa sorteio sem escolher exemplos por importância ou por classe. São explicados os modelos selecionados em A, independentemente do ranking de teste.

Regressão logística usa LinearExplainer em log-odds. Random Forest usa TreeExplainer interventional no score de probabilidade não calibrada da classe 1 ([documentação SHAP](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html)); quando incompatível ou não aditivo, há fallback explícito para PermutationExplainer. XGBoost usa TreeExplainer interventional na margem (log-odds da classe 1), porque o modo `probability` não fechou a aditividade com shap 0.54 e xgboost 3.x (erro de até 0,7 nos modelos de 2024). Para XGBoost, a matriz esparsa do pré-processamento é densificada com `NaN` nas entradas não armazenadas, e não com zero: o XGBoost trata essas entradas como ausentes, e densificar com zero explicaria outra função (margens divergentes em até ~3 log-odds). A saída de referência é a margem do pipeline real. A soma das contribuições e do valor de referência deve reproduzir a saída correspondente da classe 1 dentro da tolerância numérica; falha de aditividade impede apresentar a explicação. DummyClassifier constante não recebe uma importância fictícia.

As contribuições das colunas one-hot são somadas por variável original, preservando a aditividade. Esse agrupamento posterior não equivale necessariamente a calcular um jogo de Shapley conjunto para cada variável original: as intervenções do explicador podem quebrar dependências entre dummies ou atributos correlacionados. A importância global é a média do valor absoluto dessas contribuições agrupadas na amostra explicada. O beeswarm mostra sua distribuição com cor relativa ao valor/código da variável; cores não transformam categorias em escalas contínuas. Exemplos individuais são registros públicos reais da avaliação, sem HHID exibido. Atribuições positivas e negativas se referem ao background e à função do modelo. Não são estimativas do que ocorreria se alguém mudasse seu tempo de tela. Magnitudes em log-odds e em probabilidade não são diretamente comparáveis entre modelos.

## Associação ajustada

A regressão logística complementar é não penalizada, ajustada em casos completos de 2020–2023, com idade, sexo, sono, atividade física, amizade e ano como covariáveis definidas previamente. SCREENTIME entra por categorias, com menos de 1 hora como referência. ORs são exponenciais dos coeficientes de cada categoria. Resultados são associações condicionais amostrais; não são risco relativo, prevalência populacional ou efeito causal. O relatório informa exclusões por ausência e quantidade de casos completos. Covariáveis contemporâneas podem ser mediadoras ou consequências dos desfechos; o ajuste não elimina causalidade reversa ou confundimento.

Não são usados erros padrão ingênuos ou ICs de regressão comum como se representassem o desenho complexo NSCH. Inferência populacional permanece uma etapa metodológica separada. A interpretação não deve afirmar que uso de telas provoca ansiedade ou depressão.

## Simulador, integridade e privacidade

O simulador usa os modelos A escolhidos por CV e aplica os pipelines completos persistidos. Inputs são somente categorias aprovadas e idade de 6–17 anos. Não aceita componentes de targets nem dados identificadores. Scores não foram calibrados; a interface os apresenta como pontuações brutas, sem percentuais ou alegação de probabilidade clínica. O rótulo 0/1 é a saída da tarefa de pesquisa e não uma classificação clínica do indivíduo.

Nenhum perfil é escrito em arquivo, registrado em logs ou usado para treinamento. Estado de widgets existe apenas na sessão necessária ao formulário; resultados de perfis não são cacheados. O cache de dados contém somente o dataset público validado e é invalidado pela mudança dos hashes do manifesto e do dataset.

Joblib utiliza serialização que pode executar código. A aplicação não aceita uploads ou caminhos fornecidos por visitantes. Só carrega os artefatos locais do projeto listados em um registro com hashes, confere vínculo com o dataset e rejeita caminhos fora da pasta autorizada ou arquivos alterados. Essa proteção pressupõe que o código e o registro locais provêm da execução confiável do projeto; hashes não autenticam arquivos de terceiros. Não substituir modelos/registro por downloads desconhecidos. Mensagens da interface são genéricas e não expõem caminhos locais ou exceções internas.

Não houve validação clínica, avaliação de transporte para o Brasil ou calibração individual. A ferramenta apresenta respostas declaradas por responsáveis em uma pesquisa observacional dos Estados Unidos, com diferenças documentadas entre edições e possíveis vieses por ausência e seleção. Consulte os relatórios reais antes de interpretar resultados.
