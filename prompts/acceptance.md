# Casos de aceitação — v0 do gerador de .nk

Três entradas de teste e o comportamento esperado, em traços gerais.
Rodar contra o prompt montado (core.md + catalog.json) num modelo frio
(sem contexto do projeto). O bloco gerado deve passar no viewer com
`{ok: true}` ou com warnings justificados.

## Caso 1 — pedido típico (gera direto)

**Entrada:** "Tenho um plate EXR e três mattes de Roto que eu mesmo vou
desenhar (key light, fill, rim). Monta uma decomposição de luz: cada
luz isolada com um Grade mascarado, e o rebuild somando as três de
volta."

**Esperado:**
- Gera sem perguntar (fontes, método e objetivo estão especificados) —
  premissas declaradas cobrem o resto (linear/rgba, path placeholder).
- Bloco único: `Read` (`inputs 0`, path placeholder), 3× `Roto` vazios
  nomeados (`RotoKeyLight`…, **sem** `curves`), 3× `Grade` com
  `inputs 1+1` (mask = Roto correspondente), rebuild com `Merge2`
  (`operation plus` ou equivalente justificado) — todo nó com
  `inputs N` explícito, `set N<Nome> [stack 0]` após cada um, pushes do
  índice maior para o 0.
- **Não** deve conter: `xpos`/`ypos`, `curves`, `version`, classe ou
  knob fora do catálogo, nomes genéricos (`Grade1`).
- Resposta inclui Raciocínio (1 linha por ramo: por que unpremult se
  usado, por que `plus` no rebuild) e Premissas.

## Caso 2 — deve disparar elicitação (não gera ainda)

**Entrada:** "Faz o key desse greenscreen."

**Esperado:**
- **Nenhum TCL.** No máximo 3 perguntas direcionadas, numa única
  mensagem — candidatas: (a) keyer preferido ou critério de escolha
  (Keylight / Primatte3 / IBK estão no catálogo); (b) entrega = só a
  matte ou comp sobre um BG (existe BG?); (c) condição do screen que
  bifurca o método (despill/edge tratados aqui ou depois?).
- Perguntas de valor fino (gain do keyer, clip) **não** aparecem — são
  premissa, não pergunta.

## Caso 3 — deve disparar recusa erro > chute

**Entrada:** "Isola o carro com um Cryptomatte e desfoca o fundo com
ZDefocus."

**Esperado:**
- **Nenhum TCL contendo `Cryptomatte` ou `ZDefocus2`** (fora do
  catálogo v0) — e nenhuma classe/knob inventado para "aproximar".
- O modelo declara o que está fora do catálogo, oferece o que existe
  dentro (`Defocus` para o desfoque; `Roto` placeholder como alternativa
  de matte) e pergunta como proceder.
- Aceitável gerar parcialmente **apenas** se o usuário já tiver
  escolhido as alternativas internas.
