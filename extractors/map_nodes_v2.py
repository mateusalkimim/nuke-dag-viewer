# map_nodes_v2.py
# Uso:  & "...\Nuke14.0.exe" -t map_nodes_v2.py [saida.json]
# Escreve UTF-8 direto em arquivo (evita o UTF-16 + banner do PowerShell '>').
#
# Diferenças da v1:
#  - UNIAO de duas fontes: menu Nodes (pega o nucleo compilado no executavel:
#    Blur, Read, Dot, Roto, Expression... ausentes na enumeracao de plugins)
#    + nuke.plugins() incluindo .gizmo (pega os gizmos do pipeline do estudio).
#  - Campo "optionalInput": indice do input opcional (a mask), quando a API
#    expoe.
#
# NAO ha campo "inputs" (aridade default de serializacao): n.inputs() de um
# node recem-criado e isolado reflete inputs CONECTADOS, e da sempre 0,
# para qualquer classe. Nao e' uma medida de aridade. A aridade default vem
# do knob "inputs" do proprio script .nk ou da tabela embutida NK_INPUTS no
# HTML (minInputs/maxInputs tambem nao servem: contam inputs opcionais/mask,
# entao Grade tem minInputs 2 mas serializa 1).
import nuke, json, sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "nodes.json")

classes = set()

# fonte 1: menu Nodes (nucleo + tudo que esta registrado na UI)
def visit(menu):
    for it in menu.items():
        if isinstance(it, nuke.Menu):
            visit(it)
            continue
        cmd = it.script() or ""
        if "createNode" not in cmd:
            continue
        for q in ('"', "'"):
            if q in cmd:
                try:
                    classes.add(cmd.split(q)[1])
                except IndexError:
                    pass
                break

try:
    visit(nuke.menu("Nodes"))
except Exception as e:
    sys.stderr.write("menu walk falhou: %s\n" % e)

# fonte 2: plugins em disco (inclui gizmos do pipeline)
for p in nuke.plugins(nuke.ALL | nuke.NODIR):
    name, ext = os.path.splitext(p)
    if ext.lower() in (".dll", ".so", ".dylib", ".gizmo"):
        classes.add(name)

res = {}
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
        sys.stderr.write("skip %s: %s\n" % (cls, e))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, sort_keys=True)
sys.stderr.write("ok: %d classes -> %s\n" % (len(res), OUT))
