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

## Protocolo de erro do validador (loop de correção)

O viewer expõe o botão **Feedback LLM** (header): JSON estruturado do
último import/render, para colar de volta no modelo. Os banners HTML
continuam como estavam — o canal estruturado é paralelo.

```json
{
  "ok": false,
  "stage": "parse | validate | parse+validate | json",
  "errors":   [ {"type": "...", "node": "...", "class": "...", "detail": "..."} ],
  "warnings": [ ... ]
}
```

Campos extras por tipo: `unknown_class` → `suggestion` (did-you-mean
contra tabela embutida + JSONs carregados); `unknown_knob` → `suggestion`
+ `valid_knobs` (lista completa se a classe tem ≤40 knobs úteis, senão
top-5 por distância de edição; knobs de infraestrutura como
name/xpos/tile_color ficam fora); `merge_missing_input` → `missing`
(["A"]…); `missing_ref` → `input`, `ref`; `ambiguous_arity` →
`min_inputs`/`max_inputs` quando conhecidos; `opaque_group` →
`hidden_nodes`; `duplicate_renamed` → `from`, `to`; `external_input` →
`input`; `not_representable` → `inputs`.

Tipos de erro: `unknown_class`, `unknown_knob`*, `ambiguous_arity`,
`bad_inputs_knob`, `multi_mask`, `not_representable`, `merge_missing_input`,
`missing_ref`, `duplicate_name`, `unknown_input_key`, `input_schema_mix`,
`unpaired_ab`, `cycle`, `group_too_many_inputs`, `group_unclosed`,
`orphan_end_group`, `clone_unsupported`, `unbalanced_braces`,
`knob_block_error`, `invalid_json`, `empty`. Tipos de warning:
`unknown_knob`*, `external_input`, `external_var`, `duplicate_renamed`,
`opaque_group`, `backdrop_ignored`, `viewer_ignored`, `line_ignored`,
`dot_dangling`. (*`unknown_knob` é warning — knob errado não quebra a
topologia, mas o LLM deve corrigir.)

Regenerar após atualizar os dumps de `data/`:

```sh
python3 llm/build_mvp_subset.py
```
