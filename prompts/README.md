# prompts/ — system prompt de geração de .nk

Fonte única, três modos de consumo. O conteúdo dos arquivos não depende
do modo — montar é só concatenar/anexar.

| Arquivo | Papel |
|---|---|
| `core.md` | regras: dialeto TCL, catálogo erro>chute, elicitação, refino, correção (~1,1k tokens) |
| `catalog.json` | as 33 classes/knobs permitidos (~2k tokens) — gerado por `llm/build_mvp_subset.py`, **não editar à mão** |
| `acceptance.md` | 3 casos de teste com comportamento esperado |

## Montagem por modo

- **(a) System prompt de chat dedicado:** `core.md` + uma linha
  "Catálogo (catalog.json):" + o conteúdo do JSON, tudo no system
  prompt. Total ~3,2k tokens.
- **(b) Skill/preset carregável:** `core.md` como corpo da skill;
  `catalog.json` como arquivo da skill (referenciado pelo nome, como o
  core já faz).
- **(c) Anexo manual em serviço online:** anexar os dois arquivos e
  abrir com "Siga core.md; o catálogo é catalog.json". Funciona a frio —
  o core não referencia nada externo aos dois arquivos.

O loop completo: usuário pede → modelo (elicita ou) gera bloco TCL →
cola no `nuke-dag-viewer.html` → botão **Feedback LLM** → cola o JSON de
volta no modelo → bloco corrigido → quando `{ok: true}`, o **export do
viewer** (com layout/posições) é o artefato final para colar no Nuke.
