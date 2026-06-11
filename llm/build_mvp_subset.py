# build_mvp_subset.py
# Uso: python3 llm/build_mvp_subset.py   (da raiz do repo)
#
# Gera prompts/catalog.json: a referencia CURADA de classes/knobs para o
# system prompt de geracao de .nk (LLM). A curadoria (quais knobs
# importam por classe) e' editorial e vive no dict CURATION abaixo; a
# VALIDACAO e' programatica e inegociavel:
#   - a classe tem que existir EXATA no data/nodes.json;
#   - cada knob curado tem que existir na lista de knobs da classe;
#   - a aridade vem do data/inputs_default.json (medida).
# Qualquer divergencia ABORTA com sugestao por proximidade (difflib) —
# erro > chute, como em todo o projeto.
#
# Saida por classe:
#   class                  nome real (TCL) — ex.: Keylight e' classe OFX longa
#   menu                   nome amigavel, quando difere da classe
#   arity_default          pops do paste sem knob "inputs" (medido)
#   max_inputs             do catalogo (conta opcionais)
#   mask_input             indice do input opcional de mask, se houver
#   input_labels           semantica dos inputs (B/A/mask p/ familia merge)
#   knobs                  curados e validados contra o catalogo
#   notes                  regras de geracao (ex.: Roto nunca gera curvas)
import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NODES = os.path.join(HERE, "..", "data", "nodes.json")
INPUTS = os.path.join(HERE, "..", "data", "inputs_default.json")
OUT = os.path.join(HERE, "..", "prompts", "catalog.json")

KEYLIGHT = "OFXuk.co.thefoundry.keylight.keylight_v201"

# (classe_real, menu, knobs_curados, notes)
CURATION = [
    ("Read", None,
     ["file", "first", "last", "origfirst", "origlast", "frame_mode",
      "frame", "on_error", "colorspace", "premultiplied", "raw"],
     "Generator (aridade 0). file usa caminho com padding #### ou %04d."),
    ("Write", None,
     ["file", "file_type", "channels", "colorspace", "raw", "premultiplied",
      "create_directories", "first", "last", "use_limit"],
     "Knobs especificos de formato (datatype/compression/...) so existem "
     "apos definir file_type — nao gerar; deixar para o artista."),
    ("Merge2", "Merge",
     ["operation", "mix", "bbox", "also_merge", "screen_alpha", "output"],
     "input0=B, input1=A, input2=mask. Com 2+ inputs conectados o knob "
     "\"inputs\" e' OBRIGATORIO (\"2\" ou \"2+1\" com mask)."),
    ("Grade", None,
     ["channels", "blackpoint", "whitepoint", "black", "white", "multiply",
      "add", "gamma", "reverse", "black_clamp", "white_clamp", "unpremult",
      "invert_mask", "mix"],
     None),
    ("ColorCorrect", None,
     ["channels", "saturation", "contrast", "gamma", "gain", "offset",
      "unpremult", "mix"],
     None),
    ("Multiply", None,
     ["channels", "value", "invert_mask", "mix", "unpremult"],
     None),
    ("Premult", None, ["channels", "alpha"], None),
    ("Unpremult", None, ["channels", "alpha"], None),
    ("Roto", None,
     ["output"],
     "NUNCA gerar o knob \"curves\" (irrepresentavel; o artista desenha). "
     "Gerar no vazio como placeholder nomeado."),
    ("RotoPaint", None,
     ["output"],
     "Mesma regra do Roto: nunca gerar \"curves\"/strokes."),
    ("Keyer", None, ["input", "output", "operation", "range"], None),
    (KEYLIGHT, "Keylight",
     ["screenColour", "screenGain", "screenBalance", "alphaBias",
      "despillBias", "preBlur", "screenClipMin", "screenClipMax",
      "screenGrowShrink", "screenSoftness"],
     "Classe OFX: usar o nome completo no TCL."),
    ("Primatte3", "Primatte",
     ["algorithm", "mode", "output_mode", "spill", "matte", "detail",
      "crop", "invert_mask"],
     None),
    ("IBKColourV3", "IBKColour",
     ["screen_type", "mult"],
     "Par com IBKGizmoV3 (workflow IBK)."),
    ("IBKGizmoV3", "IBKGizmo",
     ["st", "red_weight", "lm_enable"],
     "inputs 2 tipicamente: input0=plate, input1=IBKColourV3."),
    ("EdgeBlur", None, ["size", "filter"], None),
    ("Blur", None, ["channels", "size", "filter", "quality", "crop", "mix"], None),
    ("Defocus", None,
     ["channels", "defocus", "ratio", "scale", "quality", "method", "mix"],
     None),
    ("Transform", None,
     ["translate", "rotate", "scale", "skewX", "skewY", "center", "filter",
      "clamp", "black_outside", "motionblur", "shutter"],
     None),
    ("CornerPin2D", None,
     ["to1", "to2", "to3", "to4", "from1", "from2", "from3", "from4",
      "invert", "filter", "motionblur"],
     None),
    ("TimeOffset", None, ["time_offset", "reverse_input"], None),
    ("Retime", None, ["speed", "reverse", "filter", "before", "after"], None),
    ("Shuffle2", "Shuffle",
     ["fromInput1", "fromInput2", "in1", "in2", "out1", "out2", "mappings"],
     "Shuffle moderno; o legado \"Shuffle\" nao deve ser gerado."),
    ("Copy", None,
     ["from0", "to0", "from1", "to1", "from2", "to2", "from3", "to3",
      "channels"],
     None),
    ("Dot", None, [],
     "So roteamento/legibilidade; usar knob \"label\" para anotar."),
    ("Constant", None, ["color", "channels", "format"],
     "Generator (aridade 0)."),
    ("Reformat", None,
     ["type", "format", "scale", "resize", "center", "flip", "flop", "turn",
      "filter", "black_outside", "pbb"],
     None),
    ("Crop", None, ["box", "softness", "reformat", "intersect", "crop"], None),
    ("ChannelMerge", None,
     ["operation"],
     "input0=B, input1=A; knob \"inputs 2\" obrigatorio com A e B."),
    ("FilterErode", None, ["channels", "size", "filter"], None),
    ("Keymix", None, ["channels", "invertMask", "mix", "bbox"],
     "3 inputs nativos: input0=B, input1=A, input2=mask — knob "
     "\"inputs 3\" obrigatorio quando os 3 conectados."),
    ("Expression", None,
     ["expr0", "expr1", "expr2", "expr3"],
     "Aliases do viewer: expr_r/g/b/a <-> expr0..3 (conversao nos dois "
     "sentidos no JSON canonico)."),
    ("Switch", None, ["which"],
     "Aridade variavel: o Nuke sempre serializa o knob \"inputs N\" — "
     "gerar SEMPRE com o knob explicito."),
]

MERGE_LABELS = {
    "Merge2": ["B", "A", "mask"],
    "ChannelMerge": ["B", "A"],
    "Keymix": ["B", "A", "mask"],
}

def main():
    with open(NODES, encoding="utf-8") as f:
        nodes = json.load(f)
    with open(INPUTS, encoding="utf-8") as f:
        arity = json.load(f)

    errors = []
    subset = {}
    for cls, menu, knobs, notes in CURATION:
        if cls not in nodes:
            close = difflib.get_close_matches(cls, nodes.keys(), n=3, cutoff=0.4)
            errors.append("classe %r nao existe no catalogo; proximas: %s"
                          % (cls, close))
            continue
        info = nodes[cls]
        valid = set(info.get("knobs") or [])
        for k in knobs:
            if k not in valid:
                close = difflib.get_close_matches(k, valid, n=4, cutoff=0.4)
                errors.append("%s: knob %r nao existe; proximos: %s"
                              % (cls, k, close))
        entry = {
            "arity_default": arity.get(cls),
            "max_inputs": info.get("maxInputs"),
            "knobs": knobs,
        }
        if menu:
            entry["menu"] = menu
        if "optionalInput" in info:
            entry["mask_input"] = info["optionalInput"]
        if cls in MERGE_LABELS:
            entry["input_labels"] = MERGE_LABELS[cls]
        if notes:
            entry["notes"] = notes
        subset[cls] = entry

    if errors:
        print("CURADORIA INVALIDA — %d erro(s):" % len(errors))
        for e in errors:
            print("  " + e)
        sys.exit(1)

    payload = {
        "_meta": {
            "source": "data/nodes.json + data/inputs_default.json "
                      "(medidos, Nuke 14.0v2)",
            "generator": "llm/build_mvp_subset.py",
            "purpose": "referencia curada p/ system prompt de geracao .nk",
            "arity_default_null": "classe nao medida pelo map_inputs_gui "
                                  "(lei extrapolada: 1); irrelevante para "
                                  "geracao — o dialeto sempre grava o knob "
                                  "inputs explicito",
            "classes": len(subset),
        },
        "classes": subset,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, OUT)
    size = os.path.getsize(OUT)
    nknobs = sum(len(e["knobs"]) for e in subset.values())
    print("ok: %d classes, %d knobs curados, %d bytes (~%dk tokens) -> %s"
          % (len(subset), nknobs, size, round(size / 4 / 1000), OUT))

main()
