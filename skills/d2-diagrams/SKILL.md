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
a box with rounded ends is where a flowchart starts or stops. A reader who has seen any flowchart already knows these, so the shapes tell
them what kind of thing each node is before they read a word. Rounded boxes that differ only in
colour make them ask "which of these is data and which is a process?". Second, **a main path the
eye can follow**: it starts where reading starts (top or left) and runs in one line, with
exceptions hanging off it.

Both come from using a **standard notation for each kind of diagram** rather than one invented
vocabulary for all of them: ISO 5807 flowchart symbols for decision logic, data-flow diagram rules
for pipelines, UML for state machines and sequences, the C4 model for architecture. No single
template covers every type, but each type has one, and the kit enforces it (see "Notation").

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
5. **Pick the notation, then name the kind of each node and the main path** before writing any
   D2. Which question does the diagram answer: what decides (flowchart), what data moves
   (data flow), what states a thing goes through (state machine), what the system is made of (C4)?
   Then for every node: which of that notation's kinds is it? Which sequence of nodes is the
   normal case? See "Notation" and "The main path".
6. **Decide where the image will live.** On a page you control, the text around it carries the
   title and key. Anywhere else (wiki, slide, email, README) the image stands alone, so give it a
   title and key inside the image with the `options` shown below.
7. **Build, then look at every PNG** with the Read tool. A successful build only means D2 ran.
   Ask of each image the C4 review questions, which apply to every notation: does it have a title
   naming the type and scope? A key explaining every shape, colour, border and line style used?
   Could a newcomer say what kind of thing every node is? Does every arrow say what moves or what
   triggers it, in the direction it points? Then: does the main path start at the top or left and
   run straight? Is the spacing even, or is one direction cramped?
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
        node("shop", "Web shop", "where orders come from", "external"),
        node("api", "Order API", "validates the order", "process"),
        node("db", "Orders", "Postgres", "store"),
        link("shop", "api", "order request"), link("api", "db", "valid order"),
        link("api", "shop", "refusal reason", "warn"),
    ])

build({"1-flow": (flow, ("down", "right"), {
    "notation": "dataflow",                                # the standard this diagram follows
    "title": "How an order is saved",                      # becomes "Data flow: How an order is saved"
    "key": [("external", "system outside ours"), ("process", "our code"), ("store", "stored data")],
    "arrows": [("flow", "data on the main path"), ("warn", "data sent back")],
})}, out_dir="docs/diagrams")
```

`build` renders each listed direction as it would appear on the page (a wider diagram is shrunk to
the page width), rejects flat strips and thin towers when a better-proportioned layout exists,
and keeps the one that takes the least height. Pass both `("down", "right")` unless the direction
carries meaning. It warns when the text would be too small at page width, when the result is
taller than 2000 px, or when the best layout is still a strip or a tower; each means "simplify,
split, or try the other engine". A grid diagram can be a function with no argument.

Options: `notation` (see below), `title`, `subtitle`, `key`, `arrows`, `note`, `key_at` (`"right"` or `"below"`; by default
the key goes beside a tall diagram when the page has room and below otherwise), and `engine`
(`"elk"`, the default, draws right-angled arrows and suits flows and trees; `"dagre"` draws curved
arrows and spaces graphs with loops, such as state machines, far more evenly).

### Notation: pick the standard, then the shapes

Set `"notation"` on every diagram. The build then fails on a shape that notation does not have
(a decision diamond in a data flow, a terminator in a C4 diagram), warns about unlabelled arrows
and about more than six processes on one data flow, and prefixes the title with the notation
("Data flow: ...") unless it already names it.

| Notation | Answers | Kinds it allows | Arrow labels | Standard |
|---|---|---|---|---|
| `flowchart` | what decides? | `terminator`, `process`, `decision`, `io`, `doc`, `store` | yes / no on each decision exit | ISO 5807 (ANSI X3.5 symbols) |
| `dataflow` | what data moves? | `external`, `person`, `process`, `store`, `queue`, `doc` | every arrow names its data | data-flow diagram rules (Yourdon/DeMarco, Gane & Sarson) |
| `state` | what states does it pass through? | `state`, `initial()`, `final_marker()`, `decision` (choice) | the trigger, `trigger [guard] / effect` | UML 2.5.1 state machine |
| `c4` | what is the system made of? | `person`, `external`, `process`, `store`, `queue` | intent plus protocol, one direction | C4 model (system context, container) |

For a request flowing between parts over time, use D2's own `shape: sequence_diagram` (UML
sequence notation) instead of the kit's nodes. For a slide-sized overview there is no standard;
use a C4 system-context diagram (the system as one box, people and outside systems around it, about
5–9 elements) or a top-level data flow.

The kinds and the symbol each draws:

| Kind | Shape | Use it for | Source |
|---|---|---|---|
| `process` | rectangle | work the system does: a service, job, step, function | flowchart, data flow |
| `decision` | diamond | a yes/no question; in UML a choice | flowchart, UML |
| `terminator` | box with fully rounded ends | the start and each end of a flowchart, named for the outcome | ISO 5807 |
| `io` | parallelogram | data read in or written out in a flowchart | ISO 5807 |
| `store` | cylinder | data at rest: database, table, bucket, file store | flowchart (disk), BPMN, C4 |
| `queue` | horizontal cylinder | data in transit: topic, stream, queue | convention: no standard has a queue symbol; say so in the key |
| `doc` | document | a file, report or message someone reads | flowchart |
| `external` | square-cornered box | a person, team or system outside the thing described | data flow |
| `person` | head and shoulders | a person or role, in C4 diagrams; keep the label short | C4 convention |
| `state` | rounded box | a state, including named end states ("Published") | UML |
| `initial("first")` / `final_marker("last")` | black dot / bullseye | where the machine starts / stops | UML |

The old `event` kind (an ellipse used for starts, ends, triggers and failures alike) now draws a
terminator. Do not use it for things that happen mid-flow: in a flowchart that is a process step;
in a data flow it is a labelled arrow or an external entity that receives the data.

In C4 diagrams put the element's type and technology on the second line, in brackets:
`node("api", "Order API", "[Container: Python] validates orders", "process")`. C4 also asks for a
technology on arrows between containers ("orders, JSON over HTTPS").

**Colour is not part of any of these standards.** UML assumes black on white; C4 and BPMN allow any
colour scheme as long as it is explained. So a status colour is a project convention: list it in the
key, and make the status readable without colour too (the label says "Refused", "Needs review").

| Status | Meaning |
|---|---|
| (none) | normal; each kind has its own quiet default colour |
| `risk` | blocked, failed, lost, refused |
| `hold` | waiting on a person, pending, needs review, stale |
| `good` | approved, succeeded |
| `focus` | the thing being followed or tested |

Pick the kind by asking what the node is, not how important it is. A Kafka topic is a `queue`, a
warehouse table is a `store`, the team reading a dashboard is `external`. If a diagram ends up with
only one shape, data and outside parties have probably been folded into process boxes.

The key explains every shape, status colour, border and arrow style the diagram uses, because a
convention only helps readers who can check it. In `key`, list each kind once with a plain-words
label ("Kafka topic", "service or job"), then each status. In `arrows`, list each arrow style used
(`[("flow", "moved by support staff"), ("dashed", "automatic timer")]`). The kit draws it as one
boxed legend with a small sample beside each line.

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

SIDE = {"api": [("shopper", "Shopper", "told why it was refused", "external", "refusal reason")],
        "worker": [("bank", "Card processor", "outside our system", "external", "charge request")]}
CARRIES = ["validated order", "order message"]         # one label per main arrow: what is passed

def orders(direction):
    return spine(MAIN, SIDE, direction, carries=CARRIES)
```

`spine` draws MAIN as a straight line and each SIDE chain beside the step that causes it.
`carries` names what moves along each main arrow, and the fifth item of a SIDE entry names the
data that leaves the path there. Use it
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

- **Flow or pipeline (`dataflow`):** `spine` when it is one sequence with exceptions. Alternate the
  kinds honestly: process, then the queue or store it writes to, then the next process; outside
  systems and people are `external`. Data leaving the path goes to a store or an external entity,
  never to an outcome box. No decisions: if the reader needs the logic, draw a separate flowchart.
  At most about six processes per diagram; for more, draw a top-level diagram and one diagram per
  part ("levels").
- **Decision logic (`flowchart`):** a `terminator` for the start, `decision` diamonds with yes/no
  arrows, and a `terminator` for each end, coloured `good`, `hold` or `risk`. Give every exit its
  own outcome with the reason on the second line; one shared outcome causes long crossing arrows.
  Diamonds grow fast with text: keep questions under about 20 characters per line and put the
  rest on the second line.
- **State machine (`state`):** generate from the transition table. `state` for each state,
  `initial("first_state")` for the black start dot and `final_marker("last_state")` for the
  bullseye after each end state (key entries: `("initial", "where it starts")`,
  `("end", "where it stops")`), and the trigger on every arrow.
  Set `"engine": "dagre"` and offer `("down", "right")`: state machines have loops, and the default
  engine squeezes their back-arrows into tight parallel tracks, while dagre spaces them evenly
  with curved arrows.
- **Architecture (`c4`):** a system-context diagram (people, the system, outside systems) or a
  container diagram (the system's apps and data stores). Title it "System context diagram for X"
  or "Container diagram for X"; types and technologies in brackets on the second line.
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
| Build fails: "'decision' is not part of a data-flow diagram" | The diagram mixes notations: move the logic to a flowchart, or pick the notation that fits the question |
| A person's head is huge and stretches its row | Shorten the person's label (about 14 characters a line), or use `external` |
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
