# Literacia em IA (Art. 4): programa e registos

Estado: versão 1.0 · 2026-10-21 · Cobre os testes L1, L2, L3, L4 e H10

## 1. Público

Bárbara, Madalena e administradores. Qualquer pessoa que opere, valide ou decida com base nos workflows de IA.

## 2. Conteúdo mínimo (L2), sessão de 60 minutos

1. O que é um LLM e o que faz em cada uma das 4 tarefas (`03-fichas-uso-ia.md`).
2. O que **não** faz: não decide preços, não aprova, não envia ao cliente.
3. Erros possíveis: números mal lidos ("1.250" vs "1,25"), moeda em falta, país trocado, pedidos "inventados" a partir de newsletters, texto de injeção em emails/PDF.
4. Viés de automação: confiar demasiado num resultado "limpo". Verificar sempre a fonte (email/PDF) antes de aprovar.
5. Como corrigir: editar o registo em Supabase/ferramenta de validação e marcar a cotação `a_rever`.
6. A quem reportar: responsável técnico `__________` (registar em `06-retencao-rgpd-e-incidentes.md`).
7. Regras de aprovação: só "OK" na primeira linha, de remetente autorizado.
8. Dados: não colar dados pessoais sensíveis ou de clientes finais em prompts.

## 3. Verificação de compreensão (L3 e H10)

Exercício com dados de teste:
- Mostrar 5 resumos de extração, 1 com uma cotação trocada de propósito (ex.: 1.250 € lido como 1,25 €). A pessoa deve identificar o erro, dizer onde confirmar e a quem reportar.
- Critério: identifica o erro e a via de reporte.

| Participante | Data | Erro identificado (S/N) | Via de reporte correta (S/N) |
| --- | --- | --- | --- |
| Bárbara | | | |
| Madalena | | | |

## 4. Registo de presença (L1)

| Nome | Função | Data | Assinatura |
| --- | --- | --- | --- |
| | | | |

Formador: `__________` · Material: este documento

## 5. Novos membros (L4)

Quem entrar e usar o sistema faz esta formação nos primeiros 30 dias. Acrescentar à checklist de integração: "formação em literacia de IA concluída (data)".
