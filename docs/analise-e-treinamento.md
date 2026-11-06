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

No treinamento, 2024 é reservado e não é usado para ajuste, seleção ou avaliação. Os modelos são escolhidos por ROC AUC média em cinco folds estratificados dos anos 2020–2023; imputação e codificação ocorrem dentro de cada fold. As opções de pesos de classe são comparadas para regressão logística e floresta. Os pesos amostrais não são usados no ajuste desta implementação inicial e não se afirma inferência populacional. Os modelos persistidos são as versões ajustadas no conjunto completo de desenvolvimento após busca. A avaliação temporal de 2024 ainda precisa ser implementada em etapa separada após congelar as escolhas. Nenhum resultado é diagnóstico ou prova de causalidade.

As versões instaladas dos quatro estimadores expõem `sample_weight` em `fit`; o log registra essa compatibilidade observada e confirma que o argumento não foi usado. Pesos de classe e pesos amostrais têm finalidades distintas, e a compatibilidade da API não valida inferência para o desenho complexo. O fluxo registra para cada target o número excluído por target ausente.
