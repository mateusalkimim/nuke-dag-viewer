# probe_group_inputs.py
# Uso: abra o Nuke (GUI), Script Editor, cole este arquivo e rode.
#
# Diagnostico pontual: mede a ARIDADE DEFAULT de um bloco "Group" sem o
# knob "inputs" — quantos itens da pilha o paste consome. A lei medida
# pelo map_inputs_gui.py v6 (sem knob = 0 para generators, 1 para o
# resto) NAO cobre Groups: eles sao pulados la (expandem como
# Group/end_group no copy). A duvida especifica: o default de um Group
# depende do numero de nos Input internos, ou e' fixo (1) como nas
# classes normais?
#
# Metodo (mesma infra do v6): cola 6 Dots "inputs 0" de lastro + um
# Group SINTETICO (com 0/1/2 nos Input no corpo, com e sem knob) e conta
# os inputs conectados do Group colado. Controles com knob explicito
# validam lastro e contagem.
#
# Nao escreve arquivo — so imprime a tabela de resultados. Me traga a
# saida do console.
import nuke, os, tempfile


def _nkprobe_group_main():
    TMP = os.path.join(tempfile.gettempdir(), "nk_probe_group.nk")
    N_BALLAST = 6

    def deselect_all():
        for s in nuke.selectedNodes():
            s.setSelected(False)

    def group_text(name, n_inputs, knob):
        """Group sintetico no formato real de serializacao (filhos
        indentados 1 espaco, knobs dos filhos 2 espacos)."""
        L = ["Group {"]
        if knob is not None:
            L.append(" inputs %d" % knob)
        L.append(" name %s" % name)
        L.append("}")
        for i in range(n_inputs):
            L.append(" Input {")
            L.append("  inputs 0")
            L.append("  name Input%d" % (i + 1))
            L.append(" }")
        L.append(" Output {")
        L.append("  name Output1")
        L.append(" }")
        L.append("end_group")
        return L

    def paste_and_count(block_lines, probe_name):
        snippet = []
        for j in range(N_BALLAST):
            snippet.append("Dot {")
            snippet.append(" inputs 0")
            snippet.append(" name NKPROBE_C%d" % j)
            snippet.append("}")
        snippet.extend(block_lines)
        with open(TMP, "w", encoding="utf-8") as f:
            f.write("\n".join(snippet) + "\n")
        deselect_all()
        pasted = []
        try:
            nuke.nodePaste(TMP)
            pasted = list(nuke.selectedNodes())
            target = nuke.toNode(probe_name)
            if target is None:
                return "<no nao achado>"
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

    cases = [
        # (rotulo, n_Inputs_internos, knob_inputs, esperado-se-controle)
        ("controle: 1 Input, knob 'inputs 1'", 1, 1, 1),
        ("controle: 0 Input, knob 'inputs 0'", 0, 0, 0),
        ("MEDICAO: 0 Input, SEM knob       ", 0, None, None),
        ("MEDICAO: 1 Input, SEM knob       ", 1, None, None),
        ("MEDICAO: 2 Input, SEM knob       ", 2, None, None),
    ]
    print("aridade default de Group (paste sem knob 'inputs'):")
    ok = True
    for i, (label, n_in, knob, expect) in enumerate(cases):
        got = paste_and_count(group_text("NKPROBE_G%d" % i, n_in, knob),
                              "NKPROBE_G%d" % i)
        verdict = ""
        if expect is not None:
            verdict = "PASS" if got == expect else "FAIL (esperado %d)" % expect
            if got != expect:
                ok = False
        print("  %s -> consumiu %s  %s" % (label, got, verdict))
    if not ok:
        print("ATENCAO: controle FALHOU — nao use as medicoes acima.")
    else:
        print("controles OK — medicoes confiaveis.")


_nkprobe_group_main()
