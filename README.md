# nuke-dag-viewer

Artefato HTML **autocontido** que renderiza setups de Nuke a partir de um
JSON canônico, importa/exporta o formato de clipboard `.nk` e existe para
**compreensão** (reconstrução manual no Nuke), não automação.

> Critério de sucesso: olhar o grafo e reconstruir o setup sem nenhuma
> dúvida sobre qual input vai onde.

## Uso

1. Abra `nuke-dag-viewer.html` em qualquer navegador (sem servidor, sem deps).
2. Cole um trecho `.nk` (Ctrl+C em nodes no Nuke) no campo de import — ou
   escreva o JSON canônico direto.
3. Opcional: carregue o `data/nodes.json` gerado do seu Nuke para ativar a
   validação de knobs por classe (ver `data/README.md`).

Três saídas do mesmo JSON: **grafo SVG interativo** · **snippet `.nk`**
(colável de volta no Nuke) · **tabela textual** (1 linha/nó, inputs
explícitos).

## Princípios

- **JSON canônico = fonte única de verdade.** O desenho é derivado do dado.
- **Inputs sempre nomeados** (`A`, `B`, `mask`, `input`) — sem conexões
  implícitas; Merge sem A e B é erro visível.
- **Erro > chute, sempre.** Ambiguidade real (classe desconhecida sem knob
  `inputs`, `clone`, `end_group` órfão, chaves desbalanceadas) é fatal e
  explicada; trecho parcial degrada com warnings determinísticos. Groups
  do usuário viram nós opacos (conteúdo não expandido, com aviso).
- `pos` do script Nuke é preservado **verbatim**; export re-baseado em
  (0,0) para o paste não voar para longe.

## Estrutura

```
nuke-dag-viewer.html      artefato completo (HTML+CSS+JS, zero deps)
docs/contexto.md          contexto de desenvolvimento: decisões, bugs
                          históricos, semântica de pilha do .nk, lições
extractors/               scripts que extraem metadados do SEU Nuke
  map_nodes_gui.py        núcleo compilado via menu (Script Editor, GUI)
  map_nodes_v2.py         plugins em disco (nuke -t)
  merge_nodes.py          mescla os dois dumps -> nodes.json
  map_inputs_gui.py       aridade default de serialização por classe
                          (Script Editor, GUI; autovalidação por âncoras)
data/                     dumps gerados (locais, fora do git)
tests/fixtures/           trechos .nk reais (locais, fora do git)
```

## Conhecimento crítico

A semântica de pilha do `.nk` (topo = input 0, ordem de push do Merge,
`set`/`push`, aridade default por classe) e as lições aprendidas (testes
round-trip não detectam convenção invertida; cópia de nó único não é
oráculo de serialização; aridade errada não gera erro — gera grafo
plausível e errado) estão documentadas em [`docs/contexto.md`](docs/contexto.md).

## Política de dados

Nenhum dado do estúdio é versionado: `data/` (nomes de gizmos do
pipeline) e `tests/fixtures/` (setups de produção) estão no `.gitignore`
e são regeneráveis localmente — cada pasta tem um README com o passo a
passo.
