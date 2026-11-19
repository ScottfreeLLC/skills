# D2 notes (verified on D2 0.7.1)

## Build failures

- **"reserved keywords are prohibited in edges"**: a node id is a D2 keyword (`link`, `label`,
  `shape`, `style`, `near`, `width`, `top`, `left`, ...). `d2kit` raises a clear error for these;
  rename the id.
- **"substitutions must begin on {"**: a bare `$` in a quoted label ("over $150") starts a D2
  substitution. `d2kit.q()` escapes it; in hand-written D2 write `\$`.
- **Quoting**: colours must be quoted (`"#2740C4"`) because `#` starts a comment. `d2kit.q()`
  quotes labels.
- **Markdown labels**: `|md ... |` blocks cannot contain `|`. A line that starts with `1.` becomes a
  list. Intraword underscores (`title_number`) are safe.
  A line that starts with `>` becomes a blockquote, so write "more than 30 days", not "> 30 days".

## Layout behaviour

- **Engines**: `elk` (used here) and `dagre` are bundled. `tala` is a separate paid plugin and the
  only one that supports a different direction per container.
- **Direction is global.** To get a row inside a top-to-bottom diagram, give that container
  `grid-rows: 1`.
- **Grids**: with only `grid-columns: N`, cells fill column by column (top to bottom, then the next
  column). With both `grid-rows` and `grid-columns`, cells fill along the one named first; `spine`
  relies on this. Grid cells in one row share a height and in one column a width, so a tall shape
  (cylinder, oval) stretches its neighbours. Arrows between grid cells, and arrows from outside into a grid cell, are straight
  lines that ignore boxes. Only connect cells that end up adjacent.
- **Self-loops** render badly. Say it in the node's second line instead ("linked to equivalents by
  X").
- **Container labels at top-left** can collide with an arrow entering the container there. Remove a
  redundant arrow or regroup.
- **Disconnected pieces** are placed side by side and make wide diagrams. Use a grid to stack them.
- **A free-floating note** (title, key, caption) is a disconnected piece too. Pin it with
  `near: top-center` or `near: bottom-center` so it does not widen the diagram. The kit's
  `title` and `key` options do this.
- **Lookup boxes** linked with `ref` arrows land in the layer above their consumer and can read as
  part of the main flow. Keep them `store`-coloured and say so in the key.
- **Diamonds** (`decision`) are about twice as wide as their text, so a 35-character question makes
  an 800 px diamond. Split the question over two lines (title and second line). Decision labels
  are plain centred text, not markdown, so both lines are bold.
- **Several classes** on one node work as `class: [event; risk]`; later classes override earlier
  ones. The kit writes this for `"terminator risk"`.
- **Putting the main path in a container** to keep it together does not work: ELK routes every
  arrow that crosses the container border around the outside and the result is far worse.
- **State machines and other graphs with loops**: ELK routes every back-arrow as a right-angled
  track, so 9 states with 14 labelled transitions came out as a 1,767 x 459 strip with arrows 20 px
  apart (`right`) or with labels colliding on long vertical runs (`down`). dagre (`"engine":
  "dagre"`) gave 657 x 1,130 with even spacing and curved arrows. D2 exposes `nodesep` and
  `edgesep` for dagre (the kit sets 70 and 40); there is no rank-spacing flag.
- **The key** is a container pinned with `near: center-right` (beside) or `near: bottom-center`
  (below), holding a grid of sample and text cells. `near: top-right` puts it above the diagram,
  not beside it. Sample shapes smaller than about 40 x 24 stop being recognisable. Arrow samples
  are text glyphs: a real arrow inside a grid cell stretches to fill the cell.
- **Edge labels between grid cells** (used by `spine(carries=...)`) are drawn on the straight
  arrow; the gap between cells must be wide enough for the label, which `spine` sets.
- **Shapes that look standard but are not**: D2's `oval` is an ellipse; the flowchart terminator
  is a box with fully rounded ends, which the kit draws as a rectangle with `border-radius: 999`.
  D2's `step` is a chevron, not the flowchart's predefined-process box. A `double-border` circle
  draws a ring, not the UML bullseye; the kit's `final_marker()` uses the "◉" glyph, which works as
  an arrow target.
- **`c4-person`** sizes its head to its width: a long label gives a giant head that stretches
  its whole grid row. The kit fixes the size (150 x 110 for short labels). D2 also has a minimum
  width for it, so in the key it is drawn as a glyph.
- **C4 support** (D2 0.7+): `shape: c4-person`, theme 303 ("C4"), `d2-legend`, and layers for
  zooming between levels. **Crow's-foot ER**: `sql_table` with `cf-one`, `cf-many`,
  `cf-one-required`, `cf-many-required` arrowheads.
- **Grid rows share a height**: a cylinder sample (D2 draws it at least about 58 px tall) makes
  every other sample in that key row as tall.
- **ELK options**: D2 exposes only `algorithm`, `nodeNodeBetweenLayers`, `edgeNodeBetweenLayers`,
  `padding` and `nodeSelfLoop`. There is no knob for "keep this path straight"; use `spine`.

## Spacing

`d2kit.D2_FLAGS` tightens ELK's defaults (`--elk-nodeNodeBetweenLayers`, `--elk-edgeNodeBetweenLayers`,
`--elk-padding`). The top padding leaves room for container titles; do not drop it below about 44.
These are global settings. Do not tune them per diagram.

## Output

- SVG embeds its own fonts and is the file to publish. Two-line labels are HTML inside the SVG
  (`foreignObject`), so tools such as `rsvg-convert` drop them; use D2's own PNG export.
- PNG export uses a headless Chromium that D2 downloads on first use (about 150 MB). Pass
  `png=False` to `build` to skip it, then check the SVG in a browser instead.
- D2 writes files with mode 0600; the kit resets them to 0644.
- Importing the kit would leave a `__pycache__` in the skill folder; the kit removes its own. Set
  `sys.dont_write_bytecode = True` at the top of a build script to keep the project clean too.
- Give the root a solid fill (the kit does). A transparent background shows as black in some
  viewers, hiding black text.

## Checking a page locally

Headless Chrome cannot go narrower than about 500 px, so a `--window-size=400,...` screenshot is
misleading. For a phone-width check, load the page in a 400 px `<iframe>` inside a wrapper page and
screenshot that.
