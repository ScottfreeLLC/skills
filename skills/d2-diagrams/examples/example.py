"""Worked examples: a pipeline with a straight main path, and a state machine generated from data.
Run: python3 example.py /some/output/dir"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # in a project: the kit's absolute path
from d2kit import build, initial, link, plain, spine  # noqa: E402

# --- 1. A flow with exceptions: the main path is a straight line, each exception hangs off its cause.
# Shape says what kind of thing each node is (process, queue, store, event, external party);
# colour says its status (risk = lost or refused, hold = waiting on someone).
MAIN = [
    ("shop", "Web shop", "sends the order", "external"),
    ("api", "Order API", "validates the order", "process"),
    ("queue", "orders", "queue, kept 7 days", "queue"),
    ("worker", "Fulfilment worker", "reserves stock, charges card", "process"),
    ("db", "Orders", "Postgres", "store"),
]
# What is passed along each main arrow: in a data flow the arrows are the data.
CARRIES = ["order request", "validated order", "order message", "paid order"]
# Each side entry ends with the label for the arrow that leaves the main path there.
SIDE = {
    "api": [("invalid", "Order refused", "shopper is told why", "event risk", "invalid order")],
    "worker": [("retry", "Card declined", "retried for 3 days", "event hold", "failed charge"),
               ("cancel", "Order cancelled", "after 3 days", "event risk", "still failing")],
}


def orders(direction):
    return spine(MAIN, SIDE, direction, carries=CARRIES)


# --- 2. A state machine: read it from the code, never retype it. (from, to): what triggers the move.
TRANSITIONS = {("draft", "review"): "author submits", ("review", "draft"): "reviewer rejects",
               ("review", "approved"): "reviewer approves", ("approved", "published"): "timer, 09:00"}


def states(direction):
    names = list(dict.fromkeys(s for pair in TRANSITIONS for s in pair))
    ends = [s for s in names if not any(a == s for a, _ in TRANSITIONS)]
    start = names[0]  # the table lists the normal path first; a state with arrows back into it can still be the start
    lines = [f"direction: {direction}"]
    lines += [plain(s, s.capitalize(), "final" if s in ends else "state") for s in names]
    lines.append(initial(start))
    # every transition carries its trigger: in a state machine the triggers are the events
    lines += [link(a, b, trigger, "dashed" if trigger.startswith("timer") else "flow") for (a, b), trigger in TRANSITIONS.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "diagrams"
    ok = build({
        "1-orders": (orders, ("down", "right"), {
            "title": "What happens to an order?",
            "key": [("external", "outside our system"), ("process", "service or job"), ("queue", "queue"), ("store", "stored data"),
                    ("event risk", "order lost or refused"), ("event hold", "waiting")],
            "arrows": [("flow", "the order moving forward"), ("warn", "leaves the main path")]}),
        "2-states": (states, ("down", "right"), {
            "title": "How an article gets published",
            "engine": "dagre",   # graphs with loops: curved arrows, even spacing
            "key": [("initial", "where an article starts"), ("state", "state"), ("final", "end state")],
            "arrows": [("flow", "a person triggers the move"), ("dashed", "a timer triggers the move")]}),
    }, out)
    sys.exit(0 if ok else 1)
