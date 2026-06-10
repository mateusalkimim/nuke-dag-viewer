# map_inputs_gui.py (v5)
# Uso: abra o Nuke normalmente (GUI), abra o Script Editor, cole este
# arquivo inteiro e rode (Ctrl+Enter).
#
# Mede a ARIDADE DEFAULT por classe: quantos itens da pilha o PASTE do
# Nuke consome quando o bloco .nk NAO traz o knob "inputs". E' exatamente
# a pergunta que o parser do viewer (parseNK) precisa responder.
#
# LICOES ACUMULADAS (detalhes em docs/contexto.md):
#  v1: copia de no unico nao e' oraculo (UX do $cut_paste_input).
#  v2: Script Editor roda nos globals do __main__, compartilhados com
#      callbacks do pipeline -> todo o trabalho vive numa funcao.
#  v3: o lado do SERIALIZADOR (quando o nodeCopy omite o knob) nao e'
#      confiavel nem em selecao multi-no -> medimos o lado do PASTE.
#  v4: a medicao deu {0,1} para todas as 423 classes — compativel com
#      DOIS modelos: (A) default universal <=1, real; (B) artefato — se
#      o paste ignorou o "inputs 0" dos Dots de lastro, eles se
#      encadearam e a pilha tinha 1 item so, capando tudo em 1.
#
# A v5 DISCRIMINA os dois modelos:
#  - lastro de Constant (maxInputs=0: incapaz de encadear, com ou sem
#    knob) no lugar de Dot;
#  - SELF-TEST antes do loop: cola "Merge2 {inputs 2}" e
#    "Keymix {inputs 3}" sinteticos e exige medicao 2 e 3 — prova que o
#    lastro fornece multiplos itens e que a contagem funciona. Se
#    falhar, aborta sem escrever nada.
#
# Metodo, por classe:
#   1. cria o node, serializa so ele (nodeCopy), extrai o bloco e REMOVE
#      as linhas " inputs N" de nivel superior; deleta o node. Se a
#      copia contem "end_group", a classe e' um gizmo que expande como
#      Group -> fora do escopo da tabela, pula.
#   2. cola (nodePaste) 6 Constants de lastro + o bloco sem knob.
#   3. aridade default = numero de inputs conectados do no colado.
#   4. deleta os nos colados.
#
# Saida: inputs_default.json  {classe: default}
#   - null = consumiu o lastro inteiro (>= 6).
# Ancoras de verdade conhecida (provadas por paste real/cadeia linear):
# Constant=0, Blur=1, Grade=1, Roto=1, Dot=1. Merge2/ChannelMerge/
# Keymix/Switch sao impressos como INFORMATIVOS — o valor da tabela
# antiga (2/3) era hipotese, nao verdade medida.
import nuke, json, os, re, tempfile


def _nkprobe_main():
    OUT = r"C:\Users\matte\Downloads\Scripts\nuke-dag-viewer\data\inputs_default.json"  # ajuste para o seu ambiente
    TMP_COPY = os.path.join(tempfile.gettempdir(), "nk_probe_copy.nk")
    TMP_PASTE = os.path.join(tempfile.gettempdir(), "nk_probe_paste.nk")
    N_BALLAST = 6  # lastro; maior default hipotetico conhecido e' 3

    # Menu Image>Read usa nukescripts.create_read() (sem "createNode" no
    # comando), por isso Read nunca apareceu nos dumps de menu.
    extra_classes = {"Read"}

    # verdade conhecida (paste real / cadeia linear) para autovalidar
    anchors = {"Constant": 0, "Blur": 1, "Grade": 1, "Roto": 1, "Dot": 1}
    # hipoteses da tabela antiga — so informativo, nao gate
    informative = ["Merge2", "ChannelMerge", "Keymix", "Copy", "Switch",
                   "Camera3", "RotoPaint", "Precomp"]

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
        """Devolve (linhas do bloco com ' inputs N' removido, eh_group).
        Bloco identificado pelo knob name == probe_name."""
        in_block = False
        depth = 0
        cur = []
        cur_is_target = False
        target_block = None
        has_end_group = False
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\r\n")
                if line.strip() == "end_group":
                    has_end_group = True
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
                    if cur_is_target and target_block is None:
                        target_block = cur
        return target_block, has_end_group

    def paste_and_count(block_lines, probe_name):
        """Cola lastro de Constants + bloco; devolve o numero de inputs
        conectados do no colado. Limpa tudo que colou."""
        snippet = []
        for j in range(N_BALLAST):
            snippet.append("Constant {")
            snippet.append(" name NKPROBE_C%d" % j)
            snippet.append("}")
        snippet.extend(block_lines)
        with open(TMP_PASTE, "w", encoding="utf-8") as f:
            f.write("\n".join(snippet) + "\n")
        deselect_all()
        pasted = []
        try:
            nuke.nodePaste(TMP_PASTE)
            pasted = list(nuke.selectedNodes())
            target = nuke.toNode(probe_name)
            if target is None:
                raise RuntimeError("no colado nao achado pelo nome")
            connected = 0
            for i in range(N_BALLAST + 2):
                try:
                    if target.input(i) is not None:
                        connected += 1
                except Exception:
                    break
            return connected
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

    # --- SELF-TEST do lastro: knob explicito tem que medir exato ------
    st2 = paste_and_count(
        ["Merge2 {", " inputs 2", " name NKPROBE_ST2", "}"], "NKPROBE_ST2")
    st3 = paste_and_count(
        ["Keymix {", " inputs 3", " name NKPROBE_ST3", "}"], "NKPROBE_ST3")
    if st2 != 2 or st3 != 3:
        raise RuntimeError(
            "SELF-TEST do lastro falhou: 'inputs 2'->%s, 'inputs 3'->%s "
            "(esperado 2 e 3). Lastro/contagem invalidos — nada foi "
            "escrito." % (st2, st3))
    print("self-test do lastro: inputs2->2, inputs3->3 OK")

    res = {}
    skipped = []
    groups = []
    for cls in sorted(classes):
        deselect_all()  # evita auto-conexao do createNode com a selecao
        try:
            n = nuke.createNode(cls, inpanel=False)
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
            continue
        block = None
        is_group = False
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
            block, is_group = extract_block_sans_inputs(TMP_COPY, probe_name)
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
        finally:
            try:
                nuke.delete(n)
            except Exception:
                pass
        if is_group:
            groups.append(cls)  # gizmo que expande como Group: fora do escopo
            continue
        if block is None:
            if not any(s.startswith(cls + ":") for s in skipped):
                skipped.append("%s: bloco nao achado na serializacao" % cls)
            continue
        try:
            connected = paste_and_count(block, probe_name)
            res[real_cls] = None if connected >= N_BALLAST else connected
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))

    # tripwire contra poluicao de estado (a v2 caiu exatamente nisso)
    bad = {c: type(v).__name__ for c, v in res.items()
           if not (v is None or isinstance(v, int))}
    if bad:
        raise RuntimeError("valores de tipo inesperado em res: %r" % bad)

    # escrita atomica: nunca deixa um OUT truncado para tras
    tmp_out = OUT + ".tmp"
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    os.replace(tmp_out, OUT)

    # verificacao pos-escrita
    with open(OUT, encoding="utf-8") as f:
        check = json.load(f)
    if len(check) != len(res):
        raise RuntimeError("verificacao falhou: %d classes no arquivo, %d medidas"
                           % (len(check), len(res)))

    hist = {}
    for v in res.values():
        hist[str(v)] = hist.get(str(v), 0) + 1
    print("ok: %d classes, %d bytes -> %s"
          % (len(res), os.path.getsize(OUT), OUT))
    print("  distribuicao dos defaults medidos: %s" % hist)

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

    for cls in informative:
        if cls in res:
            print("  info   %-12s medido=%s" % (cls, res[cls]))

    if groups:
        print("fora do escopo (expandem como Group no copy/paste): %d" % len(groups))
    if skipped:
        print("skipped %d:" % len(skipped))
        for s in skipped:
            print("  " + s)


_nkprobe_main()
