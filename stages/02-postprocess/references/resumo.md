# Prompt — Resumo executivo da transcrição

Produz um **resumo executivo** da transcrição: um parágrafo de visão geral, os
pontos/tópicos principais em bullets e eventuais citações-chave literais.

## Entrada
- `output/<slug>.txt` — transcrição corrida crua gerada pelo Stage 01.

## Saída
- `output/<slug>.resumo.md` — resumo estruturado em PT-BR.

## O que fazer

1. **Resumo executivo (1 parágrafo)**: 3 a 6 frases que capturam, de forma densa,
   do que se tratou o áudio — assunto central, contexto e desfecho/conclusão (se
   houver). Quem ler só esse parágrafo já entende o essencial.

2. **Tópicos / pontos principais (bullets)**: liste os assuntos abordados e os
   pontos relevantes de cada um, na ordem em que aparecem. Use sub-bullets quando um
   tópico tiver desdobramentos. Seja específico (nomes, números, decisões mencionadas)
   sem copiar parágrafos inteiros.

3. **Citações-chave (opcional)**: se houver frases marcantes, decisões verbalizadas
   ou afirmações importantes ditas de forma especialmente clara, transcreva-as
   **literalmente** entre aspas. Inclua esta seção apenas se realmente houver
   citações que agreguem — caso contrário, omita-a.

## Limites

- Baseie-se **somente** no que está na transcrição. **Não invente** dados, conclusões
  ou interpretações que o texto não sustenta.
- Citações na seção de citações-chave devem ser **literais**. O resumo e os bullets
  podem ser parafraseados, desde que fiéis ao conteúdo.
- Se a transcrição for ambígua ou incompleta em algum ponto, sinalize com cautela
  ("parece indicar...", "menção a...") em vez de afirmar com certeza.

## Formato da saída

Markdown em PT-BR, com esta estrutura:

```markdown
## Resumo

<um parágrafo>

## Pontos principais

- <tópico/ponto>
- <tópico/ponto>

## Citações-chave

> "<citação literal>"
```

(Omita a seção "Citações-chave" se não houver citações relevantes.)
