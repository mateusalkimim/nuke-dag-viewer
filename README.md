# nuke-dag-viewer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Nuke](https://img.shields.io/badge/Nuke-14.0v2-orange.svg)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

Um único arquivo HTML, sem dependências e sem servidor, que renderiza setups de
Nuke a partir de um JSON canônico e importa/exporta o formato de clipboard
`.nk`. Feito para **compreensão** — reconstruir um setup manualmente no Nuke —
e não para automação.

> **Critério de sucesso:** olhar o grafo e reconstruir o setup sem nenhuma
> dúvida sobre qual input vai onde.

> *A self-contained, dependency-free HTML viewer for Nuke node graphs. Paste a
> `.nk` clipboard snippet (or write canonical JSON) and get an interactive SVG
> graph, a pasteable `.nk` export, and an explicit-inputs text table. Built for
> faithful manual reconstruction, with node arity, positions and colors
> **measured from a real Nuke**, not assumed.*

---

## Por que existe

Ler um `.nk` "no olho" é traiçoeiro: o formato é uma máquina de pilha e a
ligação de inputs fica implícita na ordem de `push`. Uma única classe com
aridade default errada desloca a pilha inteira e produz **um grafo plausível,
porém errado** — sem nenhum erro visível. Este projeto trata isso com um lema:
**erro > chute, sempre**. Onde a topologia é ambígua de verdade, o viewer
recusa e explica; onde é determinável, ele acerta — porque os valores (aridade,
posição, cor) foram **medidos no Nuke real**, não deduzidos.

## Uso

1. Abra `nuke-dag-viewer.html` em qualquer navegador (sem build, sem deps).
2. Cole um trecho `.nk` (Ctrl+C em nós no Nuke) no campo de import — ou escreva
   o JSON canônico direto.
3. *Opcional:* carregue os JSONs gerados do **seu** Nuke (veja
   [Fidelidade](#fidelidade-ao-seu-nuke)) para validação de knobs, aridade e
   cores idênticas ao seu Node Graph.

Três saídas do mesmo JSON, mais uma entrada:

| | |
|---|---|
| **Grafo SVG interativo** | zoom no cursor, pan, `F` = enquadrar |
| **Snippet `.nk`** | colável de volta no Nuke |
| **Tabela textual** | 1 linha por nó, inputs explícitos |
| **Import `.nk`** ⟶ | parser de semântica de pilha → JSON → render |

## Princípios

- **JSON canônico = fonte única de verdade.** O desenho é derivado do dado.
- **Inputs sempre nomeados** (`A`, `B`, `mask`, `input`) — sem conexões
  implícitas; Merge sem A e B é erro visível.
- **Erro > chute, sempre.** Ambiguidade real (classe desconhecida sem knob
  `inputs`, `clone`, `end_group` órfão, chaves desbalanceadas) é fatal e
  explicada; trecho parcial degrada com warnings determinísticos. Groups do
  usuário viram nós opacos (conteúdo não expandido, com aviso).
- `pos` do script Nuke é preservado **verbatim**; export re-baseado em (0,0)
  para o paste não voar para longe no DAG do usuário.

## Fidelidade ao seu Nuke

O viewer já vem com defaults embutidos (aridade e cores medidas no Nuke 14.0v2),
então funciona "de fábrica". Para uma réplica exata do **seu** Nuke — incluindo
gizmos do pipeline e suas preferências de cor — gere três JSONs com os scripts
em [`extractors/`](extractors/) e carregue-os pelos uploads na barra lateral:

| Arquivo | Script | O que cobre |
|---|---|---|
| `nodes.json` | `map_nodes_gui.py` + `map_nodes_v2.py` + `merge_nodes.py` | catálogo de classes/knobs → valida nomes de knob |
| `inputs_default.json` | `map_inputs_gui.py` | aridade default medida → cobre gizmos do pipeline |
| `colors_default.json` | `map_colors_gui.py` | cor de tile por classe → nós com a cor do seu Node Graph |

Cada extractor roda colado no **Script Editor do Nuke (GUI)** e tem
autovalidação embutida (âncoras de verdade conhecida com PASS/FAIL) — um arquivo
gerado por uma medição quebrada é rejeitado no carregamento. Detalhes do método
(e por que medir é a única via confiável) em [`docs/contexto.md`](docs/contexto.md).

## Estrutura

```
nuke-dag-viewer.html      artefato completo (HTML+CSS+JS, zero deps)
docs/contexto.md          contexto de desenvolvimento: decisões, bugs,
                          semântica de pilha do .nk, lições aprendidas
extractors/               scripts que extraem metadados do SEU Nuke
  map_nodes_gui.py          núcleo compilado via menu (Script Editor, GUI)
  map_nodes_v2.py           plugins em disco (nuke -t)
  merge_nodes.py            mescla os dois dumps -> nodes.json
  map_inputs_gui.py         aridade default por classe (paste-oráculo)
  map_colors_gui.py         cor de tile por classe
  probe_group_inputs.py     diagnóstico pontual da aridade de Group
llm/                      geração de .nk por LLM
  build_mvp_subset.py       subset curado validado contra o catálogo
  mvp_subset.json           33 classes / ~2k tokens, inline em prompt
data/                     dumps gerados (locais, fora do git)
tests/fixtures/           trechos .nk reais (locais, fora do git)
```

## Conhecimento crítico

A semântica de pilha do `.nk` (topo = input 0, ordem de push do Merge,
`set`/`push`) e a **lei da aridade default** — bloco sem knob `inputs` consome
0 (generators) ou 1 (todo o resto), nunca 2+ — foram **medidas**, não
assumidas. As lições que levaram até elas (testes round-trip não detectam
convenção invertida; cópia de nó único não é oráculo de serialização; aridade
errada não gera erro, gera grafo plausível e errado) estão documentadas em
[`docs/contexto.md`](docs/contexto.md). É tanto referência técnica quanto um
diário de "como saber se isto é verdade ou artefato".

## Compatibilidade

Desenvolvido e medido contra **Nuke 14.0v2**. A lei da aridade e a semântica de
pilha são estáveis entre versões; classes novas/removidas e cores específicas de
outra versão são absorvidas carregando os JSONs gerados do seu próprio Nuke.

## Política de dados

Nenhum dado de produção é versionado: `data/` (nomes de gizmos do pipeline) e
`tests/fixtures/` (setups de produção) estão no `.gitignore` e são regeneráveis
localmente — cada pasta tem um README com o passo a passo.

## Contribuindo

Issues e PRs são bem-vindos. Para mudanças no parser/exportador, rode o harness
de teste descrito em [`docs/contexto.md`](docs/contexto.md) (§ Metodologia de
teste) e mantenha a cobertura das regressões. A regra de ouro do projeto:
fixtures devem imitar o formato real do Nuke, e qualquer afirmação sobre o
comportamento do Nuke precisa de um **oráculo externo** (paste real), não de
dedução.

## Licença

[MIT](LICENSE) © 2026 Mateus Alkimim.

Este é um projeto independente, sem afiliação com a Foundry. "Nuke" é marca
registrada da The Foundry Visionmongers Ltd.
