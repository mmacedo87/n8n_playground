# Gestão de mudança e reavaliação

Estado: versão 1.0 · 2026-10-21 · Cobre os testes C6, V3, V4

## 1. O que dispara uma reavaliação

Qualquer um dos seguintes exige repetir a checklist (`01-checklist-art5-e-enquadramento.md`) e atualizar as fichas (`03-fichas-uso-ia.md`):

- Mudança de modelo ou fornecedor (hoje `anthropic/claude-haiku-4.5` via OpenRouter).
- Alteração de um prompt (incrementar `versao_prompt` em `ai_log`).
- Novo workflow ou nó com LLM.
- Novo caso de uso (por exemplo avaliar pessoas, aprovar sem humano, enviar a clientes texto gerado por IA).
- Nova categoria de dados enviada ao LLM.
- Mudança regulatória relevante.

## 2. Procedimento

1. Registar o pedido de mudança (o quê, porquê, quem).
2. Responder às 4 perguntas: (a) cai no Art. 5? (b) cai no Anexo III? (c) a IA passa a decidir algo? (d) há novos dados pessoais?
3. Se (a), (b) ou (c) forem "sim": parar e pedir parecer jurídico.
4. Atualizar ficha, `versao_prompt` e documentação técnica.
5. Correr a bateria de testes (`testes-ai-act.md`, 🔴) e os testes de regressão existentes.
6. Fazer commit no branch `dev` com mensagem do que mudou; aprovar a passagem para produção.

## 3. Registo de mudanças

| Data | Mudança | Reavaliação (S/N) | Responsável | Resultado |
| --- | --- | --- | --- | --- |
| 2026-10-21 | Criação da documentação AI Act v1.0 | S | | |

## 4. Revisões periódicas (V3, V4)

| Revisão | Frequência | Última | Próxima |
| --- | --- | --- | --- |
| Reclassificação AI Act (V3) | Semestral e em cada mudança relevante | 2026-10-21 | 2027-04-21 |
| Prazos legais, incluindo adiamentos (V4), com o jurista | Semestral | | 2027-04-21 |
| Amostra de 10 execuções de IA (V1) | Mensal nos 3 primeiros meses, depois trimestral | | |
| Relatório de incidentes (V2) | Trimestral | | |
