# map_inputs_gui.py (v2)
# Uso: abra o Nuke normalmente (GUI), abra o Script Editor, cole este
# arquivo inteiro e rode (Ctrl+Enter).
#
# Mede a ARIDADE DEFAULT DE SERIALIZACAO de cada classe — o numero de
# inputs conectados para o qual o Nuke OMITE o knob "inputs" ao gravar
# o script. E' o valor que a tabela NK_INPUTS do viewer assume quando o
# .nk nao traz o knob.
#
# LICAO DA v1 (descartada): copiar um NODE SOZINHO nao e' oraculo — o
# Nuke especial-casa a copia de no unico, ligando o input 0 ao
# $cut_paste_input ("colar conecta na selecao") e OMITINDO o knob
# "inputs" mesmo com o node desconectado. Resultado: 396/423 classes
# mediram "0". O oraculo valido e' a SELECAO MULTI-NO, onde o
# serializador precisa de contagens exatas de pop (prova no paste real:
# Rotos desconectados ganham "inputs 0" explicito para nao roubar a
# cadeia pendurada que esta na pilha).
#
# Metodo v2: para cada classe, cria o node + 1 Dot decoy (nunca
# conectado, so para forcar copia multi-no). Para k = 0,1,2,...:
# conecta k Dots nos inputs 0..k-1, seleciona node+decoy+dots,
# nuke.nodeCopy(arquivo), e procura a linha " inputs N" NO BLOCO DO
# NODE SONDADO (identificado pelo knob name). Primeiro k em que a linha
# some = aridade default.
#
# Saida: inputs_default.json  {classe: default}
#   - null = nunca omitiu ate o teto -> aridade variavel (Switch,
#     Scene...); nesses o Nuke sempre serializa "inputs" e a NK_INPUTS
#     os exclui de proposito.
# No final roda autovalidacao com classes de verdade conhecida (ANCHORS)
# e imprime PASS/FAIL — se falhar, o metodo quebrou de novo: nao use o
# JSON.
import nuke, json, os, re, tempfile

OUT = r"C:\Users\matte\Downloads\Scripts\nuke-dag-viewer\data\inputs_default.json"  # ajuste para o seu ambiente
TMP = os.path.join(tempfile.gettempdir(), "nk_probe.nk")
PROBE_CAP = 4  # maior default da NK_INPUTS atual e' 3 (Keymix, IBKGizmoV3)

# Menu Image>Read usa nukescripts.create_read() (sem "createNode" no
# comando), por isso Read nunca apareceu nos dumps de menu. Forca aqui.
EXTRA_CLASSES = {"Read"}

# verdade conhecida (paste real / uso diario) para autovalidar o metodo
ANCHORS = {"Constant": 0, "Blur": 1, "Grade": 1, "Merge2": 2,
           "ChannelMerge": 2, "Keymix": 3, "Roto": 1, "Switch": None}

INPUTS_RE = re.compile(r"^ inputs (\d+)$")
NAME_RE = re.compile(r"^ name (\S+)$")
HDR_RE = re.compile(r"^[A-Za-z_][\w.]* \{")

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
classes |= EXTRA_CLASSES

def deselect_all():
    for s in nuke.selectedNodes():
        s.setSelected(False)

def select_only(nodes):
    deselect_all()
    for x in nodes:
        x.setSelected(True)

def target_has_inputs_knob(probe_name):
    """Serializa a selecao atual; True/False se o bloco cujo knob name
    == probe_name tem linha ' inputs N'; None se o bloco nao aparecer."""
    if os.path.exists(TMP):
        os.remove(TMP)
    nuke.nodeCopy(TMP)
    in_block = False
    depth = 0
    cur_inputs = False
    cur_is_target = False
    with open(TMP, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if not in_block:
                if HDR_RE.match(line):
                    in_block = True
                    depth = line.count("{") - line.count("}")
                    cur_inputs = False
                    cur_is_target = False
                continue
            if depth == 1:  # knobs de nivel superior do bloco
                if INPUTS_RE.match(line):
                    cur_inputs = True
                m = NAME_RE.match(line)
                if m and m.group(1) == probe_name:
                    cur_is_target = True
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                in_block = False
                if cur_is_target:
                    return cur_inputs
    return None

res = {}
skipped = []
for cls in sorted(classes):
    deselect_all()  # evita auto-conexao do createNode com a selecao
    try:
        n = nuke.createNode(cls, inpanel=False)
    except Exception as e:
        skipped.append("%s: %s" % (cls, e))
        continue
    dots = []
    try:
        try:
            n.setName("NKPROBE_TARGET")
        except Exception:
            pass
        probe_name = n.name()  # nome real (rename pode colidir/falhar)
        for i in range(n.inputs()):
            n.setInput(i, None)
        decoy = nuke.nodes.Dot()  # nunca conectado: forca copia multi-no
        dots.append(decoy)
        cap = PROBE_CAP
        try:
            cap = min(cap, int(n.maxInputs()))
        except Exception:
            pass
        default = None
        for k in range(0, cap + 1):
            if k > 0:
                d = nuke.nodes.Dot()
                dots.append(d)
                if not n.setInput(k - 1, d):
                    break  # classe nao aceita esse indice: para de sondar
            select_only([n] + dots)
            has = target_has_inputs_knob(probe_name)
            if has is None:
                raise RuntimeError("bloco do node nao achado na serializacao")
            if not has:
                default = k
                break
        res[n.Class()] = default
    except Exception as e:
        skipped.append("%s: %s" % (cls, e))
    finally:
        for d in dots:
            try:
                nuke.delete(d)
            except Exception:
                pass
        try:
            nuke.delete(n)
        except Exception:
            pass

# escrita atomica: nunca deixa um OUT truncado para tras (uma run
# interrompida/travada no meio do dump ja produziu um JSON parcial)
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
print("  default fixo: %d | variavel/indeterminado (null): %d" % (fixed, var))

fails = 0
for cls, exp in sorted(ANCHORS.items()):
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
