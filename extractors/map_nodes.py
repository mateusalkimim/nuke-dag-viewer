# map_nodes.py  ->  rode com:  nuke -t map_nodes.py > nodes.json
import nuke, json, sys

res, seen = {}, set()

def visit(menu):
    for it in menu.items():
        if isinstance(it, nuke.Menu):
            visit(it)
            continue
        try:
            cmd = it.script() or ''
        except RuntimeError:
            continue  # separador / item sem comando
        if 'createNode' not in cmd:
            continue
        try:
            cls = cmd.split('"')[1]
        except IndexError:
            continue
        if cls in seen:
            continue
        seen.add(cls)
        try:
            n = nuke.createNode(cls, inpanel=False)
            res[n.Class()] = {
                "minInputs": n.minInputs(),
                "maxInputs": n.maxInputs(),
                "knobs": list(n.knobs().keys()),
            }
            nuke.delete(n)
        except Exception as e:
            # registra o que falhou em vez de engolir silenciosamente
            sys.stderr.write(f"skip {cls}: {e}\n")

nuke.Undo.disable()
visit(nuke.menu('Nodes'))
print(json.dumps(res, indent=2, sort_keys=True))