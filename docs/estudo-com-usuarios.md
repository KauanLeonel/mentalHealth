# Pesquisa 2: avaliação do protótipo com famílias (proposta)

> Pergunta: uma plataforma de acompanhamento da rotina digital ajuda famílias a compreender seus hábitos e construir planos de uso considerados úteis por elas?

A NSCH não mede compreensão, adesão a planos nem bem-estar de quem usa o aplicativo. Responder a essa pergunta exige um estudo próprio, ainda **não realizado**. Este documento organiza o que o protótipo já oferece para esse estudo e o que precisa ser definido antes de começar.

## O que o protótipo já oferece

| Necessidade do estudo | Recurso | Onde |
|---|---|---|
| Registro da rotina | Diário: tela, sono, atividades (inclusive as definidas pela família), "a tela atrapalhou?", quem registrou | `mindscreen.rotina.criar_registro` |
| Compreensão dos gráficos | Histórico com tela e sono no mesmo gráfico, linhas dos objetivos, atividades e resumo de 7 dias | `mindscreen.painel.routine_history_chart`, `resumo_periodo` |
| Plano escolhido pela família | Combinados, objetivos com valores escolhidos pela família e progresso | `criar_objetivo`, `progresso_objetivos` |
| Reflexão | Perguntas para conversa com respostas opcionais | `registrar_reflexao` |
| Medidas de percepção | Página "Avaliar o protótipo": compreensão dos gráficos, utilidade do plano e facilidade (1–5), intenção de voltar a usar e comentário | `criar_avaliacao` |
| Coleta controlada pelo participante | Botão "Baixar meus dados (JSON)". O app não guarda nada; o participante decide se envia o arquivo | `exportar` |

## A definir antes de qualquer coleta

1. **Ética.** Submeter o protocolo ao Comitê de Ética em Pesquisa da instituição (Plataforma Brasil). Prever TCLE para responsáveis e TALE para crianças e adolescentes, e tratar os dados conforme a LGPD, que considera os dados de saúde e de crianças e adolescentes como sensíveis ou de proteção especial.
2. **Desenho.** Começar por um estudo de usabilidade qualitativo (tarefas guiadas e entrevistas com responsáveis e adolescentes) antes de qualquer acompanhamento longitudinal.
3. **Tarefas sugeridas.** Registrar três dias; responder o que o gráfico mostra (por exemplo, "em qual dia houve mais tela?"); criar um objetivo e um combinado; encontrar quando procurar um profissional.
4. **Medidas.** Acerto nas tarefas de leitura dos gráficos, notas da página de avaliação, intenção de retorno e temas das entrevistas. Se forem usados instrumentos padronizados (por exemplo, uma escala de usabilidade), verificar se existe versão validada em português.
5. **Critérios de continuidade.** Definir antes da coleta o que justificaria investir em armazenamento persistente e coleta longitudinal, por exemplo: maioria entende os gráficos e considera o plano útil.

## O que não deve ser afirmado

- Que o aplicativo melhora a saúde mental, o sono ou o bem-estar. Isso exigiria outro desenho de estudo.
- Que os resultados da NSCH validam recomendações individuais ou servem de referência para uma família específica.
