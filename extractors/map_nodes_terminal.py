# map_nodes_terminal.py  ->  & "...\Nuke14.0.exe" -t map_nodes_terminal.py > nodes.json
import nuke, json, sys, os

res = {}
seen = set()

# pega os plugins .dll/.so/.dylib disponíveis -> nome do arquivo = classe do node
classes = set()
for p in nuke.plugins(nuke.ALL | nuke.NODIR):
    name, ext = os.path.splitext(p)
    if ext.lower() in (".dll", ".so", ".dylib"):
        classes.add(name)

for cls in sorted(classes):
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
        sys.stderr.write(f"skip {cls}: {e}\n")

print(json.dumps(res, indent=2, sort_keys=True))