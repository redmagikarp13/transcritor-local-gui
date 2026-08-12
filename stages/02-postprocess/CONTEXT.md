# Stage 02 — Pós-processamento por IA (opcional)

Transforma a **transcrição crua** do Stage 01 em algo útil — texto limpo, resumo
ou ata — usando o Claude. É o único stage que gasta token de IA, e é **opcional**:
só roda quando você quiser ir além do `.txt` cru.

- **Entrada:** `output/<slug>.txt` (transcrição corrida gerada pelo Stage 01).
- **Saída:** `output/<slug>.<tipo>.md` (ex.: `<slug>.limpo.md`, `<slug>.resumo.md`, `<slug>.ata.md`).
- **Idioma:** tudo sai em **pt-BR** (o idioma do conteúdo transcrito). Os prompts
  preservam o português do áudio; não traduzem.

> Pré-requisito: o Stage 01 já precisa ter rodado e produzido `output/<slug>.txt`.
> Se ainda não há transcrição crua, volte para `stages/01-transcribe/CONTEXT.md`.

---

## Os três modos

Cada modo é um prompt em `references/`. Escolha pelo que você precisa do material:

| Prompt | O que faz | Saída |
|---|---|---|
| `references/limpeza.md` | Remove vícios de fala ("né", "tipo", "ã", repetições), corrige pontuação e quebra em parágrafos legíveis. **Não muda o conteúdo nem resume** — só limpa. | `output/<slug>.limpo.md` |
| `references/resumo.md` | Resumo executivo curto + bullets dos tópicos principais. Para quando você só quer saber do que se tratou. | `output/<slug>.resumo.md` |
| `references/ata.md` | Estrutura como ata de reunião: participantes, pauta, decisões, pendências e próximos passos. Para reuniões (Solunar etc.). | `output/<slug>.ata.md` |

### Quando usar cada um

- **`limpeza`** — quando você quer o texto **inteiro**, só que legível: vai virar
  post, artigo, material de aula, ou base para revisão. Mantém tudo o que foi dito.
- **`resumo`** — quando o áudio é longo e você só precisa do **panorama**: aula,
  palestra, entrevista da qual quer extrair os pontos sem reler tudo.
- **`ata`** — quando é uma **reunião com decisões e encaminhamentos**: você quer
  saber quem ficou de fazer o quê, o que foi decidido e o que ficou pendente.

> Pode encadear: rode `limpeza` primeiro e depois `resumo`/`ata` sobre o texto
> limpo, se quiser mais qualidade. Mas em geral o prompt já lida bem com o `.txt` cru.

---

## Como acionar

Não há script aqui — quem roda este stage é o **Claude**, lendo o arquivo e
aplicando o prompt. Fluxo:

1. Abra o Claude Code **dentro do workspace** `transcritor-local/`.
2. Peça em linguagem natural, citando o arquivo e o modo. Exemplos:
   - `"limpa a transcrição output/reuniao-solunar.txt"`
   - `"faz um resumo de output/aula-cefor.txt"`
   - `"vira ata a transcrição output/reuniao-solunar.txt"`
3. O Claude lê `references/<modo>.md`, aplica sobre `output/<slug>.txt` e escreve
   o resultado em `output/<slug>.<tipo>.md`.

Se você não disser o modo, o Claude pergunta qual dos três você quer (limpeza,
resumo ou ata).

---

## Routing

| Tarefa | Carregar |
|---|---|
| Limpar o texto cru | `references/limpeza.md` + `output/<slug>.txt` |
| Resumir o conteúdo | `references/resumo.md` + `output/<slug>.txt` |
| Gerar ata de reunião | `references/ata.md` + `output/<slug>.txt` |
| Gerar a transcrição crua antes | `../01-transcribe/CONTEXT.md` |

## Convenções

- O `<slug>` é o mesmo nome-base do arquivo de áudio original (ex.: `reuniao-solunar`),
  herdado do Stage 01 — mantenha-o consistente em todos os arquivos da pipeline.
- Saídas sempre em `output/`, em Markdown (`.md`), com o sufixo do tipo
  (`.limpo` / `.resumo` / `.ata`) entre o slug e a extensão.
- O `output/<slug>.txt` original **nunca** é sobrescrito; o pós-processamento
  sempre escreve um arquivo novo.
