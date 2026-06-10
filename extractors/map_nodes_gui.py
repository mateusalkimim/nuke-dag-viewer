# map_nodes_gui.py
# Uso: abra o Nuke normalmente (GUI), abra o Script Editor, cole este
# arquivo inteiro e rode (Ctrl+Enter).
#
# Faz so a parte que o modo terminal (-t) nao consegue: caminha o menu
# "Nodes" (nuke.menu requer GUI) para achar as classes do nucleo
# compilado (Blur, Read, Dot, Roto, Expression, Merge2, Grade...) que
# nao aparecem em nuke.plugins(). Para cada classe, cria o node e
# captura minInputs/maxInputs/knobs/optionalInput, igual ao
# map_nodes_v2.py. Escreve direto em arquivo (UTF-8), sem depender de
# copiar/colar a saida do Script Editor.
#
# NAO captura "inputs" (n.inputs()): de um node recem-criado e isolado
# isso reflete inputs CONECTADOS e da sempre 0 — nao serve como aridade
# default. Aridade vem do knob "inputs" do .nk ou da tabela NK_INPUTS.
import nuke, json, os

OUT = r"C:\Users\matte\Downloads\Scripts\nuke-dag-viewer\data\nodes_menu.json"  # ajuste para o seu ambiente

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

res = {}
skipped = []
for cls in sorted(classes):
    try:
        n = nuke.createNode(cls, inpanel=False)
        entry = {
            "minInputs": n.minInputs(),
            "maxInputs": n.maxInputs(),
            "knobs": list(n.knobs().keys()),
        }
        try:
            entry["optionalInput"] = n.optionalInput()
        except Exception:
            pass
        res[n.Class()] = entry
        nuke.delete(n)
    except Exception as e:
        skipped.append("%s: %s" % (cls, e))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, sort_keys=True)

print("ok: %d classes -> %s" % (len(res), OUT))
if skipped:
    print("skipped %d:" % len(skipped))
    for s in skipped:
        print("  " + s)
