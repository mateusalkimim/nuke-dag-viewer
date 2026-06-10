# data/ — dumps do Nuke (locais, fora do git)

Os JSONs desta pasta são gerados a partir do **seu** Nuke e ficam fora do
versionamento (contêm nomes de gizmos do pipeline do estúdio).

| Arquivo | Gerado por | Como |
|---|---|---|
| `nodes_menu.json` | `extractors/map_nodes_gui.py` | colar no Script Editor do Nuke GUI e rodar |
| `nodes.json` | `extractors/map_nodes_v2.py` + `merge_nodes.py` | `nuke -t map_nodes_v2.py` e depois `python merge_nodes.py nodes_menu.json nodes.json` |
| `inputs_default.json` | `extractors/map_inputs_gui.py` | colar no Script Editor do Nuke GUI e rodar; só usar se o console terminar com `anchors OK` |
| `colors_default.json` | `extractors/map_colors_gui.py` | colar no Script Editor do Nuke GUI e rodar; cores de tile por classe (inclui suas preferências) |

O viewer (`nuke-dag-viewer.html`) carrega dois arquivos em runtime, cada
um pelo seu botão de upload:

- `nodes.json` — validação de nomes de knobs e mensagens de erro com
  min–max por classe;
- `inputs_default.json` — aridade default **medida** do seu Nuke, com
  prioridade sobre a tabela embutida; cobre gizmos não-Group do pipeline
  (ex.: `ABME_*` medem 0). O loader valida âncoras (Blur=1, Grade=1,
  Roto=1, Dot=1, Constant=0) e **rejeita** arquivos de medição quebrada;
- `colors_default.json` — cor de tile por classe (knob `tile_color` ou
  `nuke.defaultNodeColor`), com prioridade sobre a paleta embutida — os
  nós ficam com as mesmas cores do seu Node Graph. Repinta na hora, sem
  re-importar.

⚠️ Não use redirect `>` do PowerShell para gravar estes arquivos: os
scripts escrevem direto em arquivo (UTF-8) e o redirect trava o arquivo,
causando `PermissionError` (detalhes em `docs/contexto.md`).
