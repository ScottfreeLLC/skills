---
name: d2-diagrams
description: Create professional technical diagrams (architecture, data flow, pipelines, decision flowcharts, schemas, state machines, run order, comparisons) as SVG and PNG using D2 with automatic layout, generated from code where possible. Use this whenever the user asks for a diagram, a figure, a visual of how something works, "draw this", "diagram the system", or a diagram page, and whenever you are about to reach for Mermaid, hand-written SVG, or ASCII boxes for anything bigger than four boxes. Not for statistical charts, UI mockups or illustrations.
license: Apache-2.0
---

# D2 diagrams

Describe what is in the diagram. Let D2 decide where it goes.

This skill exists because two other approaches failed in practice. Mermaid with whole sentences in
the boxes produced "a jumble of words". A hand-positioned tool produced nice pictures but needed a
patch for every overlap. What worked: short labels, a plain list of boxes and links, D2's layout
engine, and looking at every image before showing it.

Two things make a reader trust a diagram at first glance, and a diagram that builds cleanly can
still miss both. First, **standard notation**: a diamond is a decision, a cylinder is stored data,
an oval is an event. A reader who has seen any flowchart already knows these, so the shapes tell
them what kind of thing each node is before they read a word. Rounded boxes that differ only in
colour make them ask "which of these is data and which is a process?". Second, **a main path the
eye can follow**: it starts where reading starts (top or left) and runs in one line, with
exceptions hanging off it.

Three more things decide whether a reader finds the diagram useful. **Arrows say what moves**: in
a data flow the arrows are the data, so each one names what is passed ("raw events", "Parquet
files"); in a state machine each names what triggers the move. **The picture has room**: boxes and
arrows are spaced evenly in both directions, not squeezed into a flat strip or a thin tower.
**The key is a proper legend**: boxed, with a small sample of each shape and arrow, placed where
the diagram has space for it.

## Workflow

1. **Check the tool.** Run `python3 <skill>/scripts/d2kit.py`. It prints the D2 version, whether a
   browser for PNG export is already cached, and the kit's absolute path. If D2 is missing, or PNG
   export would download a browser, ask before installing (or pass `png=False`).
2. **Decide the set.** Each diagram answers one question a reader would ask ("how is one request
   handled?", "what may link to what?", "in what order do I run this?"). Write the question down
   first; it becomes the title. Three to seven diagrams usually cover a system. One diagram that
   tries to answer everything is the main cause of bad diagrams.
3. **Find what the code already defines.** If a registry, enum, config, schema or route table holds
   the structure, generate the diagram from it by importing or parsing it. Generated diagrams
   cannot drift from the code. For logic that lives in a function body, write the tree as a table
   and check it against the function (see `examples/decision_flow.py`). Hand-describe only what
   exists nowhere else.
4. **Write a build script** next to the output (for example `docs/diagrams/src/build.py`). Put the
   kit's absolute path (printed in step 1) on `sys.path`; the relative path in the examples only
   works inside the skill folder.
5. **Name the kind of each node and the main path** before writing any D2. For every node: is it
   a process, a decision, an event, stored data, a queue, a state, or something outside the
   system? Which sequence of nodes is the normal case? See "Notation" and "The main path".
6. **Decide where the image will live.** On a page you control, the text around it carries the
   title and key. Anywhere else (wiki, slide, email, README) the image stands alone, so give it a
   title and key inside the image with the `options` shown below.
7. **Build, then look at every PNG** with the Read tool. A successful build only means D2 ran.
   Ask of each image: could a newcomer say what kind of thing every node is from its shape and
   the key? Does the main path start at the top or left and run straight? Does every arrow say
   what moves or what triggers it? Is the spacing even, or is one direction cramped?
8. **Fix by changing what the diagram says**, never where things sit. See "When it looks wrong".
9. **Report** the files, the one-line rebuild command, and anything you could not verify.

## Writing a diagram

```python
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/absolute/path/to/d2-diagrams/scripts")
from d2kit import node, plain, link, group, grid, spine, initial, build

def flow(direction):
    return "\n".join([
        f"direction: {direction}",
        node("api", "API", "validates the request", "process"),
        node("db", "Orders", "Postgres", "store"),
        node("bad", "Request invalid", "caller gets a 400", "event risk"),
        link("api", "db", "valid order"), link("api", "bad", "invalid order", "warn"),
    ])

build({"1-flow": (flow, ("down", "right"), {
    "title": "How an order is saved",                      # optional: for stand-alone images
    "key": [("process", "our code"), ("store", "stored data"), ("event risk", "request refused")],
    "arrows": [("flow", "main path"), ("warn", "leaves the main path")],
})}, out_dir="docs/diagrams")
```

`build` renders each listed direction as it would appear on the page (a wider diagram is shrunk to
the page width), rejects flat strips and thin towers when a better-proportioned layout exists,
and keeps the one that takes the least height. Pass both `("down", "right")` unless the direction
carries meaning. It warns when the text would be too small at page width, when the result is
taller than 2000 px, or when the best layout is still a strip or a tower; each means "simplify,
split, or try the other engine". A grid diagram can be a function with no argument.

Options: `title`, `subtitle`, `key`, `arrows`, `note`, `key_at` (`"right"` or `"below"`; by default
the key goes beside a tall diagram when the page has room and below otherwise), and `engine`
(`"elk"`, the default, draws right-angled arrows and suits flows and trees; `"dagre"` draws curved
arrows and spaces graphs with loops, such as state machines, far more evenly).

### Notation: shape is the kind of thing, colour is its status

The class you pass to `node` is a kind, optionally followed by a status: `"store"`,
`"event risk"`, `"queue hold"`. The kinds follow the conventions readers already know (flowchart
symbols, data-flow and architecture diagrams, UML state machines):

| Kind | Shape | Use it for |
|---|---|---|
| `process` | rectangle | work the system does: a service, job, step, function |
| `decision` | diamond | a yes/no question or a guard |
| `event` | oval | something that happens: the start, an end or outcome, a trigger, a failure |
| `store` | cylinder | data at rest: database, table, bucket, file store |
| `queue` | horizontal cylinder | data in transit: topic, stream, queue |
| `doc` | document | a file, report or message someone reads |
| `external` | square-cornered box | a person, team or system outside the thing being described |
| `state` / `final` | rounded box / double border | a state in a state machine / an end state |

| Status | Meaning |
|---|---|
| (none) | normal; each kind has its own quiet default colour |
| `risk` | blocked, failed, lost, refused |
| `hold` | waiting on a person, pending, needs review, stale |
| `good` | approved, succeeded |
| `focus` | the thing being followed or tested |

Pick the kind by asking what the node is, not how important it is. "Batch over 1 MB is rejected"
is something that happens, so it is an `event` (with status `risk`), not a process. A Kafka topic
is a `queue`, a warehouse table is a `store`, the team reading a dashboard is `external`. If a
diagram ends up with only one shape, check whether data and events have been folded into process
boxes; pulling them out is usually what makes the picture make sense.

The key explains every shape, status colour and arrow style the diagram uses, because a
convention only helps readers who can check it. In `key`, list each kind once with a plain-words
label ("Kafka topic", "service or job"), then each status. In `arrows`, list each arrow style used
(`[("flow", "moved by support staff"), ("dashed", "automatic timer")]`). The kit draws it as one
boxed legend with a small sample beside each line. A key that explains colours only leaves the
shapes as decoration; a loose row of labels under the picture reads as an afterthought.

Arrow classes: `flow` (default), `warn` (leaves the main path), `ref` (lookup, dotted), `strong`
(the link that matters), `dashed` (automatic, timed, or optional), `accent` (a second actor). Pass
`palette=` to `build` to match a project's colours.

### The main path

A layered layout gives every branch the same weight, so a flow with side branches drifts sideways
at each one and can end up starting in the top-right corner. Decide which nodes are the normal
case and keep them in one line:

```python
MAIN = [("api", "Order API", "validates the order", "process"),
        ("queue", "orders", "queue, kept 7 days", "queue"),
        ("worker", "Fulfilment worker", "charges the card", "process")]

SIDE = {"api": [("invalid", "Order refused", "shopper is told why", "event risk", "invalid order")],
        "worker": [("declined", "Card declined", "retried for 3 days", "event hold", "failed charge")]}
CARRIES = ["validated order", "order message"]         # one label per main arrow: what is passed

def orders(direction):
    return spine(MAIN, SIDE, direction, carries=CARRIES)
```

`spine` draws MAIN as a straight line and each SIDE chain beside the step that causes it.
`carries` names what moves along each main arrow, and the fifth item of a SIDE entry names what
leaves the path there. Use it
whenever a flow is one sequence plus exceptions (pipelines, request paths, run order with failure
points). It suits up to about twelve main steps going down or six going right. For flows that
truly branch and rejoin (decision trees, state machines) use `direction` with `node` and `link`,
and declare the normal-case nodes and links first.

### Labels

A box holds a short bold name and at most one short second line (aim for under 40 characters).
Explanations belong in the text around the figure. If a label needs a sentence, the box is doing
two jobs: split it, or move the sentence to the caption. Use the reader's words; put a code
identifier on the second line only when the reader will search for it.

Arrows carry the story, so label them. In a data flow, name what is passed along each arrow in
two or three words ("raw batches", "valid events", "hourly Parquet files"): a reader asking "what
goes from this box to that one?" should find the answer on the arrow, not have to infer it from
the box names. In a state machine, the label is the event that causes the move (who or what moves
the thing). Label every arrow even when many share a label; colour or dash them by actor as well
if that helps, and list the styles under `arrows` in the key. The only arrows that go unlabelled
are yes/no-free steps in a flowchart, such as the arrow from the start oval.

Draw only what the source states. If the notes say a topic is kept for three days, that is a
second line on the topic, not a new "data lost after 3 days" failure node. An inferred node looks
exactly as authoritative as a documented one, and the reader cannot tell them apart.

### Choosing a structure for the content

- **Flow or pipeline:** `spine` when it is one sequence with exceptions. Alternate the kinds
  honestly: process, then the queue or store it writes to, then the next process. Without side
  branches, `direction` plus `group` for stages also works; merge steps until one direction is at
  most about eight layers deep.
- **Decision logic (flowchart):** an `event` oval for the start, `decision` diamonds with yes/no
  arrows, and an `event` oval for each end, coloured `good`, `hold` or `risk`. Give every exit its
  own outcome with the reason on the second line; one shared outcome causes long crossing arrows.
  Diamonds grow fast with text: keep questions under about 20 characters per line and put the
  rest on the second line.
- **State machine (UML):** generate from the transition table. `state` for each state, `final` for
  end states, `initial("first_state")` for the black start dot (give it a key entry too:
  `("initial", "where it starts")`), and the trigger on every arrow.
  Set `"engine": "dagre"` and offer `("down", "right")`: state machines have loops, and the default
  engine squeezes their back-arrows into tight parallel tracks, while dagre spaces them evenly
  with curved arrows.
- **Schema or "what links to what":** generate from the code; merge arrows that share both ends and
  kind into one arrow with a two-line label.
- **A list of parallel routes or variants:** one small `group` per route, laid out in a grid
  (`grid-columns: N` at the root, `grid-columns: 1` inside each group).
- **Run order with inputs:** `grid(...)` with every arrow joining neighbouring cells.

## When it looks wrong

| Symptom | Change |
|---|---|
| Too tall or too wide | Merge steps, drop arrow labels, or split into two diagrams |
| Text too small on the page | The diagram is wider than the page; same fixes |
| An arrow runs through a label or box | Remove a redundant arrow, or regroup |
| A label sits on another arrow | Drop the commonest label and explain it in the key |
| Flat strip, or arrows packed a few pixels apart | Loops in the graph: set `"engine": "dagre"`; else offer the other direction |
| Key far from the diagram or wider than it | Set `key_at` to `"right"` or `"below"`; shorten the key labels |
| Arrows with no labels | Name what is passed (flows) or what triggers the move (state machines) |
| Starts in a corner and steps sideways | Side branches are pulling the main path; use `spine` |
| Tall and thin, arrows bunched on one axis | Offer `"right"` as well, or `"engine": "dagre"` |
| Every node is the same shape | Kinds were not assigned; see "Notation" |
| Tangle around one box | That box has too many links; merge parallel arrows or split the diagram |
| Long arrows to a shared outcome | One outcome box per exit |
| Side-branch boxes sink far from their source | Drop the groups, or move the box into the group |
| Straight diagonal arrow across boxes | An arrow between non-neighbouring grid cells; reorder cells or drop the grid |

Never reach for coordinates, manual offsets or hand-edited SVG. If two structural changes do not
fix it, the diagram is answering more than one question.

## Where the image goes

- **A wiki, slide, doc or email:** hand over the PNG; it always renders. Give it a title and key.
- **A web page you control:** use `inline_svg(path, title)` and paste the markup into the HTML.
  Give the page the diagrams' paper colour. Put narrow figures beside their text and wide ones
  below it. Load a design skill (for example `frontend-design`) for the page itself, and
  screenshot it at desktop and phone width before publishing.
- **An SVG that other tools will process** (converters, static-site pipelines): build with
  `plain_labels=True`. The default two-line labels are HTML inside the SVG and some non-browser
  renderers drop them. Plain labels lose the bold-name styling.

## Reference

Read `references/d2-notes.md` when a build fails or D2 does something unexpected (reserved words,
grid fill order, markdown labels, placing notes, PNG export, tuning spacing).
