# Prompt — Ata de reunião a partir da transcrição

Transforma a transcrição de uma reunião em uma **ata estruturada**: participantes,
pauta/temas, decisões, pendências e próximos passos com responsáveis.

## Entrada
- `output/<slug>.txt` — transcrição corrida crua gerada pelo Stage 01.
  (Se existir uma versão diarizada com falantes, prefira-a para identificar quem
  disse o quê — mas isso é opcional.)

## Saída
- `output/<slug>.ata.md` — ata em PT-BR.

## O que fazer

1. **Participantes**: liste quem participou, **quando inferível** pela transcrição
   (nomes citados, falantes que se identificam, vocativos). Se não der para
   identificar com segurança, escreva "Não identificados na transcrição" — **não
   invente nomes**.

2. **Pauta / temas tratados**: os assuntos discutidos, em tópicos. Reflete a ordem
   ou o agrupamento lógico da conversa.

3. **Decisões tomadas**: tudo que foi **acordado/decidido** de forma explícita.
   Cada decisão em uma linha objetiva. Se algo foi discutido mas **não** decidido,
   não liste aqui (vai para pendências).

4. **Pendências / pontos em aberto**: questões levantadas sem conclusão, dúvidas não
   resolvidas, temas adiados.

5. **Próximos passos / ações**: tarefas concretas combinadas. Para cada uma, indique
   o **responsável quando mencionado** e o **prazo quando mencionado**. Use o formato:
   `- [ ] <ação> — Responsável: <nome ou "a definir"> — Prazo: <prazo ou "—">`.

## Limites

- Baseie-se **somente** no que foi efetivamente dito. **Não invente** participantes,
  decisões, responsáveis ou prazos. Quando a informação não existe, marque como
  "a definir", "não mencionado" ou "—".
- Distinga **decisão** (acordado) de **discussão** (debatido sem fechar). Não promova
  uma conversa em aberto a decisão.
- Se a transcrição não for de uma reunião (ex.: monólogo, aula, áudio avulso),
  sinalize isso no topo e preencha apenas as seções que fizerem sentido.

## Formato da saída

Markdown em PT-BR, com esta estrutura:

```markdown
# Ata — <título/assunto da reunião>

**Data:** <se mencionada, senão "não informada">
**Participantes:** <lista ou "não identificados na transcrição">

## Pauta / temas

- <tema>

## Decisões

- <decisão>

## Pendências

- <ponto em aberto>

## Próximos passos

- [ ] <ação> — Responsável: <nome / a definir> — Prazo: <prazo / —>
```
