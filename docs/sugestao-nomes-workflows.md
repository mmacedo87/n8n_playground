# Sugestão de nomes para os fluxos de trabalho do n8n

Criado em 2026-10-17. Nada foi renomeado no n8n: são apenas sugestões.

**Critério:** manter a referência `WFx` e trocar o resto do nome por algo que diga o que o fluxo faz e em que passo do processo se encontra. Formato: `WFx - Verbo + objeto (contexto)`.

**Base da análise:** li o conteúdo completo (nós e código) de WF2, WF5, WF6 e WF9. Quanto aos restantes, baseei-me na descrição e nas etiquetas guardadas no n8n; convém confirmar se algum nome fica impreciso depois de os abrires.

## Processo de propostas (etiqueta `propostas`)

Ordem do processo: pedido → extração → frete → conformidade → validação → aprovação → envio → confirmação → expedição → acompanhamento.

| Ref. | Nome atual | Nome sugerido | O que faz (resumo) |
|---|---|---|---|
| WF1 | WF1 - Extrair pedido do email | **WF1 - Extrair o pedido de proposta de uma mensagem de correio eletrónico** | Recebe uma mensagem e devolve o pedido estruturado, extraído por modelo de linguagem e validado em código, com campos em falta, grau de confiança e rascunho de resposta. |
| WF2 | WF2 - Pedido de proposta | **WF2 - Registar o pedido de proposta e confirmar a receção** | Formulário ou chamada de outro fluxo: grava a proposta no Supabase (código PRP), envia a confirmação por correio eletrónico e dispara o WF3, o WF4 e o aviso no Slack. |
| WF3 | WF3 - Pedido de cotação de frete | **WF3 - Pedir cotações de frete às transportadoras** | Envia um pedido de cotação a até 5 transportadoras (cópia oculta), com registo por transportadora. |
| WF4 | WF4 - Enriquecimento de proposta | **WF4 - Apurar conformidade e direitos aduaneiros** | Grava o código pautal, a taxa por destino e as notas fitossanitárias, sem modelo de linguagem. |
| WF5 | WF5 - Resumo para validação | **WF5 - Enviar o resumo da proposta para validação (Bárbara)** | Envia à Bárbara o resumo com dados, cotações e conformidade; passa a proposta a `em_validacao`; avisa no Slack. |
| WF6 | WF6 - Ler cotações das transportadoras | **WF6 - Ler as respostas de frete e gravar as cotações (texto e PDF)** | Lê as mensagens e os PDF das transportadoras, associa-os à proposta, extrai a cotação por modelo de linguagem, valida em código, grava e reenvia o resumo (WF5). |
| WF8 | WF8 - Aprovação da Bárbara por email | **WF8 - Aprovar a proposta pela resposta da Bárbara (OK)** | Lê a resposta da Bárbara; só «OK/aprovo» na primeira linha aprova; qualquer outro texto apenas avisa no Slack. |
| WF9 | WF9 - Envio da proposta ao cliente | **WF9 - Enviar ao cliente a proposta aprovada** | Envia a mensagem em português ou inglês com a ligação de confirmação; recusa propostas sem preço final; passa a `enviada`. |
| WF10 | WF10 - Confirmação da encomenda | **WF10 - Confirmar a encomenda pela ligação enviada ao cliente** | Ligação web em dois passos (resumo e botão); marca a proposta como aceite, cria a expedição e avisa. |
| WF11 | WF11 - Plano de expedição | **WF11 - Planear a expedição (formulário da Madalena)** | Formulário que grava produção, existências, recolha, modo e transportadora; passa a `em_expedicao` e chama o WF12. |
| WF12 | WF12 - Follow-up ao cliente | **WF12 - Enviar ao cliente o plano final de expedição** | Envia ao cliente o modo de expedição, a recolha e a chegada estimada; marca a proposta como concluída. |

### Falta o WF7
Não existe nenhum WF7 no n8n. Sugestão: reservar o número para a **fase 5 do Moloni** (ver `plano_workflow_moloni_fase5.md`), com o nome **WF7 - Calcular o preço final da proposta (Moloni)**. Se se mantiver a ordem do processo, o preço deve ficar entre o frete e a validação.

## Fluxos auxiliares e de erro

| Nome atual | Nome sugerido | O que faz |
|---|---|---|
| Notificar Slack | **Auxiliar - Enviar aviso curto para o Slack** | Fluxo reutilizável: publica uma mensagem num canal (propostas, cotacoes ou estado). |
| Mail Error Flow | **Erro geral - Avisar por correio eletrónico quando um fluxo falha** | Envia o nome do fluxo, o nó que falhou, o erro e a ligação à execução. |
| WF2 Error Flow - Pedido de proposta | **WF2 Erro - Avisar se o registo do pedido falhou** | Indica se a proposta chegou a ser gravada e que o WF3 não foi chamado. |

Sugestão: usar os prefixos `Auxiliar -` e `Erro ...`, para que estes fluxos fiquem agrupados e não se confundam com a sequência WFx.

## Fora do processo de propostas

| Nome atual | Nome sugerido | Nota |
|---|---|---|
| Read Outlook Messages | **Teste - Criar rascunhos de resposta às mensagens da pasta 1 (Outlook)** | Tem texto fixo provisório e arranque manual; o nome atual não diz que cria rascunhos. O prefixo `Teste -` evita confusões. |
| Claude → Slack \| Estado das tarefas | **Claude - Publicar o estado das tarefas no Slack** | Sem descrição no n8n; nome inferido do atual. Confirmar o que faz antes de renomear. |

## Notas
- Os nomes ficaram mais longos de propósito, para dizerem o que fazem. Para versões mais curtas, bastam o verbo e o objeto (por exemplo, `WF5 - Enviar o resumo para validação`).
- A descrição do WF1 e do WF2 está cortada no n8n; convém completá-las ao renomear.
- Renomear não afeta as ligações: as chamadas entre fluxos usam o identificador, não o nome. A exceção são as referências em texto, como os comentários e as notas dos nós.
- Nomes próprios (Slack, Outlook, Supabase, Moloni, n8n, Claude) mantêm-se como são.
