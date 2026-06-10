# tests/fixtures/ — trechos .nk reais (locais, fora do git)

Fixtures copiados do clipboard do Nuke em produção — ficam fora do
versionamento porque contêm setups/rotos do estúdio.

| Arquivo | Cobre |
|---|---|
| `nodes.txt` | Regressão do bug do Roto (aridade default 1): `push $cut_paste_input` consumido por Roto **sem** knob `inputs`, três Rotos desconectados com `inputs 0` explícito, cadeia de ChannelMerges. Resultado esperado: CM1 A=Blur5, CM2 A=Blur4, CM6 A=Defocus3, zero erros, warning de input externo no BaseTela. |
| `nodes2.txt` | Group do usuário sem knob `inputs` (com grupos aninhados e `set/push` de variáveis pós-`end_group`). Resultado esperado: **import completo** — 12 nós, zero erros; `AdaptiveDenoise1` vira nó opaco (15 internos ocultos) consumindo `Denoise1` e alimentando `IBKColourV3_1`/`IBKGizmoV3_1` (B=Group, A=IBKColour); warnings de input externo no Stamp2 e de Group opaco. |

Para reproduzir: abrir `nuke-dag-viewer.html`, colar o conteúdo do
fixture no campo de import `.nk`. A metodologia de harness (extração do
parser por marcadores + Node) está em `docs/contexto.md`.
