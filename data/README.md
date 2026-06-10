# data/ — dumps do Nuke (locais, fora do git)

Os JSONs desta pasta são gerados a partir do **seu** Nuke e ficam fora do
versionamento (contêm nomes de gizmos do pipeline do estúdio).

| Arquivo | Gerado por | Como |
|---|---|---|
| `nodes_menu.json` | `extractors/map_nodes_gui.py` | colar no Script Editor do Nuke GUI e rodar |
| `nodes.json` | `extractors/map_nodes_v2.py` + `merge_nodes.py` | `nuke -t map_nodes_v2.py` e depois `python merge_nodes.py nodes_menu.json nodes.json` |
| `inputs_default.json` | `extractors/map_inputs_gui.py` | colar no Script Editor do Nuke GUI e rodar; só usar se o console terminar com `anchors OK` |

O viewer (`nuke-dag-viewer.html`) carrega o `nodes.json` em runtime pelo
botão de upload — validação de nomes de knobs e mensagens de erro com
min–max por classe.

⚠️ Não use redirect `>` do PowerShell para gravar estes arquivos: os
scripts escrevem direto em arquivo (UTF-8) e o redirect trava o arquivo,
causando `PermissionError` (detalhes em `docs/contexto.md`).
