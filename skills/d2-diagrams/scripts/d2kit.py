"""d2kit: describe boxes and links, let D2 lay them out.

Import this from a small build script kept next to the diagrams:

    import sys; sys.path.insert(0, "<skill>/scripts")
    from d2kit import node, plain, link, group, grid, spine, initial, final_marker, build

    def flow(direction):
        return "\n".join([f"direction: {direction}",
                          node("api", "API", "validates requests", "process"),
                          node("db", "Orders", "Postgres", "store"),
                          link("api", "db", "write")])

    build({"1-flow": (flow, ("down", "right"), {"notation": "dataflow"})}, out_dir="docs/diagrams")

A node's class is its kind (which sets the shape) plus, optionally, its status (which sets the
colour): "process", "decision", "terminator", "io", "store", "queue", "doc", "external", "person",
"state", then "focus", "risk", "hold", "good", "check" or "out". For example "terminator risk".

The "notation" option names the standard a diagram follows ("flowchart", "dataflow", "state",
"c4"; see PROFILES). build() then refuses shapes that notation does not have and warns about
unlabelled arrows, so a diagram cannot quietly drift into an invented notation.

Nothing here takes a coordinate. If a diagram looks wrong, change what it says (fewer boxes,
shorter labels, a different grouping or direction), never where things sit.
"""

import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder and the user's project
shutil.rmtree(Path(__file__).resolve().parent / "__pycache__", ignore_errors=True)  # this module's own cache is written before the line above runs

# True: two-line labels with a bold name (HTML inside the SVG; right for web pages and for PNG).
# False: plain SVG text, for SVGs that must survive non-browser renderers. build(plain_labels=True) sets it.
MARKDOWN = True

# Shape says what KIND of thing a node is; colour says its STATUS. Keep both meanings fixed across a set.
PALETTE = {
    "paper": "#F5F6F8",
    "focus": ("#DFE4FA", "#2740C4"),   # the thing under discussion / where the reader starts
    "store": ("#E6EAEE", "#5A6672"),   # data at rest or in transit (default colour of store, queue, doc)
    "step": ("#D3EEEC", "#0B7F7A"),    # work the system does (default colour of process and state)
    "check": ("#FCEBC5", "#B87A00"),   # decisions and guards (default colour of decision)
    "risk": ("#F7D9E9", "#B5176E"),    # blocked, failed, lost, refused
    "hold": ("#E9E1F7", "#6B46C1"),    # waiting on a person, pending, needs review, stale
    "good": ("#D9F2DF", "#1F7A3A"),    # approved, succeeded
    "out": ("#FFFFFF", "#000000"),     # neutral (default colour of terminator)
}
# kind -> (D2 shape, default colour, extra style). Where a standard defines the symbol, the shape
# follows it: ISO 5807 / ANSI X3.5 flowcharts (process rectangle, decision diamond, terminator with
# rounded ends, input/output parallelogram, document, disk cylinder for stored data), data-flow
# diagrams (process, store, external entity) and UML 2.5.1 state machines (rounded state, filled
# initial dot, bullseye final marker; see initial() and final_marker()). Conventions, not standards:
# the horizontal cylinder for a queue or topic, C4's person shape, and every colour.
KINDS = {
    "process":    ("rectangle", "step", "border-radius: 6; "),
    "decision":   ("diamond", "check", ""),
    "terminator": ("rectangle", "out", "border-radius: 999; "),   # D2's "oval" is an ellipse, not this
    "io":         ("parallelogram", "store", ""),
    "store":      ("cylinder", "store", ""),
    "queue":      ("queue", "store", ""),
    "doc":        ("document", "store", ""),
    "external":   ("rectangle", "focus", "border-radius: 0; "),
    "person":     ("c4-person", "focus", ""),
    "state":      ("rectangle", "step", "border-radius: 22; "),
    "final":      ("rectangle", "out", "border-radius: 22; double-border: true; "),  # old; use final_marker()
}
# names used by earlier versions of the kit; "event" drew an ellipse and meant several things
ALIASES = {"step": "process", "ask": "decision", "event": "terminator"}
MARKERS = ("initial", "end")   # UML pseudostates, drawn by initial() and final_marker()

# The standard each notation follows, the kinds it has, and what build() checks.
PROFILES = {
# "arrows": the connector styles a notation has. Flowcharts, data flows and UML state machines draw
# every connector the same way: what an arrow carries goes in its label, not in its colour or weight.
    "flowchart": {"standard": "ISO 5807 / ANSI X3.5 flowchart", "title": "Flowchart: ",
                  "kinds": {"terminator", "process", "decision", "io", "doc", "store"}, "label_all": False,
                  "arrows": {"flow"}},
    "dataflow": {"standard": "data-flow diagram (Yourdon/DeMarco, Gane & Sarson)", "title": "Data flow: ",
                 "kinds": {"process", "store", "queue", "doc", "external", "person"}, "label_all": True,
                 "max_process": 6, "arrows": {"flow"}},
    "state": {"standard": "UML 2.5.1 state machine", "title": "State machine: ",
              "kinds": {"state", "decision", "initial", "end"}, "label_all": True, "arrows": {"flow"}},
    "c4": {"standard": "C4 model (system context / container)", "title": "",
           "kinds": {"person", "external", "process", "store", "queue"}, "label_all": True,
           "arrows": {"flow", "dashed"}},   # C4 allows line styles that the key explains, e.g. dashed = async
}
TONES = ("focus", "risk", "hold", "good", "check", "out")
# D2 keywords that cannot be used as ids ("link" bit us once).
RESERVED = {"link", "label", "shape", "style", "class", "classes", "near", "width", "height", "icon", "tooltip",
            "direction", "constraint", "top", "left", "vars", "layers", "scenarios", "steps", "grid-rows",
            "grid-columns", "grid-gap", "vertical-gap", "horizontal-gap", "source-arrowhead", "target-arrowhead"}


def head(palette=None):
    p = {**PALETTE, **(palette or {})}
    kinds = "\n".join(
        f'  {k}: {{shape: {shape}; style: {{fill: "{p[c][0]}"; stroke: "{p[c][1]}"; stroke-width: 2; {x}font-color: "#000000"}}}}'
        for k, (shape, c, x) in KINDS.items())
    tones = "\n".join(f'  {t}: {{style: {{fill: "{p[t][0]}"; stroke: "{p[t][1]}"}}}}' for t in TONES)
    edge = lambda colour, w=2, dash="": (  # noqa: E731
        f'{{style: {{stroke: "{colour}"; stroke-width: {w}; {dash}font-color: "#000000"; italic: false; font-size: 14}}}}')
    return f"""vars: {{
  d2-config: {{
    layout-engine: elk
    pad: 12
  }}
}}
style.fill: "{p['paper']}"
classes: {{
{kinds}
{tones}
  initial: {{shape: circle; width: 18; height: 18; style: {{fill: "#000000"; stroke: "#000000"}}}}
  end: {{shape: text; style: {{font-size: 30; font-color: "#000000"}}}}
  blank: {{style: {{opacity: 0}}}}
  note:  {{shape: text; style: {{font-color: "#4A5560"; font-size: 15; bold: false}}}}
  keybox: {{style: {{fill: transparent; stroke-width: 0; font-size: 8}}}}
  group: {{label.near: top-left; style: {{fill: transparent; stroke: "#9AA5B1"; stroke-dash: 4; border-radius: 10; font-color: "#4A5560"; font-size: 18; bold: false}}}}
  flow:   {edge('#000000')}
  ref:    {edge(p['store'][1], 2, 'stroke-dash: 2; ')}
  strong: {edge(p['step'][1], 4)}
  warn:   {edge(p['risk'][1])}
  dashed: {edge(p['check'][1], 2, 'stroke-dash: 4; ')}
  accent: {edge(p['focus'][1], 3)}
}}
"""


def q(text):
    return json.dumps(text, ensure_ascii=False).replace("$", "\\$")  # a bare $ starts a D2 substitution


def _id(i):
    if i.split(".")[-1] in RESERVED:
        raise ValueError(f"'{i}' is a reserved D2 keyword; pick another id")
    return i


def _cls(spec):
    """'store' -> store; 'terminator risk' -> [terminator; risk]; 'risk' alone -> [process; risk]."""
    words = [ALIASES.get(w, w) for w in (spec or "process").split()]
    kinds = [w for w in words if w in KINDS or w in ("blank", "note", *MARKERS)]
    tones = [w for w in words if w in TONES]
    unknown = set(words) - set(kinds) - set(tones)
    if unknown or len(kinds) > 1:
        raise ValueError(f"'{spec}': use one kind ({', '.join(KINDS)}) and optionally one status ({', '.join(TONES)})")
    both = (kinds or ["process"]) + tones
    return both[0] if len(both) == 1 else "[" + "; ".join(both) + "]"


def _size(cls, *text):
    """D2 sizes a person's head to its width, so a long label gives a giant head that stretches its
    whole grid row. Give it a fixed size and keep its label short (about 14 characters a line)."""
    if "person" not in _cls(cls):
        return ""
    return f"; width: {max(150, 8 * max(len(t or '') for t in text) + 40)}; height: 110"


def node(i, title, sub=None, cls="process"):
    """A node with a short bold name and, optionally, one short second line.
    cls is a kind, optionally followed by a status: "process", "store", "terminator risk", "queue hold"."""
    size = _size(cls, title, sub)
    if not MARKDOWN or "decision" in _cls(cls):  # a question reads as one centred sentence, wrapped over two lines
        return f"{_id(i)}: {q(title + (chr(10) + sub if sub else ''))} {{class: {_cls(cls)}{size}}}"
    body = f"**{title}**  \n{sub}" if sub else f"**{title}**"
    return f"{_id(i)}: {{\n  class: {_cls(cls)}{size.replace('; ', chr(10) + '  ')}\n  label: |md\n{body}\n|\n}}"


def plain(i, title, cls="process"):
    """A one-line node (use inside grids, or for 'blank' spacer cells with an empty title)."""
    return f"{_id(i)}: {q(title)} {{class: {_cls(cls)}{_size(cls, title)}}}"


def initial(target, i="d2kit_start"):
    """The UML initial marker: a small black dot with an arrow to the state where things begin."""
    return f'{i}: "" {{class: initial}}\n{i} -> {target}: {{class: flow}}'


def final_marker(source, trigger=None, i=None):
    """The UML final marker (a bullseye) with an arrow from the last state. A named end state such
    as "Published" stays an ordinary state; this marker after it says the machine stops there."""
    i = i or f"d2kit_end_{source.replace('.', '_')}"
    return f'{i}: "◉" {{class: end}}\n{link(source, i, trigger)}'


def link(a, b, text=None, cls="flow"):
    """An arrow. Classes: flow, ref, strong, warn, dashed, accent."""
    return f"{a} -> {b}: {q(text) + ' ' if text else ''}{{class: {cls}}}"


def group(i, title, *body, extra=""):
    """A dashed container. `extra` takes raw D2 lines, e.g. 'grid-rows: 1'."""
    inner = "\n".join("  " + ln for ln in "\n".join(body).splitlines())
    extra = "".join(f"  {ln}\n" for ln in extra.splitlines() if ln.strip())
    return f"{_id(i)}: {q(title)} {{\n  class: group\n{extra}{inner}\n}}"


def grid(columns, *cells, h_gap=70, v_gap=50):
    """Root-level grid. D2 0.7 fills column by column. Arrows between grid cells are drawn as
    straight lines, so only link cells that end up next to each other."""
    return "\n".join([f"grid-columns: {columns}", f"horizontal-gap: {h_gap}", f"vertical-gap: {v_gap}", *cells])


def spine(main, side=None, direction="down", carries=None, side_cls="flow", gap=None):
    """A main path drawn as one straight line, with exceptions hanging off the step that causes them.

    main: [(id, title, sub, cls), ...] in order, joined by arrows.
    carries: what moves along each main arrow, one label per arrow (len(main) - 1), e.g.
          ["event batches", "raw events", ...]. In a data flow the arrows are the data, so name it.
    side: {main_id: [(id, title, sub, cls) or (id, title, sub, cls, arrow_label), ...]} drawn beside
          that step as a chain leading away from it (main -> first -> second), with `side_cls` arrows.
    Layered layout gives every branch equal weight, so a path with side branches drifts sideways at
    each one. This puts the path on a grid instead: the reader's eye runs straight along it."""
    side = side or {}
    carries = list(carries or [])
    if carries and len(carries) != len(main) - 1:
        raise ValueError(f"carries needs one label per main arrow: {len(main) - 1}, got {len(carries)}")
    width = 1 + max([len(v) for v in side.values()] or [0])
    down = direction in ("down", None)
    side_labels = any(len(c) > 4 and c[4] for v in side.values() for c in v)
    # room for the arrow labels: along the path only when it carries labels, across it for side labels
    along = (gap or (0, 0))[1] or (64 if carries else 34)
    across = (gap or (0, 0))[0] or (150 if side_labels else 60)
    if not down and carries:
        along = max(along, 40 + 8 * max(len(c or "") for c in carries))
    a, b = ("rows", "columns") if down else ("columns", "rows")
    out = [f"grid-{a}: {len(main)}", f"grid-{b}: {width}",  # D2 fills along the dimension named first
           f"horizontal-gap: {across if down else along}", f"vertical-gap: {along if down else across}"]
    for n, m in enumerate(main):
        cells = [node(*m[:4])] + [node(*c[:4]) for c in side.get(m[0], [])]
        cells += [plain(f"d2kit_gap_{n}_{k}", "", "blank") for k in range(width - len(cells))]
        out += cells
    out += [link(x[0], y[0], carries[n] if carries else None) for n, (x, y) in enumerate(zip(main, main[1:]))]
    for m_id, chain in side.items():
        prev = m_id
        for c in chain:
            out.append(link(prev, c[0], c[4] if len(c) > 4 else None, side_cls))
            prev = c[0]
    return "\n".join(out)


def title_block(title, subtitle=None, size=20):
    """A heading inside the image, for a diagram that will be pasted somewhere on its own."""
    if MARKDOWN:
        text = f"**{title}**" + (f"  \n{subtitle}" if subtitle else "")
        return f"d2kit_title: |md\n{text}\n| {{near: top-center; style.font-size: {size}}}"
    text = title + (f"\n{subtitle}" if subtitle else "")
    return f"d2kit_title: {q(text)} {{shape: text; near: top-center; style.font-size: {size}; style.bold: true}}"


EDGE_SAMPLES = {"flow": ("────▶", "out"), "warn": ("────▶", "risk"), "strong": ("━━▶", "step"), "accent": ("━━▶", "focus"),
                "dashed": ("- - ▶", "check"), "ref": ("· · ▶", "store")}


def key_block(items, arrows=None, note=None, at="below", per_row=3, palette=None):
    """A boxed legend: a small sample of each shape or arrow with its meaning beside it.

    items:  [(cls, text), ...] where cls is what you pass to node() ("store", "terminator risk").
    arrows: [(link class, text), ...] e.g. [("warn", "leaves the main path"), ("dashed", "timer")].
    note:   one more line of plain text, if something does not fit either list.
    at:     "right" stacks the entries in one column beside the diagram (for tall diagrams);
            "below" lays them out per_row to a row under it (for wide ones). build() picks.
    Cells in a grid row share a height, and D2 will not draw a cylinder shorter than about 58 px,
    so flat samples go on rows of their own, then tall ones, then the arrows: nothing gets stretched."""
    p = {**PALETTE, **(palette or {})}

    def glyph(text, size, colour="#000000", h=34, bold=False):  # a clear box keeps its text centred
        return (f'{q(text)} {{width: 56; height: {h}; style: {{fill: transparent; stroke-width: 0; font-size: {size}; '
                f'bold: {str(bold).lower()}; font-color: "{colour}"}}}}', h)

    flat, tall, lines = [], [], []
    for cls, text in items:
        words = [ALIASES.get(w, w) for w in cls.split()]
        kind = next((w for w in words if w in KINDS), "process")
        marker = next((w for w in words if w in MARKERS), None)
        if marker:  # markers and people are drawn as glyphs: as shapes a grid cell would stretch them
            flat.append((*glyph(*{"initial": ("●", 20), "end": ("◉", 24)}[marker]), text))
        elif kind == "person":
            flat.append((*glyph("👤", 22), text))
        else:
            # D2 draws a cylinder's lid at a fixed size, so below these sizes it turns into a blob
            w, h = {"store": (50, 58), "queue": (84, 34), "doc": (46, 30), "io": (50, 26)}.get(kind, (56, 34))
            (tall if kind == "store" else flat).append(
                (f'"" {{class: {_cls(cls)}; width: {w}; height: {h}; style.stroke-width: 1}}', h, text))
    for cls, text in arrows or []:
        g, colour = EDGE_SAMPLES.get(cls, EDGE_SAMPLES["flow"])
        lines.append((*glyph(g, 14, p[colour][1], 26, True), text))
    per_row = 1 if at == "right" else max(1, min(per_row, max(len(flat), len(tall), len(lines), 1)))
    entries = []
    for run in (flat, tall, lines):  # each run starts on a fresh row
        if run:
            entries += run + [None] * (-len(run) % per_row)
    if note:
        entries += [("", 26, note)] + [None] * (per_row - 1)
    cols = 3 * per_row - 1   # sample, text, and a spacer between entries
    cells = []
    for n, e in enumerate(entries):
        if n % per_row:
            cells.append(f'  g{n}: "" {{class: blank; width: 28; height: 1}}')
        if e is None:
            cells += [f'  s{n}: "" {{class: blank; width: 1; height: 1}}', f'  t{n}: "" {{class: blank; width: 1; height: 1}}']
            continue
        sample, h, text = e
        cells.append(f"  s{n}: {sample}" if sample else f'  s{n}: "" {{class: blank; width: 1; height: 1}}')
        cells.append(f'  t{n}: {q(text)} {{width: {int(7.4 * len(text)) + 16}; height: {h}; label.near: center-left; '
                     f'style: {{fill: transparent; stroke-width: 0; font-size: 14; bold: false; font-color: "#000000"}}}}')
    return "\n".join([
        'd2kit_key: "Key" {', f"  near: {'center-right' if at == 'right' else 'bottom-center'}", "  label.near: top-left",
        '  style: {fill: "#FFFFFF"; stroke: "#9AA5B1"; stroke-width: 1; border-radius: 6; font-size: 13; bold: true; font-color: "#4A5560"}',
        f"  grid-rows: {len(entries) // per_row}", f"  grid-columns: {cols}", "  horizontal-gap: 12", "  vertical-gap: 10",
        *cells, "}"])


D2_FLAGS = ["--elk-nodeNodeBetweenLayers=46", "--elk-edgeNodeBetweenLayers=28",
            "--elk-padding=[top=46,left=28,bottom=28,right=28]"]
DAGRE_FLAGS = ["--dagre-nodesep=70", "--dagre-edgesep=40"]


def _render(src, dest, engine="elk"):
    flags = DAGRE_FLAGS if engine == "dagre" else D2_FLAGS
    p = subprocess.run(["d2", *flags, str(src), str(dest)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[-1500:])


def svg_size(svg_path):
    m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', Path(svg_path).read_text())
    return float(m.group(1)), float(m.group(2))


def _spec(entry):
    fn, directions, *rest = entry if isinstance(entry, tuple) else (entry, None)
    opts = rest[0] if rest else {}
    takes_dir = bool(inspect.signature(fn).parameters)
    directions = tuple(directions or (("down",) if takes_dir else (None,)))
    return (lambda d: fn(d) if takes_dir else fn()), directions, opts


def _extras(opts, key_at, per_row, palette):
    extra = []
    if opts.get("title"):
        extra.append(title_block(opts["title"], opts.get("subtitle"), opts.get("title_size", 20)))
    if opts.get("key") or opts.get("arrows") or opts.get("note"):
        extra.append(key_block(opts.get("key") or [], opts.get("arrows"), opts.get("note"), key_at, per_row, palette))
    return "\n" + "\n".join(extra)


def check_notation(body, notation):
    """Check generated D2 against a notation profile. Returns (errors, warnings).
    Errors: a shape or arrow style the notation does not have. Warnings: unlabelled arrows where the notation
    labels every one, and more processes on one data-flow diagram than a reader can hold."""
    prof = PROFILES[notation]
    used, processes, errors, warnings = {}, 0, [], []
    lines = body.splitlines()
    for n, ln in enumerate(lines):
        if "->" in ln:
            continue
        m = re.search(r"class: (\[[^\]]+\]|[\w-]+)", ln)
        if not m:
            continue
        words = m.group(1).strip("[]").replace(";", " ").split()
        for w in words:
            if w in KINDS or w in MARKERS:
                owner = (ln.split(":")[0] if not ln.strip().startswith("class:") else lines[n - 1].split(":")[0]).strip()
                used.setdefault(w, owner)
                processes += w == "process"
    for kind, example in used.items():
        if kind not in prof["kinds"]:
            errors.append(f"'{kind}' (e.g. {example}) is not part of a {prof['standard']}; "
                          f"use one of: {', '.join(sorted(prof['kinds']))}")
    styles = {}
    for ln in lines:
        m = re.search(r"->.*class: ([\w-]+)", ln)
        if m:
            styles.setdefault(m.group(1), ln.split(":")[0].strip())
    for style, example in styles.items():
        if style not in prof["arrows"]:
            errors.append(f"arrow style '{style}' (e.g. {example}) is not part of a {prof['standard']}, which draws "
                          f"every connector alike; use {' or '.join(sorted(prof['arrows']))} and say what is "
                          "special in the label"),
    if prof.get("label_all"):
        bare = [ln.strip() for ln in lines if re.search(r"->\s*[\w.]+\s*:\s*\{", ln)
                and "opacity: 0" not in ln and "d2kit_start" not in ln and "d2kit_end" not in ln]
        if bare:
            warnings.append(f"{len(bare)} unlabelled arrow(s), e.g. {bare[0].split(':')[0]}")
    if prof.get("max_process") and processes > prof["max_process"]:
        warnings.append(f"{processes} processes; a {prof['standard']} keeps about {prof['max_process']} "
                        "per diagram: split it into levels")
    return errors, warnings


def _shape_penalty(w, h):
    """0 for a comfortable proportion; grows as the image becomes a flat strip or a thin tower."""
    ratio = w / h
    return 0.0 if 0.45 <= ratio <= 2.4 else round(abs(math.log(ratio / (0.45 if ratio < 0.45 else 2.4))), 2)


def build(diagrams, out_dir, src_dir=None, page_width=1180, names=None, palette=None, png=True,
          plain_labels=False, max_height=2000, min_scale=0.65):
    """diagrams: {name: fn} or {name: (fn, directions)} or {name: (fn, directions, options)}.

    fn(direction) returns D2 text without the header; a grid diagram can be fn() with no argument.
    With several directions, each is rendered as it would appear on a page_width page (a wider
    diagram is shrunk to fit, down to min_scale). A flat strip or a thin tower loses to a layout
    with a comfortable proportion, and one shrunk below 85% loses to one that is not; among the
    rest, the one that takes the least height is kept.
    options:
      "title", "subtitle"  a heading inside the image, for diagrams that will stand alone
      "title_size"         its font size (default 20; about 32 for a slide)
      "key": [(class, text), ...], "arrows": [(link class, text), ...], "note": "..."
                           a boxed legend; it goes beside a tall diagram and below a wide one
      "key_at": "right" | "below"   overrides that choice
      "engine": "elk" (default; straight, right-angled arrows) or "dagre" (curved arrows; better
                for graphs with loops such as state machines)
      "notation": "flowchart" | "dataflow" | "state" | "c4"   the standard the diagram follows:
                shapes outside it fail the build, unlabelled arrows are reported, and the title
                gets the notation's prefix ("Data flow: ...") unless it already names it
    plain_labels=True writes plain SVG text instead of HTML labels."""
    global MARKDOWN
    MARKDOWN = not plain_labels
    if not shutil.which("d2"):
        sys.exit("d2 is not installed. macOS: brew install d2. Others: https://d2lang.com/tour/install")
    out, ok = Path(out_dir), True
    src_dir = Path(src_dir) if src_dir else out / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    for name in names or list(diagrams):
        fn, directions, opts = _spec(diagrams[name])
        notes = []
        if opts.get("notation"):
            prof = PROFILES[opts["notation"]]
            errors, notes = check_notation(fn(directions[0]), opts["notation"])
            if errors:
                ok = False
                print(f"[{name}] FAILED notation {opts['notation']}:\n  " + "\n  ".join(errors))
                continue
            word = prof["title"].split(":")[0].lower()
            if opts.get("title") and prof["title"] and word not in opts["title"].lower():
                opts = {**opts, "title": prof["title"] + opts["title"]}
        engine = opts.get("engine", "elk")
        hd = head(palette).replace("layout-engine: elk", f"layout-engine: {engine}")
        src, svg, best = src_dir / f"{name}.d2", out / f"{name}.svg", None
        try:
            for d in directions:
                body = fn(d)
                src.write_text(hd + body + "\n")          # measure the diagram alone, then place the key
                _render(src, svg, engine)
                w0, h0 = svg_size(svg)
                # beside a tall diagram when there is room on the page for it, otherwise below
                key_at = opts.get("key_at") or ("right" if h0 > 1.15 * w0 and w0 + 300 <= page_width else "below")
                text = hd + body + _extras(opts, key_at, max(1, int(w0 // 230)), palette) + "\n"
                src.write_text(text)
                _render(src, svg, engine)
                w, h = svg_size(svg)
                scale = min(1.0, page_width / w)
                score = (scale < min_scale, _shape_penalty(w, h), scale < 0.85, h * scale if scale >= min_scale else w)
                if best is None or score < best[0]:
                    best = (score, d, w, h, text)
            src.write_text(best[4])
            _render(src, svg, engine)
            if png:
                _render(src, out / f"{name}.png", engine)
            for f in (svg, out / f"{name}.png", src):
                if f.exists():
                    os.chmod(f, 0o644)  # D2 writes 0600, which breaks sharing and web servers
            scale = min(1.0, page_width / best[2])
            fits = "" if scale == 1 else f"  shown at {scale:.0%} on a {page_width} px page"
            fits += "" if scale >= min_scale else "  TEXT TOO SMALL AT PAGE WIDTH: simplify or split"
            fits += "" if best[3] * scale <= max_height else f"  TALLER THAN {max_height}: merge steps or split"
            fits += "" if not best[0][1] else ("  FLAT STRIP" if best[2] > best[3] else "  THIN TOWER") + ": try the other direction or engine"
            fits += "".join(f"  NOTATION: {w}" for w in notes)
            print(f"[{name}] ok  direction={best[1] or 'grid'}  {best[2]:.0f} x {best[3]:.0f}{fits}")
        except RuntimeError as e:
            ok = False
            print(f"[{name}] FAILED\n{e}")
    return ok


def inline_svg(svg_path, title):
    """Return (svg_markup, natural_width) ready to paste into an HTML page. Inline rather than
    <img>: D2's two-line labels are HTML inside the SVG and render most reliably inline."""
    svg = re.sub(r"^<\?xml[^>]*\?>", "", Path(svg_path).read_text())
    w, _ = svg_size(svg_path)
    style = f'style="display:block;width:100%;height:auto;max-width:{w:.0f}px;min-width:{min(w, 600):.0f}px" role="img" aria-label={q(title)}'
    return svg.replace("<svg ", f"<svg {style} ", 1), w


if __name__ == "__main__":
    v = subprocess.run(["d2", "--version"], capture_output=True, text=True) if shutil.which("d2") else None
    print("d2", v.stdout.strip() if v else "NOT INSTALLED (macOS: brew install d2)")
    caches = [Path.home() / "Library/Caches/ms-playwright", Path.home() / ".cache/ms-playwright"]
    has = any(c.exists() and any(c.glob("chromium*")) for c in caches)
    print("png export:", "browser already cached" if has else
          "NO cached browser; the first PNG export downloads about 150 MB. Ask first, or pass png=False")
    print("kit path:", Path(__file__).resolve().parent)
