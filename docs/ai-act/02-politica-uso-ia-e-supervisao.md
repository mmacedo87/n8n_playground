# Política de uso de IA e supervisão humana

Estado: **rascunho para aprovação da gestão** · Versão 1.0 · 2026-10-21 · Cobre os testes D3, H11, T3

## 1. Âmbito

Aplica-se a todos os workflows que usam IA na automação de propostas (WF1, WF3, WF6) e a quem os opera ou revê (comercial, administração, TI).

## 2. Princípios

1. **A IA assiste, não decide.** Preço, aprovação de propostas e envio ao cliente dependem de pessoas e de regras determinísticas.
2. **Validação em código.** Todo o output do LLM é validado (esquema, listas permitidas, regras de texto); em falha usa-se texto fixo ou regra de reserva, nunca um valor inventado.
3. **Transparência.** Mensagens com texto redigido por IA identificam esse apoio.
4. **Minimização de dados.** Ao LLM só vai o necessário; o `ai_log` guarda resumos sem dados pessoais (sem corpo de email).
5. **Rastreabilidade.** Cada uso de IA fica em `ai_log` (workflow, execução, modelo, versão do prompt).
6. **Reversibilidade.** Qualquer workflow pode ser desativado e revertido (ver `07-runbook-reversao.md`).

## 3. Proibido

- Usar a IA para avaliar, pontuar ou selecionar pessoas.
- Introduzir dados pessoais sensíveis ou de clientes finais em prompts.
- Enviar ao cliente texto gerado por IA sem passar pelas validações do workflow.
- Alterar modelo, prompt ou caso de uso sem seguir `05-gestao-de-mudanca.md`.

## 4. Supervisão humana (H11)

**Decisão a registar pela gestão** (opções para o email de pedido de cotação do WF3):

| Opção | Descrição | Risco |
| --- | --- | --- |
| A (proposta) | Envio automático a transportadoras com texto validado em código, frase de IA obrigatória e registo em `ai_log`. Revisão amostral mensal (10 execuções). | Baixo: destinatários são transportadoras, texto sem preços nem links. |
| B | Rascunho para aprovação da Bárbara antes de cada envio. | Mais lento, sem ganho relevante de segurança. |

Decisão: `[ ] A   [ ] B` · Decidido por: `__________` · Data: `__________`

Para propostas ao cliente: nenhuma sai sem resposta "OK" de remetente autorizado (WF8) e `preco_final` preenchido (WF9).

## 5. Transparência (Art. 50): decisão (T3)

Proposta: aplicar por boa prática, mesmo que a obrigação legal possa não existir.

Frase a acrescentar **em código**, depois da assinatura, em todos os emails do WF3 (não gerada pelo LLM):

> "Esta mensagem foi redigida com apoio de um sistema de inteligência artificial e enviada pelo nosso sistema de propostas."

Rodapés dos WF9 e WF12 (modelos fixos, sem IA): trocar "enviada com o apoio de um sistema automático, revista pela nossa equipa" por "Mensagem enviada automaticamente pelo nosso sistema de propostas." enquanto não houver revisão humana de cada mensagem.

Parecer do jurista sobre Art. 50(1) e 50(2): `________________` · Data: `__________`

## 6. Responsabilidades

| Função | Responsabilidade |
| --- | --- |
| Gestão | Aprovar esta política, decisões H11/T3, reavaliações |
| Bárbara (comercial) | Validar propostas, reportar erros de extração |
| Madalena | Idem, no seu âmbito |
| Responsável técnico | Manter workflows, `ai_log`, alertas e documentação |

## 7. Incidentes

Qualquer erro de IA com impacto (preço errado, email indevido, fuga de dados) regista-se no registo de incidentes (`06-retencao-rgpd-e-incidentes.md`), é corrigido e analisado em V2 (trimestral).

## 8. Aprovação

| Função | Nome | Data | Assinatura |
| --- | --- | --- | --- |
| Gestão | | | |
