# Nuke DAG Viewer — contexto de desenvolvimento

> Artefato HTML autocontido que renderiza setups de Nuke a partir de JSON canônico, importa/exporta o formato de clipboard `.nk`, e existe para **compreensão** (reconstrução manual no Nuke), não automação. Critério de sucesso: olhar o grafo e reconstruir o setup sem nenhuma dúvida sobre qual input vai onde.

**Arquivos** (layout do repo `nuke-dag-viewer`): `nuke-dag-viewer.html` na raiz (artefato completo) · `extractors/map_nodes_v2.py` (plugins em disco, roda em `nuke -t`) · `extractors/map_nodes_gui.py` (núcleo compilado via menu, roda no Script Editor do Nuke GUI) · `extractors/merge_nodes.py` (mescla os dois dumps) · `extractors/map_inputs_gui.py` (aridade default por classe via paste-oráculo, Script Editor do GUI, autovalidação por âncoras) · `extractors/probe_group_inputs.py` (diagnóstico pontual: aridade default de bloco `Group` sem knob, com controles) · `extractors/map_colors_gui.py` (cor de tile por classe → `colors_default.json`) · `data/` fora do git: `nodes.json` (dump mesclado, Nuke 14.0v2, 565 classes: 423 núcleo + 449 plugins, 307 sobrepostas), `nodes_menu.json` (intermediário só do núcleo, 423 classes), `inputs_default.json` · `llm/` (versionado): `build_mvp_subset.py` (gera `prompts/catalog.json`) · `prompts/` (versionado): `core.md` (system prompt v0) + `catalog.json` (subset curado) + `acceptance.md` (casos de aceitação) · `tests/fixtures/` fora do git: `nodes.txt` (regressão do bug do Roto), `nodes2.txt` (caso Group)

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
- **Group do usuário vira nó OPACO** (não quebra mais): o cabeçalho do `Group {...}` vira um nó com `note` "Group do usuário — conteúdo não expandido (K nós internos)" + warning; o corpo (nós internos, `set`/`push` internos, Groups aninhados) é pulado até o `end_group` casado sem tocar a pilha externa. Fiel à semântica: o grupo ocupa exatamente 1 slot da pilha (prova no paste real: `set N… [stack 0]` logo após o `end_group`). No export, vira `NoOp` placeholder (mesmo nome, label "era um Group do usuário", comentário `#` de aviso) — o `.nk` exportado continua válido e a topologia se preserva. Os ~261 gizmos NST do pipeline expandem como Group no copy/paste, então isso destrava a maior parte dos pastes reais do estúdio.
- **Continua fatal (ambiguidade real):** classe desconhecida sem knob `inputs`; `clone`; `end_group` órfão (trecho começando no meio de um Group); Group sem `end_group` casado (trecho cortado); Group com 2+ inputs (não representável no schema A/B/mask/input); chaves desbalanceadas. Group **sem** knob `inputs` consome 1 — **medido** pelo `probe_group_inputs.py` (default 1 independente do nº de `Input`s internos, até com zero). Política: **erro > chute, sempre**.

## Aridade de inputs — resolução em cadeia de prioridade

1. Knob `inputs` explícito no script (formas `2`, `2+1`, `1+1`, `0+1`).
2. Tabela embutida `NK_INPUTS` (~200 classes padrão, **valores medidos** no Nuke 14.0v2 pelo `map_inputs_gui.py` v6).
3. Erro informativo (cita min–max do `nodes.json` carregado, se a classe constar nele).

**A LEI DA ARIDADE DEFAULT (medida, v6):** bloco sem knob `inputs` consome **0** (generators puros: Read, Constant, CheckerBoard2, ColorBars, ColorWheel, CMSTestPattern, Input, AudioRead…) ou **1** (todas as outras 411 classes do menu) — **nunca 2+**. Merge2/ChannelMerge/Keymix com 2+ inputs conectados *sempre* serializam o knob; um Merge sem knob tem **só o B** conectado (o parser rotula o pop único de classes merge como `B`, e a validação "falta A" acusa — comportamento correto e visível). As classes de aridade variável (Switch, Scene, ScanlineRender…) também medem 1 e agora **estão na tabela**; na prática o Nuke sempre grava o knob nelas. Nomes de **classe ≠ nomes de menu** (Exposure=`EXPTool`, Shuffle moderno=`Shuffle2`, Keylight=classe OFX longa); a doc oficial lista menus, o parser precisa de classes.

**Descobertas do dump real (v2, 565 classes):**
- `minInputs`/`maxInputs` contam inputs **opcionais** → NÃO servem como default (Grade: min 2, serializa 1; Merge2: min 3).
- **`n.inputs()` não serve para aridade default — testado e descartado.** De um node recém-criado e isolado, `n.inputs()` reflete inputs *conectados*, e deu **0 para as 565/565 classes**. Tampouco existe fórmula geral a partir de `minInputs`/`maxInputs`/`optionalInput`: a relação que funciona para Grade/Merge2/Blur/Dot/Transform (`min - 1` se há mask) erra Shuffle2 (dá 0, correto é 1). `map_nodes_v2.py`/`map_nodes_gui.py` não gravam mais o campo `"inputs"`. Aridade default vem só do knob `inputs` do script ou da `NK_INPUTS`.
- **Bug histórico (corrigido): `Roto:0` na `NK_INPUTS` — o correto é `Roto:1`.** Conclusão anterior ("Roto dá 1 pela fórmula, correto é 0") estava invertida. Prova por paste real: Rotos desconectados ganham `inputs 0` **explícito** (Nuke só serializa o knob quando difere do default), e um Roto com bg conectado vem **sem** o knob, precedido de `push` do item que ele consome. Sintoma do bug: off-by-one na pilha inteira após o Roto — todo Merge subsequente pegava o A da fileira errada e o último ramo ficava pendurado, com "input A vem de fora do trecho colado" no primeiro Merge. Lição: aridade default errada na tabela **não gera erro, gera grafo errado e plausível** — só oráculo externo (screenshot do Node Graph real) revelou. A suspeita se confirmou e foi além: a medição v6 achou **40 divergências** na tabela (RotoPaint, Camera*/Axis*/Light*, e TODAS as entradas 2/3 — Merge2, ChannelMerge, Keymix, Copy, STMap, IBKGizmoV3… — eram na verdade 1). A tabela inteira foi reescrita com os valores medidos.
- **Aridade default É mensurável no GUI, mas pelo lado do PASTE, não do serializador** (método do `map_inputs_gui.py` v6): serializar o nó com `nodeCopy`, extrair o bloco e **remover a linha `inputs`**; montar snippet sintético com 6 Dots `inputs 0` (lastro empilhado) + o bloco; `nuke.nodePaste` e **contar os inputs conectados** do nó colado — esse número é o que o paste pop-a sem o knob, exatamente a pergunta que o `parseNK` responde. Salvaguardas obrigatórias: **self-test antes do loop** (colar `Merge2 {inputs 2}`/`Keymix {inputs 3}` e exigir medição 2/3 — valida lastro, contagem e ausência de encadeamento) e âncoras de verdade *provada* (Constant=0, Blur=1, Grade=1, Roto=1, Dot=1; **não** usar valores da própria tabela como âncora — Merge2=2 era hipótese circular e mascarou a lei por uma rodada).
- **O lastro tem que ser Dot, não Constant (lição da v5):** inputs **tipados** de classes 3D/Deep/particle (look do Camera, inputs Deep…) *rejeitam* a conexão de um Constant no paste — 94 classes mediram 0 falso. Dot é conector universal (2D, 3D, Deep, particle). O encadeamento acidental de Dots (se o `inputs 0` do lastro fosse ignorado) é descartado pelo self-test: `inputs 2` mediria 1 e a run abortaria.
- **Sondar o lado do SERIALIZADOR não é confiável nem em seleção multi-nó (lição da v3):** com decoy na seleção, as 8 âncoras falharam com o mesmo padrão da v1 (Blur=0, Merge2=1, Keymix=1, Constant=nunca-omite) — o serializador aplica regras próprias de UX/ordem de emissão (a quem ligar o `$cut_paste_input` etc.) que não controlamos nem conhecemos por completo. A dedução "multi-nó força modo exato" feita a partir do `nodes.txt` não generaliza. Motivo exato não determinado — irrelevante, pois o oráculo correto é o paste.
- **Cópia de nó ÚNICO não é oráculo (lição da v1 do script):** o Nuke especial-casa `nodeCopy` de um nó só — liga o input 0 ao `$cut_paste_input` (UX de "colar conecta na seleção") e **omite o knob `inputs` mesmo com o nó desconectado**. Resultado da v1: 396/423 classes mediram "0", âncoras todas erradas com padrão sistemático (default−1 ou invertido). Só a seleção multi-nó obriga o serializador ao modo exato de contagens de pop.
- **Script Editor roda nos globals do `__main__`, compartilhados com callbacks do pipeline (lição da v2):** `knobChanged`/`onCreate` do estúdio disparam a cada `setSelected`/`createNode` da sonda, e um callback que atribui a nomes comuns (`default`, `n`…) **sobrescreve as variáveis do script colado no meio da run** — na v2 isso pôs um objeto `Boolean_Knob` no dict de resultados (`TypeError` no `json.dump`). Regra: scripts de Script Editor fazem todo o trabalho **dentro de uma função** (locals são imunes), com tripwire de tipo antes de serializar. Os erros avulsos no console durante a sonda (scripts Python 2 do pipeline, `IndexError` em callbacks) são ruído esperado — as classes afetadas caem em `skipped`.
- `nuke.plugins()` só vê `.dll/.so/.gizmo` em disco → **perde o núcleo compilado** (Blur, Read, Dot, Roto, Expression...). Além disso, `nuke -t` (terminal) **não roda `nuke.menu()`** ("not in GUI mode") — o "menu walk" da v2 não funciona em modo terminal. Solução adotada: `map_nodes_gui.py` roda o menu walk dentro do Nuke GUI (colado no Script Editor) e escreve `nodes_menu.json`; `merge_nodes.py` mescla com o dump de plugins do terminal (`nodes.json`) → `nodes.json` final.
- PowerShell `>` grava **UTF-16 LE com BOM** e `nuke -t` imprime banner antes do JSON. O loader do artefato tolera ambos (detecta BOM, pula até a primeira `{`); v2/gui escrevem UTF-8 direto em arquivo. **Atenção:** se o script também escreve o arquivo internamente (como v2/gui fazem), não use `> nodes.json` — o redirect do PowerShell trava o arquivo e o `open()` do script falha com `PermissionError`.
- `Read` não aparece em nenhum dos dois dumps (nem núcleo nem plugins) — **causa provável identificada:** o item de menu Image>Read chama `nukescripts.create_read()` (abre o file browser), não `nuke.createNode(...)`, então o menu walk (que filtra por `"createNode"` no comando) nunca o captura. Confirmado na v6: forçando via `extra_classes = {"Read"}`, o Read mede normalmente (default 0, generator).

**Benefício do dump mesmo em v1:** validação de nomes de knobs do JSON autorado (23k nomes) → warning amarelo por knob inexistente na classe, com aliases de Expression traduzidos antes de checar.

## Geometria e fidelidade visual (paridade com o Nuke)

- Fluxo top-down; **paleta embutida re-semeada com as cores de fábrica medidas** (`map_colors_gui.py`, fidelidade 198/198 classes padrão): Merge índigo `#4b5ec6`, Filter laranja `#cc804e`, Color azul-claro `#7aa9ff`, 3D verde `#006413`, Deep azul-escuro `#000060`, Time `#b0a45d`, Channel/Copy vinho `#9e3c63`, Keyer verde-vivo `#00ff00`, Roto `#71c671`, Transform lilás `#a57aaa`, OCIO `#1caa98`, default cinza-claro `#cccccc` (Dot, Switch, Expression, Read…). A paleta antiga ('convenção') divergia do Nuke real — ex.: Merge não é laranja, laranja é Filter; Dissolve/Switch/Expression são cinza.
- **Cores reais do Nuke do usuário em runtime:** `colors_default.json` (gerado por `map_colors_gui.py`: knob `tile_color` se ≠0, senão `nuke.defaultNodeColor(classe)`, formato `0xRRGGBBAA`→`#rrggbb`, `null` = sem cor específica) carregado por upload, prioridade sobre a paleta embutida, repinta sem re-importar. O `textColorFor` (luminância) já garante legibilidade em cores claras.
- **Âncora do Nuke:** nó 80×18, Dot 12×12, canto sup. esquerdo. Conversão para desenho alinha os **centros** (nós do viewer são maiores). `pos` no JSON fica verbatim.
- **Export grava `inputs 0` explícito em nós sem conexões:** pela lei medida, bloco sem knob consome 1 (não-generators) — um nó desconectado exportado sem o knob roubaria um item da pilha no paste do usuário (bug latente revelado pela lei, corrigido junto com o suporte a Group).
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

## Geração de .nk por LLM (workstream)

Objetivo paralelo ao viewer: um system prompt que ensina um LLM a **gerar** `.nk` válido usando o catálogo medido do projeto. O viewer entra como **motor de layout + validador** do loop.

- **O catálogo completo não cabe inline.** `nodes.json` medido: 566 classes, 32.725 knobs (média 57,8/classe; máx 1059 — Roto), ~184k tokens. Decisão: o prompt carrega inline só uma **referência curada do MVP**; o catálogo completo fica no validador (o viewer já tem o `nodes.json`).
- **Subset MVP curado** (`llm/build_mvp_subset.py` → `prompts/catalog.json`): 33 classes que cobrem ~80% de comp, 179 knobs, ~2k tokens. Curadoria editorial no script, **validação programática inegociável**: classe tem que existir exata no `nodes.json`, cada knob tem que existir na classe — nome errado aborta com sugestão por proximidade (difflib). A 1ª rodada pegou 7 nomes errados meus (`datatype`/`compression` não existem no Write recém-criado — são knobs dinâmicos pós-`file_type`; Keylight usa `preBlur`/`screenClipMin/Max`; `Primatte3` não tem `operation`; Defocus chama aspect de `ratio`). Correções de nome classe≠menu: `Keylight`=`OFXuk.co.thefoundry.keylight.keylight_v201`, `Shuffle2`, `Primatte3`, `IBKGizmoV3`+`IBKColourV3`.
- **Dialeto de geração (v0):** conexões **sempre explícitas** (knob `inputs N` em todo nó, inclusive `inputs 0`; `set Nx [stack 0]` após cada nó; `push $Nx`/`push 0`) — empilhamento implícito reintroduziria a classe de bug off-by-one do Roto. O modelo **não** gera `xpos`/`ypos` (o viewer faz layout no import; o artefato final é o export do viewer). Bloco TCL único; refino = bloco substitutivo completo. Roto/RotoPaint nunca geram `curves` (irrepresentável; placeholder vazio).
- **Entrada de estado para refino:** o JSON canônico do viewer, não TCL bruto — medido: `nodes.txt` (14 nós) tem ~64k tokens por causa das curvas de Roto; o JSON canônico do mesmo setup ~1KB (60× menor). Knobs pesados elididos ⇒ nó intocável em conteúdo (reconectável/movível, não regenerável).
- **System prompt v0 escrito** (`prompts/core.md`, ~1,1k tokens + catálogo ~2k): dialeto TCL com exemplo anatômico, catálogo erro>chute, elicitação (máx 3 perguntas, só o que muda topologia; resto vira premissa declarada), formato de resposta (bloco + raciocínio 1 linha/ramo + premissas), refino via JSON canônico com "Preservar do original" para nós elididos, protocolo de correção com circuit-breaker (mesmo erro 2× → pergunta). Casos de aceitação em `prompts/acceptance.md`; montagem por modo de consumo em `prompts/README.md`; o que ficou fora da v0 (e porquê) em `llm/README.md`.

## Feedback estruturado (LLM)

Canal paralelo aos banners HTML: `parseNK` e `validate` coletam objetos `{type, node?, class?, knob?, suggestion?, valid_knobs?, detail}`; o botão **Feedback LLM** abre o drawer com o JSON do último import/render (`{ok, stage, errors, warnings}`) para o loop de correção da geração de .nk por modelo. Did-you-mean por distância de edição para classe (contra tabela embutida + JSONs carregados) e knob (contra o `nodes.json`, com `valid_knobs` completo ≤40 ou top-5, excluindo knobs de infraestrutura). Schema e lista de tipos: `llm/README.md`.

## Metodologia de teste

Harness em Node: extrai as seções do HTML por marcadores (`importação .nk`…`fim importação .nk`; seção `validação` até `layout`; `function exportNK` até `tabela`), injeta stubs/globals como parâmetros de `new Function` (`esc`, `isMergeClass`, `NK_USER`, helpers de feedback), roda asserts. **Os harnesses são efêmeros** (reconstruídos em `/tmp` por sessão) — a cobertura acumulada até aqui: regressão do bug do Roto com o fixture real `nodes.txt` (CM1/CM2/CM6 corretos, warning de externo); import completo do `nodes2.txt` (12 nós, Group opaco com 15 internos, cadeia IBK); lei da aridade (Merge sem knob = `{B}`, Switch sem knob consome 1); cadeia de prioridade de aridade com `NK_USER_INPUTS` (override do usuário, `null` fatal específico); export com NoOp placeholder e `inputs 0` explícito; fidelidade da paleta re-semeada (198/198); canal de feedback estruturado (20/20: tipos, did-you-mean classe/knob, cap de `valid_knobs`, `buildFeedback`). **Regras aprendidas:** fixtures devem imitar o formato real do Nuke (1 knob por linha; ordem de push correta) — dois bugs de fixture já ocorreram por desvio disso; e round-trip contra si mesmo não detecta convenção invertida — toda afirmação sobre o Nuke precisa de oráculo externo.

## Pendências / próximos passos possíveis

- ~~Rodar `probe_group_inputs.py` e ligar o resultado~~ **feito**: medido (controles PASS) — Group sem knob consome **1**, independente do nº de `Input`s internos (**até com zero**). A lei universal vale para Groups sem caso especial. `nodes2.txt` importa inteiro (12 nós, zero erros, Group opaco com 15 internos ocultos).

- ~~Rodar `map_inputs_gui.py` e cruzar com a `NK_INPUTS`~~ **feito (v6)**: 40 divergências corrigidas, tabela reescrita com valores medidos, lei da aridade documentada acima. `Precomp:1` é o único valor extrapolado sem medição direta (expande como Group no copy/paste) — junto com as ~44 classes de versões antigas ausentes do menu 14.0v2 (extrapoladas pela lei).
- ~~Carregar o `inputs_default.json` em runtime no viewer~~ **feito**: segundo upload ao lado do `nodes.json`. Prioridade de aridade: knob `inputs` do script → `NK_USER_INPUTS` (medido do usuário) → `NK_INPUTS` (embutida) → erro; valor `null` (medido como variável) continua erro pedindo knob explícito. O loader **valida âncoras no load** (Blur=1, Grade=1, Roto=1, Dot=1, Constant=0) e rejeita arquivos de medição quebrada — defesa contra o lixo que as v1–v3 do extractor produziam.
- ~~Subset curado do MVP para o system prompt~~ **feito**: `llm/build_mvp_subset.py` → `prompts/catalog.json` (33 classes, validadas contra o catálogo).
- ~~Canal de erro estruturado no viewer (protocolo de correção p/ LLM)~~ **feito**: botão "Feedback LLM" + ~30 tipos com did-you-mean (ver seção acima e `llm/README.md`).
- ~~Rascunhar a v0 do system prompt de geração de .nk~~ **feito**: `prompts/core.md` + `acceptance.md` (ver seção "Geração de .nk por LLM"). Próximo: rodar os 3 casos de aceitação num modelo frio e iterar o core.
- **Versionar o harness de teste em `tests/`** (hoje é efêmero, reconstruído em `/tmp` a cada sessão): consolidar num script único a cobertura listada em "Metodologia de teste" — a antiga pendência de cobrir a nova ordem de prioridade e a regressão do Roto já foi atendida nos harnesses efêmeros, falta só durabilidade. Atenção: os fixtures reais são locais (fora do git), então o harness versionado precisa pular os testes de fixture quando os arquivos não existirem.
- Usar `optionalInput` do dump para validar se `mask` declarado faz sentido por classe.
- Mapeamento de 3 inputs sem mask é especial-caso de Keymix (B/A/mask); outras classes 3+ → erro de representabilidade.
- Tabela embutida tem entradas de menor confiança no bloco 3D (ex.: Card2) — dump v2 sobrepõe (via validação de knobs/min-max).
- Sem persistência entre sessões (artefato não usa storage do navegador): nodes.json se recarrega por sessão.
