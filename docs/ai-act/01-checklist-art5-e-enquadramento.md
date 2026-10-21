# Classificação AI Act: práticas proibidas (Art. 5) e alto risco (Art. 6 / Anexo III)

Estado: **rascunho para aprovação da gestão** · Versão 1.0 · 2026-10-21 · Cobre os testes C1, C2, C3, C5
Nota: documento técnico de apoio, não é parecer jurídico. A confirmação final cabe ao jurista (ver secção 4).

## 1. Sistema avaliado

Automação de propostas comerciais de cortiça (B2B, exportação): receção de pedidos por email, cotação de frete a transportadoras, enriquecimento com requisitos do país de destino, validação humana e envio da proposta. Utiliza o modelo `anthropic/claude-haiku-4.5` via OpenRouter em 3 workflows (WF1, WF3, WF6), com 4 tarefas (ver `03-fichas-uso-ia.md`).

## 2. Checklist Art. 5(1): práticas proibidas (teste C1)

| # | Prática proibida | Aplica-se? | Justificação |
| --- | --- | --- | --- |
| a | Técnicas subliminares, manipuladoras ou enganosas que distorcem o comportamento | Não | O LLM redige apenas pedidos de cotação a transportadoras com texto validado em código. Não há persuasão de pessoas. |
| b | Exploração de vulnerabilidades (idade, deficiência, situação social) | Não | Destinatários são empresas (transportadoras, clientes B2B). |
| c | Pontuação social | Não | Nenhuma pessoa é pontuada. |
| d | Avaliação do risco de cometer crimes com base em perfis | Não | Fora de âmbito. |
| e | Bases de dados de reconhecimento facial por recolha não dirigida | Não | Sem imagens nem biometria. |
| f | Inferência de emoções no trabalho ou na escola | Não | Sem análise de emoções. |
| g | Categorização biométrica para inferir dados sensíveis | Não | Sem biometria. |
| h | Identificação biométrica remota em tempo real em espaços públicos | Não | Fora de âmbito. |

Verificado por inspeção dos prompts e nós LLM dos workflows em 2026-10-21. Reverificar em cada alteração (ver `05-gestao-de-mudanca.md`).

## 3. Enquadramento no Anexo III (teste C2)

| Área do Anexo III | Aplica-se? | Justificação |
| --- | --- | --- |
| 1. Biometria | Não | Não usada. |
| 2. Infraestruturas críticas | Não | O sistema não gere segurança de infraestruturas. |
| 3. Educação e formação | Não | Não usada. |
| 4. Emprego e gestão de trabalhadores | Não | Não avalia nem seleciona pessoas. |
| 5. Serviços essenciais (crédito, seguros, prestações públicas, emergências) | Não | Não avalia solvência nem elegibilidade. |
| 6. Aplicação da lei | Não | Não usada. |
| 7. Migração, asilo e fronteiras | Não | Não usada. |
| 8. Justiça e processos democráticos | Não | Não usada. |

**Conclusão:** o sistema não é de alto risco. Classificação: risco limitado/mínimo, com boas práticas voluntárias (transparência, supervisão humana, registo). Obrigação direta aplicável: literacia em IA (Art. 4).

## 4. Controlo: a IA não decide (teste C3)

O output do LLM nunca chega diretamente a preço final, aprovação ou envio ao cliente:

- Preço final (`preco_final`) e frete escolhido são definidos por pessoas/código, não pelo LLM.
- Aprovação da proposta: só por resposta "OK" de remetente autorizado (WF8), depois de validação humana.
- Emails ao cliente (WF9, WF10, WF12) usam modelos fixos, sem nós LLM.
- Saídas do LLM nos WF1/WF3/WF6 passam por nós de código de validação (esquema, listas permitidas, regras de texto) com reserva determinística quando falham.

## 5. Papel da empresa (teste C5)

Entendimento técnico: **responsável pela implantação (deployer)** do modelo de terceiros e, por montar o sistema, possível **fornecedor** do sistema de IA. Dado o risco limitado, as obrigações práticas são as do Art. 4 e, se aplicável, Art. 50.

Pendente de parecer do jurista:
- [ ] Confirmar o papel (deployer e/ou fornecedor)
- [ ] Confirmar que o sistema não é de alto risco
- Parecer arquivado em: `________________` · Data: `__________`

## 6. Aprovação

| Função | Nome | Data | Assinatura |
| --- | --- | --- | --- |
| Gestão | | | |
| Responsável do sistema | | | |
