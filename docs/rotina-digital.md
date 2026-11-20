# Protótipo de rotina digital

**Bem-estar e rotina digital de crianças e adolescentes: uma plataforma de apoio à reflexão familiar baseada em dados.**

O protótipo ajuda responsáveis e adolescentes a observar, ao longo do tempo, como o uso de telas se encaixa na rotina (sono, atividade física, convivência e outras atividades que a família considera importantes) e a construir um plano de hábitos escolhido pela própria família. A referência de desenho é o plano de mídia familiar da American Academy of Pediatrics, que propõe planos adaptados à rotina e às prioridades de cada família. Essa referência não comprova que o aplicativo produza melhora de saúde.

O protótipo **não calcula escores de saúde, não faz previsões individuais e não usa os classificadores** das versões v1–v3. Os modelos foram treinados com relatos de responsáveis nos EUA e não foram validados clinicamente nem para famílias brasileiras.

## Páginas

| Página | O que faz | Regras |
|---|---|---|
| Diário de rotina | Tela recreativa e sono (horas), atividades da lista ou incluídas pela família, "a tela atrapalhou alguma atividade?" e quem registrou | `criar_registro`, `nova_atividade` |
| Histórico | Resumo dos últimos 7 dias, tela e sono no mesmo gráfico com as linhas dos objetivos, atividades, tabela e progresso dos objetivos | `resumo_periodo`, `progresso_objetivos`, `painel.routine_history_chart` |
| Plano em família | Combinados, objetivos configuráveis (limite de tela, horas de sono, dias com uma atividade) e perguntas de reflexão com respostas opcionais | `criar_objetivo`, `registrar_reflexao` |
| Saiba mais | Conteúdo educativo com fontes, quando conversar com um profissional e contatos de urgência (SAMU 192, CVV 188) | `configs/conteudo_familiar.json`, `mindscreen.conteudo` |
| Pesquisa | O que a análise da NSCH encontrou, em linguagem simples, com gráficos e limites | `reports/modelagem/v4_contribuicao` (ver `docs/contribuicao-incremental.md`) |
| Avaliar o protótipo | Compreensão dos gráficos, utilidade do plano, facilidade, intenção de voltar a usar | `criar_avaliacao` (ver `docs/estudo-com-usuarios.md`) |

## Decisões

- Valores não informados permanecem ausentes; zero é um valor explicitamente informado. Datas futuras e durações fora de 0–24 horas são rejeitadas. Uma nova entrada da mesma data substitui a anterior.
- Médias e progresso usam apenas os dias em que o valor foi informado. Um dia sem informação **não** conta como objetivo não alcançado.
- Os números dos objetivos são escolhidos pela família. O aplicativo não sugere limites nem compara a família com a população da NSCH.
- O perfil da NSCH aparece apenas na página Pesquisa e traz um aviso de que não serve de referência para uma família específica.
- Registros, plano, reflexões e avaliação ficam em memória na sessão Streamlit, sem gravação pelo aplicativo em arquivo, log ou banco de dados. O botão de apagar remove esses dados. "Baixar meus dados" gera um JSON somente quando solicitado. Essa arquitetura não garante nada sobre infraestrutura de hospedagem, navegador ou logs de terceiros e não substitui uma revisão antes da implantação.
- A interface só apresenta. Regras ficam em `src/mindscreen/rotina.py`, conteúdo em `configs/conteudo_familiar.json`, gráficos em `src/mindscreen/painel.py` e o caminho dos resultados em `configs/interface.json` (chave `contribuicao`).

A interface anterior, inclusive o simulador exploratório, foi preservada em `app/pesquisa_streamlit.py` para pesquisa, sem acesso pelo aplicativo familiar.

Os dados da NSCH e os registros do aplicativo têm origens, populações e medições distintas. A análise da NSCH informa o contexto da pesquisa, mas não valida recomendações individuais nem a utilidade da interface. Nenhuma avaliação com famílias foi realizada. A proposta de estudo está em `docs/estudo-com-usuarios.md`. Não se devem apresentar benefícios clínicos sem um estudo adequado.
