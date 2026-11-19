"""Worked examples: a data-flow diagram with a straight main path, and a UML state machine
generated from data. Run: python3 example.py /some/output/dir"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # in a project: the kit's absolute path
from d2kit import build, final_marker, initial, link, plain, spine  # noqa: E402

# --- 1. A data-flow diagram (Yourdon/DeMarco): processes, stores, queues and the people or systems
# outside, joined by arrows that are the data. No decisions or start/stop symbols: those belong in a
# flowchart. The main path is a straight line; data leaving it hangs off the step that sends it.
MAIN = [
    ("shop", "Web shop", "where the shopper orders", "external"),
    ("api", "Order API", "validates the order", "process"),
    ("queue", "orders", "queue, kept 7 days", "queue"),
    ("worker", "Fulfilment worker", "reserves stock, charges card", "process"),
    ("db", "Orders", "Postgres", "store"),
]
# What is passed along each main arrow: in a data flow the arrows are the data.
CARRIES = ["order request", "validated order", "order message", "paid order"]
# Each side entry ends with the label for the arrow that leaves the main path there: the data.
SIDE = {
    "api": [("shopper", "Shopper", "sees why it was refused", "external", "refusal reason")],
    "worker": [("bank", "Card processor", "outside our system", "external", "charge request")],
}


def orders(direction):
    return spine(MAIN, SIDE, direction, carries=CARRIES, side_cls="flow")   # one arrow style in a data flow


# --- 2. A state machine: read it from the code, never retype it. (from, to): what triggers the move.
TRANSITIONS = {("draft", "review"): "author submits", ("review", "draft"): "reviewer rejects",
               ("review", "approved"): "reviewer approves", ("approved", "published"): "timer, 09:00"}


def states(direction):
    names = list(dict.fromkeys(s for pair in TRANSITIONS for s in pair))
    ends = [s for s in names if not any(a == s for a, _ in TRANSITIONS)]   # UML: a state, then the bullseye
    start = names[0]  # the table lists the normal path first; a state with arrows back into it can still be the start
    lines = [f"direction: {direction}"]
    lines += [plain(s, s.capitalize(), "state") for s in names]
    lines.append(initial(start))
    lines += [final_marker(s) for s in ends]
    # every transition carries its trigger: in a state machine the triggers are the events
    lines += [link(a, b, trigger) for (a, b), trigger in TRANSITIONS.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "diagrams"
    ok = build({
        "1-orders": (orders, ("down", "right"), {
            "title": "What data moves when an order is placed?", "notation": "dataflow",
            "key": [("external", "person or system outside ours"), ("process", "service or job"),
                    ("queue", "queue (convention)"), ("store", "stored data")],
            "arrows": [("flow", "data, named on the arrow")]}),
        "2-states": (states, ("down", "right"), {
            "title": "How an article gets published", "notation": "state",
            "engine": "dagre",   # graphs with loops: curved arrows, even spacing
            "key": [("initial", "where an article starts"), ("state", "state"), ("end", "where it stops")],
            "arrows": [("flow", "a move, labelled with what triggers it")]}),
    }, out)
    sys.exit(0 if ok else 1)
