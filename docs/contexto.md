# Nuke DAG Viewer — contexto de desenvolvimento

> Artefato HTML autocontido que renderiza setups de Nuke a partir de JSON canônico, importa/exporta o formato de clipboard `.nk`, e existe para **compreensão** (reconstrução manual no Nuke), não automação. Critério de sucesso: olhar o grafo e reconstruir o setup sem nenhuma dúvida sobre qual input vai onde.

**Arquivos** (layout do repo `nuke-dag-viewer`): `nuke-dag-viewer.html` na raiz (artefato completo) · `extractors/map_nodes_v2.py` (plugins em disco, roda em `nuke -t`) · `extractors/map_nodes_gui.py` (núcleo compilado via menu, roda no Script Editor do Nuke GUI) · `extractors/merge_nodes.py` (mescla os dois dumps) · `extractors/map_inputs_gui.py` (aridade default de serialização por classe via `nuke.nodeCopy` multi-nó, Script Editor do GUI, autovalidação por âncoras) · `data/` fora do git: `nodes.json` (dump mesclado, Nuke 14.0v2, 565 classes: 423 núcleo + 449 plugins, 307 sobrepostas), `nodes_menu.json` (intermediário só do núcleo, 423 classes), `inputs_default.json` · `tests/fixtures/` fora do git: `nodes.txt` (regressão do bug do Roto), `nodes2.txt` (caso Group)

---

## Arquitetura

- **JSON canônico = fonte única de verdade.** O estado vive no dado; o desenho é derivado.
- **Três saídas do mesmo JSON:** grafo SVG interativo · snippet `.nk` (clipboard do Nuke) · tabela textual (1 linha/nó, inputs explícitos).
- **Uma entrada extra:** import de `.nk` colado (parser de semântica de pilha) → JSON → render.
- **Tabela de aridade em runtime:** o usuário carrega o `nodes.json` gerado do próprio Nuke; sobrepõe a tabela embutida.

## Schema JSON

```json
{
  "nodes": [
    {"name": "Merge12", "class": "Merge2",
     "knobs": {"operation": "minus"},
     "inputs": {"A": "Expression_V", "B": "Plate", "mask": "Roto1"},
     "pos": [-8857, 1009],
     "note": "plate − V"}
  ],
  "backdrops": [{"label": "...", "contains": ["Merge12"]}]
}
```

- **Inputs sempre nomeados** — chaves permitidas: `A`, `B`, `mask`, `input`. Regra inegociável: Merge sem A **e** B é inválido (erro visível: banner + nó vermelho tracejado + badge do pipe faltante). Sem conexões implícitas.
- `pos` (opcional) = `[xpos, ypos]` **verbatim** do script Nuke (âncora = canto superior esquerdo). Quando presente, vence o layout automático.
- `note` (opcional) = descrição humana; no import, o knob `label` do Nuke vira `note`.
- Aliases de Expression: `expr_r/g/b/a` ↔ `expr0..3` (conversão nos dois sentidos).

## Semântica de pilha do `.nk` (conhecimento crítico)

- **O topo da pilha vira o input 0.** Prova: cadeia linear sem `push` (`Read / Grade / Blur`) — cada nó conecta no anterior (topo) pelo input 0. Itens mais fundos → índices mais altos.
- **Merge2:** input0=B, input1=A, input2=mask. Ordem de push no export: **mask, A, B** (B por último = topo). `inputs 2+1` quando há mask; `1+1` para nó simples com mask.
- **Bug histórico (corrigido):** a 1ª implementação assumiu topo = índice mais alto. Parser e exportador compartilhavam a inversão → round-trip passava, mas paste real entrava com main↔mask e A↔B trocados. Lição: **testes round-trip contra si mesmo não detectam convenção invertida; precisa de oráculo externo** (paste real do Nuke / o caso forçado da cadeia linear).
- `set VAR [stack N]` = peek; `push $VAR` = push; `push 0` = desconectado de propósito.
- Knobs: um por linha; valor com chaves `{...}` balanceadas pode ser multilinha; sem chaves = até o fim da linha.

## Tolerância a trechos parciais (não quebra)

- `push $Nxxxx` de variável nunca definida → sentinela EXTERNA + warning (não fatal).
- Underflow de pilha → índices mais fundos viram externos; **determinístico**: topo recebe o que existe (Merge com 1 item: B=item, A=externo omitido).
- Externos ficam desconectados com warning nomeando nó+input; se for A/B de Merge, a validação acusa normalmente.
- **Continua fatal (ambiguidade real):** classe desconhecida sem knob `inputs`; `clone`; `Group/end_group`; chaves desbalanceadas. Política: **erro > chute, sempre**.

## Aridade de inputs — resolução em cadeia de prioridade

1. Knob `inputs` explícito no script (formas `2`, `2+1`, `1+1`, `0+1`).
2. Tabela embutida `NK_INPUTS` (~180 classes padrão por categoria de menu).
3. Erro informativo (cita min–max do `nodes.json` carregado, se a classe constar nele).

**Regras da tabela embutida:** nodes de aridade **variável** (Switch, ContactSheet, Scene, ScanlineRender, AppendClip, JoinViews…) ficam fora de propósito — o Nuke sempre serializa `inputs` neles. Nomes de **classe ≠ nomes de menu** (Exposure=`EXPTool`, Shuffle moderno=`Shuffle2`, Keylight=classe OFX longa); a doc oficial lista menus, o parser precisa de classes.

**Descobertas do dump real (v2, 565 classes):**
- `minInputs`/`maxInputs` contam inputs **opcionais** → NÃO servem como default (Grade: min 2, serializa 1; Merge2: min 3).
- **`n.inputs()` não serve para aridade default — testado e descartado.** De um node recém-criado e isolado, `n.inputs()` reflete inputs *conectados*, e deu **0 para as 565/565 classes**. Tampouco existe fórmula geral a partir de `minInputs`/`maxInputs`/`optionalInput`: a relação que funciona para Grade/Merge2/Blur/Dot/Transform (`min - 1` se há mask) erra Shuffle2 (dá 0, correto é 1). `map_nodes_v2.py`/`map_nodes_gui.py` não gravam mais o campo `"inputs"`. Aridade default vem só do knob `inputs` do script ou da `NK_INPUTS`.
- **Bug histórico (corrigido): `Roto:0` na `NK_INPUTS` — o correto é `Roto:1`.** Conclusão anterior ("Roto dá 1 pela fórmula, correto é 0") estava invertida. Prova por paste real: Rotos desconectados ganham `inputs 0` **explícito** (Nuke só serializa o knob quando difere do default), e um Roto com bg conectado vem **sem** o knob, precedido de `push` do item que ele consome. Sintoma do bug: off-by-one na pilha inteira após o Roto — todo Merge subsequente pegava o A da fileira errada e o último ramo ficava pendurado, com "input A vem de fora do trecho colado" no primeiro Merge. Lição: aridade default errada na tabela **não gera erro, gera grafo errado e plausível** — só oráculo externo (screenshot do Node Graph real) revelou. `RotoPaint:0`, `Precomp:0` e a família 3D `Camera*/Axis*/Light*` (input *look/axis* opcional) são suspeitos do mesmo erro — verificar com `map_inputs_gui.py`.
- **Aridade default É mensurável no GUI, mas só em cópia MULTI-nó** (método do `map_inputs_gui.py` v2): conectar k Dots (k=0,1,2,…) ao node, selecionar node+Dots+decoy e serializar com `nuke.nodeCopy(arquivo)`; o primeiro k em que a linha `inputs` é **omitida** no bloco do node é o default exato. O script embute âncoras de verdade conhecida (Constant=0, Blur=1, Merge2=2, Keymix=3, Switch=variável) e imprime PASS/FAIL — se falhar, não usar o JSON.
- **Cópia de nó ÚNICO não é oráculo (lição da v1 do script):** o Nuke especial-casa `nodeCopy` de um nó só — liga o input 0 ao `$cut_paste_input` (UX de "colar conecta na seleção") e **omite o knob `inputs` mesmo com o nó desconectado**. Resultado da v1: 396/423 classes mediram "0", âncoras todas erradas com padrão sistemático (default−1 ou invertido). Só a seleção multi-nó obriga o serializador ao modo exato de contagens de pop.
- **Script Editor roda nos globals do `__main__`, compartilhados com callbacks do pipeline (lição da v2):** `knobChanged`/`onCreate` do estúdio disparam a cada `setSelected`/`createNode` da sonda, e um callback que atribui a nomes comuns (`default`, `n`…) **sobrescreve as variáveis do script colado no meio da run** — na v2 isso pôs um objeto `Boolean_Knob` no dict de resultados (`TypeError` no `json.dump`). Regra: scripts de Script Editor fazem todo o trabalho **dentro de uma função** (locals são imunes), com tripwire de tipo antes de serializar. Os erros avulsos no console durante a sonda (scripts Python 2 do pipeline, `IndexError` em callbacks) são ruído esperado — as classes afetadas caem em `skipped`.
- `nuke.plugins()` só vê `.dll/.so/.gizmo` em disco → **perde o núcleo compilado** (Blur, Read, Dot, Roto, Expression...). Além disso, `nuke -t` (terminal) **não roda `nuke.menu()`** ("not in GUI mode") — o "menu walk" da v2 não funciona em modo terminal. Solução adotada: `map_nodes_gui.py` roda o menu walk dentro do Nuke GUI (colado no Script Editor) e escreve `nodes_menu.json`; `merge_nodes.py` mescla com o dump de plugins do terminal (`nodes.json`) → `nodes.json` final.
- PowerShell `>` grava **UTF-16 LE com BOM** e `nuke -t` imprime banner antes do JSON. O loader do artefato tolera ambos (detecta BOM, pula até a primeira `{`); v2/gui escrevem UTF-8 direto em arquivo. **Atenção:** se o script também escreve o arquivo internamente (como v2/gui fazem), não use `> nodes.json` — o redirect do PowerShell trava o arquivo e o `open()` do script falha com `PermissionError`.
- `Read` não aparece em nenhum dos dois dumps (nem núcleo nem plugins) — **causa provável identificada:** o item de menu Image>Read chama `nukescripts.create_read()` (abre o file browser), não `nuke.createNode(...)`, então o menu walk (que filtra por `"createNode"` no comando) nunca o captura. O `map_inputs_gui.py` v2 força a classe via `EXTRA_CLASSES = {"Read"}` — confirmar no próximo run.

**Benefício do dump mesmo em v1:** validação de nomes de knobs do JSON autorado (23k nomes) → warning amarelo por knob inexistente na classe, com aliases de Expression traduzidos antes de checar.

## Geometria e fidelidade visual (paridade com o Nuke)

- Fluxo top-down; cores por classe: Merge laranja `#d98a2b`, Grade/color azul `#4d7ab5`, Expression verde-água `#2fa890`, Shuffle/channel vermelho-escuro `#8a2f2f`, Blur/filter roxo `#7a4f9e`, Read/plate cinza `#6b6b6b`.
- **Âncora do Nuke:** nó 80×18, Dot 12×12, canto sup. esquerdo. Conversão para desenho alinha os **centros** (nós do viewer são maiores). `pos` no JSON fica verbatim.
- **Export re-baseado em (0,0):** xpos/ypos convertidos de volta ao referencial Nuke e subtraído o mínimo — offsets relativos preservados, paste não voa para longe (caso real: `xpos -8857`).
- **Mask:** entra pelo lado que **encara a fonte** (badge `m` acompanha); linha reta tracejada quando ambos têm `pos`, cotovelo lateral no layout automático. Pipes A/B com badges rotulados no topo.
- **Dots:** círculo pequeno cinza (não retângulo). Opção "Colapsar Dots" religa consumidores à fonte real transitivamente (dots = geometria, não semântica); warnings para dots com label e cadeias soltas.
- Conexões longas (>1 fileira) no layout automático roteiam por lane lateral para nunca atravessar nós.
- Navegação: scroll=zoom no cursor, arrastar/botão-do-meio/Alt=pan, pinch no mobile, **F=enquadrar**.
- Layout automático: camadas por caminho mais longo; filho segue o x do pipe **B** (tronco vertical à la Nuke).

## Defaults de import (UI)

- "Usar posições originais" **ligado** · "Colapsar Dots" **desligado** (com geometria real, dots cumprem a função). Inverter os dois = visão puramente semântica com layout automático.
- Nós novos entre renders pulsam em amarelo (estático com `prefers-reduced-motion`).
- BackdropNode e Viewer são ignorados com warning no import (backdrops se recriam via JSON).

## Metodologia de teste

Harness em Node: extrai as seções parser/export do HTML por regex (marcadores `importação .nk` … `fim importação .nk`), injeta stubs (`esc`, `isMergeClass`, `NODE_H`), roda asserts. Cobertura: round-trip parser↔export, fragmentos parciais, underflow determinístico, prioridade NK_USER, colapso de dots, pos verbatim, export zerado, ambiguidades fatais. **Regra aprendida:** fixtures devem imitar o formato real do Nuke (1 knob por linha; ordem de push correta) — dois bugs de fixture já ocorreram por desvio disso.

## Pendências / próximos passos possíveis

- **Rodar `map_inputs_gui.py` no Nuke GUI e cruzar `inputs_default.json` com a `NK_INPUTS`** — corrigir divergências (suspeitos: `RotoPaint:0`, `Precomp:0`, `Camera*/Axis*/Light*:0`). O bug do Roto provou que valor errado na tabela produz grafo errado *sem nenhum erro visível*.
- Atualizar o harness de teste: a cobertura "prioridade NK_USER" referia-se à aridade (`def`), que foi removida — revisar para cobrir a nova ordem (knob `inputs` → `NK_INPUTS` → erro citando min–max do `nodes.json`). Incluir fixture de regressão do caso Roto (cadeia do `nodes.txt`: `push $cut_paste_input` + Roto sem knob `inputs` consumindo o externo).
- Usar `optionalInput` do dump para validar se `mask` declarado faz sentido por classe.
- Mapeamento de 3 inputs sem mask é especial-caso de Keymix (B/A/mask); outras classes 3+ → erro de representabilidade.
- Tabela embutida tem entradas de menor confiança no bloco 3D (ex.: Card2) — dump v2 sobrepõe (via validação de knobs/min-max).
- Sem persistência entre sessões (artefato não usa storage do navegador): nodes.json se recarrega por sessão.
