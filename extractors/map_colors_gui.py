# map_colors_gui.py
# Uso: abra o Nuke (GUI), Script Editor, cole este arquivo e rode.
#
# Captura a COR DE TILE default de cada classe — a cor com que o node
# aparece no Node Graph do SEU Nuke (inclui as suas preferencias de
# cor). O viewer carrega o JSON em runtime e pinta os nodes identicos.
#
# Fonte da cor, por classe:
#   1. knob tile_color do node recem-criado, se != 0 (cor propria);
#   2. senao nuke.defaultNodeColor(n.Class()) (cor de preferencia);
#   3. se ambos 0/indisponiveis -> null (viewer usa a paleta embutida).
# Formato Nuke: 0xRRGGBBAA -> gravamos "#rrggbb".
#
# Mesmas salvaguardas dos outros extractors: trabalho todo dentro de
# funcao (globals do __main__ sao compartilhados com callbacks do
# pipeline), escrita atomica, verificacao pos-escrita e sanidade da
# medicao (variedade de cores) com aviso explicito.
import nuke, json, os

def _nkprobe_colors_main():
    OUT = r"C:\Users\matte\Downloads\Scripts\nuke-dag-viewer\data\colors_default.json"  # ajuste para o seu ambiente

    extra_classes = {"Read"}  # menu usa nukescripts.create_read()

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

    def to_hex(v):
        v = int(v) & 0xFFFFFFFF
        return "#%02x%02x%02x" % ((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255)

    res = {}
    skipped = []
    for cls in sorted(classes):
        deselect_all()
        try:
            n = nuke.createNode(cls, inpanel=False)
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
            continue
        try:
            color = None
            try:
                tile = int(n["tile_color"].value())
            except Exception:
                tile = 0
            if tile:
                color = to_hex(tile)
            else:
                try:
                    pref = int(nuke.defaultNodeColor(n.Class()))
                    if pref:
                        color = to_hex(pref)
                except Exception:
                    pass
            res[n.Class()] = color
        except Exception as e:
            skipped.append("%s: %s" % (cls, e))
        finally:
            try:
                nuke.delete(n)
            except Exception:
                pass

    bad = {c: type(v).__name__ for c, v in res.items()
           if not (v is None or (isinstance(v, str) and len(v) == 7 and v[0] == "#"))}
    if bad:
        raise RuntimeError("valores de tipo inesperado em res: %r" % bad)

    tmp_out = OUT + ".tmp"
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    os.replace(tmp_out, OUT)

    with open(OUT, encoding="utf-8") as f:
        check = json.load(f)
    if len(check) != len(res):
        raise RuntimeError("verificacao falhou: %d no arquivo, %d medidas"
                           % (len(check), len(res)))

    colored = [v for v in res.values() if v]
    distinct = len(set(colored))
    print("ok: %d classes, %d bytes -> %s" % (len(res), os.path.getsize(OUT), OUT))
    print("  com cor: %d | sem cor especifica (null): %d | cores distintas: %d"
          % (len(colored), len(res) - len(colored), distinct))
    if colored and distinct < 5:
        print("ATENCAO: pouquissima variedade de cor (%d distintas) — medicao "
              "suspeita, confira antes de usar." % distinct)
    else:
        print("variedade de cores OK — JSON confiavel.")
    if skipped:
        print("skipped %d:" % len(skipped))
        for s in skipped:
            print("  " + s)


_nkprobe_colors_main()
