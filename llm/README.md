# llm/ — geração de .nk por LLM

Material para o system prompt que ensina um LLM a gerar `.nk` (TCL do
Nuke) válido, usando o catálogo medido do projeto.

| Arquivo | O que é |
|---|---|
| `build_mvp_subset.py` | gera o subset curado a partir de `data/nodes.json` + `data/inputs_default.json`. A curadoria (quais knobs importam por classe) é editorial e vive no script; **toda entrada é validada contra o catálogo real** — classe inexistente ou knob com nome errado aborta com sugestão por proximidade. |
| `mvp_subset.json` | o subset gerado: 33 classes que cobrem ~80% de comp, ~2k tokens — cabe inline no prompt. Versionado porque só contém classes padrão do Nuke (nenhum dado de pipeline). |

## Campos por classe

- `arity_default` — quantos itens da pilha o paste consome sem o knob
  `inputs` (medido; `null` = não medido, lei extrapolada: 1). Informativo:
  o dialeto de geração **sempre** grava o knob explícito.
- `max_inputs` / `mask_input` — do catálogo (contam opcionais).
- `input_labels` — semântica B/A/mask para a família merge.
- `knobs` — curados e validados; o LLM só deve setar knobs desta lista.
- `menu` — nome amigável quando difere da classe TCL (Keylight é classe
  OFX longa; Shuffle moderno = `Shuffle2`; Primatte = `Primatte3`).
- `notes` — regras de geração (ex.: Roto **nunca** gera `curves`).

## Decisões do dialeto de geração (v0)

- Conexões **sempre explícitas**: knob `inputs N` em todo nó (inclusive
  `inputs 0` em desconectados), `set Nx [stack 0]` após cada nó,
  `push $Nx` por conexão, `push 0` para buraco intencional.
- O modelo **não** gera `xpos`/`ypos` — o viewer faz o layout no import e
  o export grava posições re-baseadas.
- Bloco TCL único por resposta; refino = bloco completo substitutivo.
- Para refinar setup existente: entrada é o **JSON canônico** do viewer
  (TCL bruto custa ~60× mais tokens por causa de curvas de Roto), com
  knobs pesados elididos — nós elididos são intocáveis em conteúdo.

Regenerar após atualizar os dumps de `data/`:

```sh
python3 llm/build_mvp_subset.py
```
