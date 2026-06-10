# merge_nodes.py
# Uso: python merge_nodes.py nodes_menu.json nodes.json [saida.json]
#
# Mescla o dump do nucleo (gerado via map_nodes_gui.py, dentro do Nuke
# GUI) com o dump de plugins em disco (gerado via map_nodes_v2.py em
# modo terminal). Em conflito, o dump do nucleo (primeiro argumento)
# vence, pois reflete n.inputs() real do node recem-criado.
import json, sys

if len(sys.argv) < 3:
    sys.exit("uso: python merge_nodes.py nodes_menu.json nodes.json [saida.json]")

core_path, plugins_path = sys.argv[1], sys.argv[2]
out_path = sys.argv[3] if len(sys.argv) > 3 else plugins_path

with open(core_path, encoding="utf-8") as f:
    core = json.load(f)
with open(plugins_path, encoding="utf-8") as f:
    plugins = json.load(f)

merged = {**plugins, **core}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, sort_keys=True)

overlap = len(core) + len(plugins) - len(merged)
print("merged: %d classes (%d nucleo + %d plugins, %d sobrepostas) -> %s" % (
    len(merged), len(core), len(plugins), overlap, out_path))
