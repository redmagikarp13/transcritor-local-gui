# Prompt — Limpeza de transcrição

Transforma uma transcrição crua do Whisper em um texto **legível**, removendo
vícios de fala e corrigindo pontuação, **sem alterar, resumir ou inventar nada**
do que foi dito.

## Entrada
- `output/<slug>.txt` — transcrição corrida crua gerada pelo Stage 01.

## Saída
- `output/<slug>.limpo.md` — mesmo conteúdo, limpo e formatado em parágrafos.

## O que fazer

1. **Remover vícios de fala e ruído de oralidade**, mantendo o sentido intacto:
   - Bordões e muletas: "né", "tipo", "aí", "então assim", "sabe?", "é...", "tá?",
     "olha", "assim ó", "meio que".
   - Hesitações e sons de preenchimento: "éééh", "ãã", "hmm", "uhum", "tipo assim".
   - Repetições imediatas de palavra ("eu eu fui", "a a gente") e gaguejos.
   - Falsos começos e frases abandonadas ("eu ia dizer que... bom, deixa pra lá").
     Quando o falante reformula no meio, **mantenha apenas a versão final completa**
     da ideia, descartando o começo interrompido.

2. **Corrigir pontuação e ortografia**:
   - Inserir vírgulas, pontos finais, pontos de interrogação e exclamação.
   - Corrigir maiúsculas (início de frase, nomes próprios).
   - Corrigir erros óbvios de transcrição do Whisper (palavra grudada, capitalização
     estranha) **somente quando a intenção é inequívoca**. Na dúvida, preserve.

3. **Quebrar em parágrafos legíveis**:
   - Agrupar frases por assunto/ideia em parágrafos curtos.
   - Quando houver troca evidente de assunto, começar novo parágrafo.

## Limites rígidos (NÃO fazer)

- **NÃO resumir.** A íntegra do que foi dito deve permanecer — só sai o que é puro
  ruído de oralidade (muletas, hesitações, repetições, falsos começos).
- **NÃO parafrasear** nem "melhorar" o vocabulário. Preserve as palavras e o tom de
  quem falou; você está limpando, não reescrevendo.
- **NÃO inventar** conteúdo, dados, nomes ou conclusões que não estejam no texto.
- **NÃO reordenar** ideias nem mudar o significado de nenhuma frase.
- Se um trecho estiver incompreensível ou a transcrição claramente falhou, marque
  com `[inaudível]` em vez de adivinhar.

## Formato da saída

Texto corrido em parágrafos, em PT-BR. Sem cabeçalhos extras, sem comentários seus,
sem metadados — apenas a transcrição limpa.
