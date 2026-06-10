# map_inputs_gui.py (v4)
# Uso: abra o Nuke normalmente (GUI), abra o Script Editor, cole este
# arquivo inteiro e rode (Ctrl+Enter).
#
# Mede a ARIDADE DEFAULT por classe: quantos itens da pilha o PASTE do
# Nuke consome quando o bloco .nk NAO traz o knob "inputs". E' exatamente
# a pergunta que o parser do viewer (parseNK) precisa responder.
#
# LICAO DA v1: copiar um NODE SOZINHO nao e' oraculo — o Nuke
# especial-casa a copia de no unico (liga o input 0 ao $cut_paste_input
# e omite o knob mesmo desconectado).
#
# LICAO DA v2: o codigo colado no Script Editor roda nos globals do
# __main__, compartilhados com callbacks do pipeline; um callback que
# atribui a nomes comuns sobrescreve variaveis do script no meio da run.
# Por isso todo o trabalho vive dentro de uma funcao (locals sao imunes).
#
# LICAO DA v3: sondar o lado do SERIALIZADOR (quando o nodeCopy escreve
# ou omite o knob) e' nao-confiavel mesmo em selecao multi-no — o
# serializador aplica regras de UX/ordem de emissao proprias (as 8
# ancoras falharam com o mesmo padrao da v1 mesmo com decoy na selecao).
# O oraculo correto e' o lado do PASTE: construir um snippet sintetico
# com lastro de Dots na pilha + o bloco da classe SEM o knob "inputs",
# colar com nuke.nodePaste e CONTAR quantos Dots o no consumiu. O paste
# e' deterministico e e' a semantica que o parser imita.
#
# Metodo v4, por classe:
#   1. cria o node, serializa so ele (nodeCopy), extrai o bloco e REMOVE
#      as linhas " inputs N" de nivel superior; deleta o node.
#   2. monta snippet: 6 Dots com "inputs 0" (ficam empilhados) + bloco.
#   3. deseleciona tudo, nuke.nodePaste(snippet).
#   4. aridade default = numero de inputs conectados do no colado.
#   5. deleta os nos colados.
#
# Saida: inputs_default.json  {classe: default}
#   - null = consumiu o lastro inteiro (>= 6) — aridade variavel/enorme;
#     a NK_INPUTS exclui essas classes de proposito.
# No final roda autovalidacao com classes de verdade conhecida (anchors)
# e imprime PASS/FAIL — se falhar, o metodo quebrou de novo: nao use o
# JSON.
import nuke, json, os, re, tempfile


def _nkprobe_main():
    OUT = r"C:\Users\matte\Downloads\Scripts\nuke-dag-viewer\data\inputs_default.json"  # ajuste para o seu ambiente
    TMP_COPY = os.path.join(tempfile.gettempdir(), "nk_probe_copy.nk")
    TMP_PASTE = os.path.join(tempfile.gettempdir(), "nk_probe_paste.nk")
    N_DOTS = 6  # lastro; maior default conhecido e' 3 (Keymix, IBKGizmoV3)

    # Menu Image>Read usa nukescripts.create_read() (sem "createNode" no
    # comando), por isso Read nunca apareceu nos dumps de menu.
    extra_classes = {"Read"}

    # verdade conhecida (paste real / uso diario) para autovalidar o
    # metodo. Switch ficou de fora: e' classe de aridade variavel e seu
    # comportamento de paste sem knob e' justamente o que vamos MEDIR.
    anchors = {"Constant": 0, "Blur": 1, "Grade": 1, "Merge2": 2,
               "ChannelMerge": 2, "Keymix": 3, "Roto": 1}

    inputs_re = re.compile(r"^ inputs (\d+)$")
    name_re = re.compile(r"^ name (\S+)$")
    hdr_re = re.compile(r"^[A-Za-z_][\w.]* \{")

    classes = set()

    def visit(menu):
        for it in menu.items():
            if isinstance(it, nuke.Menu):
                visit(it)
                continue
            try:
                cmd = it.script() or ""
            except RuntimeError:
                continue
            if "createNode" not in cmd:
                continue
            for q in ('"', "'"):
                if q in cmd:
                    try:
                        classes.add(cmd.split(q)[1])
                    except IndexError:
                        pass
                    break

    visit(nuke.menu("Nodes"))
    classes |= extra_classes

    def deselect_all():
        for s in nuke.selectedNodes():
            s.setSelected(False)

    def extract_block_sans_inputs(path, probe_name):
        """Devolve as linhas do bloco cujo knob name == probe_name, com
        as linhas ' inputs N' de nivel superior removidas; None se o
        bloco nao for achado."""
        in_block = False
        depth = 0
        cur = []
        cur_is_target = False
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\r\n")
                if not in_block:
                    if hdr_re.match(line):
                        in_block = True
                        depth = line.count("{") - line.count("}")
                        cur = [line]
                        cur_is_target = False
                    continue
                drop = False
                if depth == 1:  # knobs de nivel superior do bloco
                    if inputs_re.match(line):
                        drop = True
                    m = name_re.match(line)
                    if m and m.group(1) == probe_name:
                        cur_is_target = True
                if not drop:
                    cur.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    in_block = False
                    if cur_is_target:
                        return cur
        return None

    res = {}
    skipped = []
    for cls in sorted(classes):
        # --- passo 1: bloco serializado da classe, sem o knob inputs ---
        deselect_all()  # evita auto-conexao do createNode com a selecao
        try:
            n = nuke.createNode(cls, inpanel=False)
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
            continue
        block = None
        real_cls = cls
        try:
            try:
                n.setName("NKPROBE_TARGET")
            except Exception:
                pass
            probe_name = n.name()  # nome real (rename pode colidir/falhar)
            real_cls = n.Class()
            for i in range(n.inputs()):
                n.setInput(i, None)
            deselect_all()
            n.setSelected(True)
            if os.path.exists(TMP_COPY):
                os.remove(TMP_COPY)
            nuke.nodeCopy(TMP_COPY)
            block = extract_block_sans_inputs(TMP_COPY, probe_name)
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
        finally:
            try:
                nuke.delete(n)
            except Exception:
                pass
        if block is None:
            if not any(s.startswith(cls + ":") for s in skipped):
                skipped.append("%s: bloco nao achado na serializacao" % cls)
            continue

        # --- passo 2: snippet com lastro de Dots + bloco sem knob ---
        snippet = []
        for j in range(N_DOTS):
            snippet.append("Dot {")
            snippet.append(" inputs 0")
            snippet.append(" name NKPROBE_D%d" % j)
            snippet.append("}")
        snippet.extend(block)
        with open(TMP_PASTE, "w", encoding="utf-8") as f:
            f.write("\n".join(snippet) + "\n")

        # --- passos 3-5: paste, contagem dos inputs, limpeza ---
        deselect_all()
        pasted = []
        try:
            nuke.nodePaste(TMP_PASTE)
            pasted = list(nuke.selectedNodes())
            target = nuke.toNode(probe_name)
            if target is None:
                raise RuntimeError("no colado nao achado pelo nome")
            connected = 0
            for i in range(N_DOTS + 2):
                try:
                    if target.input(i) is not None:
                        connected += 1
                except Exception:
                    break
            res[real_cls] = None if connected >= N_DOTS else connected
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
        finally:
            seen = set()
            for p in pasted + [nuke.toNode(probe_name)]:
                if p is None or id(p) in seen:
                    continue
                seen.add(id(p))
                try:
                    nuke.delete(p)
                except Exception:
                    pass

    # tripwire contra poluicao de estado (a v2 caiu exatamente nisso):
    # todo valor precisa ser int ou None ANTES de tentar escrever
    bad = {c: type(v).__name__ for c, v in res.items()
           if not (v is None or isinstance(v, int))}
    if bad:
        raise RuntimeError("valores de tipo inesperado em res: %r" % bad)

    # escrita atomica: nunca deixa um OUT truncado para tras
    tmp_out = OUT + ".tmp"
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    os.replace(tmp_out, OUT)

    # verificacao pos-escrita: rele o arquivo final e confere a contagem
    with open(OUT, encoding="utf-8") as f:
        check = json.load(f)
    if len(check) != len(res):
        raise RuntimeError("verificacao falhou: %d classes no arquivo, %d medidas"
                           % (len(check), len(res)))

    fixed = sum(1 for v in res.values() if v is not None)
    var = sum(1 for v in res.values() if v is None)
    print("ok: %d classes, %d bytes -> %s"
          % (len(res), os.path.getsize(OUT), OUT))
    print("  default fixo: %d | variavel/lastro esgotado (null): %d" % (fixed, var))

    fails = 0
    for cls, exp in sorted(anchors.items()):
        got = res.get(cls, "<ausente>")
        status = "PASS" if got == exp else "FAIL"
        if status == "FAIL":
            fails += 1
        print("  anchor %-12s esperado=%-4s medido=%-4s %s"
              % (cls, exp, got, status))
    if fails:
        print("ATENCAO: %d anchor(s) FAIL — metodo invalido, NAO use o JSON." % fails)
    else:
        print("anchors OK — JSON confiavel.")

    if skipped:
        print("skipped %d:" % len(skipped))
        for s in skipped:
            print("  " + s)


_nkprobe_main()
