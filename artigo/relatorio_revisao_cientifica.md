# Revisão científica do MindScreen

Revisão executada em 19/11/2026. O manuscrito mantém o protótipo familiar como contribuição central e explicita a função de cada análise. As versões anteriores do texto e da bibliografia estão em `versoes_anteriores/`.

## Auditoria e decisões

- O repositório contém cinco CSVs Topical, rotinas de auditoria, harmonização, associação, treinamento, explicabilidade e calibração, aplicações Streamlit, testes e artefatos das versões v1, v2 e v3. Não foram localizados notebooks do projeto. O PDF anterior no diretório Downloads foi lido com PDF.js. Tinha nove páginas, sendo a última ocupada apenas pela continuação da referência de Valkenburg et al.
- Os dicionários de 2020 a 2024 documentam as categorias de tela e a condição atual após histórico positivo. A exclusão explícita de tarefas escolares em 2024 motivou o ajuste de sensibilidade sem essa edição. Os resultados não ponderados de 2020–2023 foram preservados e conferidos contra o relatório v2.
- A análise ponderada executável foi acrescentada em `src/mindscreen/desenho_nsch.py`. Os cinco hashes correspondem ao manifesto e os campos de desenho dos CSVs coincidem com os registros elegíveis do Parquet. A saída conserva perfil anual, prevalências por tela, contrastes descritivos por idade, regressões bruta e ajustadas, VIF e sensibilidade sem 2024.
- A análise com pesos reproduz o desenho publicado no guia multianual e conserva as unidades fora do domínio no cálculo de variância. Dois testes verificam por cálculo independente a variância estratificada e um contraste de regressão saturada. R survey, SAS, Stata e SUDAAN não foram executados.
- Foram reinferidos os escores dos XGBoost A/B de depressão e ansiedade, nas versões sem calibração e calibrada, sobre registros determinados de 2024. Métricas e contagens da versão 2 coincidiram com o relatório. O erro quadrático médio dos escores coincidiu com o Brier da versão 3. O bootstrap já registrado foi conferido no relatório. O protocolo continua exploratório porque 2024 já havia influenciado decisões.
- O artigo ganhou quatro tabelas ao todo, um gráfico das OR ponderadas com IC95% e um diagrama das partes implementadas. A bibliografia contém 28 referências. Os links encurtados na impressão mantêm os endereços completos. Os arquivos SBC fornecidos foram conferidos byte a byte.
- O formulário familiar falhava porque a importação de regras do diário havia sido substituída durante a integração anterior. A importação foi corrigida e a página de pesquisa passou a mencionar a análise ponderada. Os testes de rotina, interface familiar, desenho e figuras passaram (13 testes). A suíte completa teve 93 aprovações, duas falhas e nove subtestes aprovados. As falhas foram na interface de pesquisa legada, que ainda resolve relatórios pelos caminhos antigos, e no manifesto de harmonização, cujo caminho de documentação aponta para outro computador. A suíte foi executada com o diretório temporário sob o workspace para contornar a ACL do Windows.

## Entregáveis e verificação

O resultado numérico complementar está em `resultados_reproducao/desenho_nsch.json`. O controle de evidências vincula cada grupo de resultados ao relatório, método ou fonte. A checagem estática confrontou tabelas com as saídas, confirmou chaves citadas, referências cruzadas, estilos e arquivos de figuras. O gráfico foi inspecionado visualmente.

O ZIP da revisão inclui o manuscrito, a bibliografia, os dois arquivos de estilo e a imagem ponderada. O comando local de compilação não pôde iniciar porque pdfLaTeX está indisponível. A quebra de página final e o layout completo precisam ser verificados no PDF da revisão. A avaliação do protótipo com famílias e a validação temporal independente continuam pendentes.
