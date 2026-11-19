"""Decision flow drawn from a table and checked against the real function.

A function body of if/else has no registry to import. Write the tree once as a table, draw from
it, and walk the same table against the real function on boundary cases before rendering. A
swapped yes/no arrow is hard to spot by eye and easy to catch this way.

Run: python3 decision_flow.py /some/output/dir
"""
import itertools
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # in a project: the kit's absolute path
from d2kit import build, link, node  # noqa: E402


def decide(amount, days, vip):  # stand-in for the function you import from the project
    if days > 30:
        return "reject"
    if vip:
        return "approve"
    return "review" if amount > 100 else "approve"


# id: (question, second line or None, test on the inputs, where "yes" goes, where "no" goes)
QUESTIONS = {
    "late": ("Bought more than 30 days ago?", None, lambda c: c["days"] > 30, "reject:past the 30-day limit", "vip"),
    "vip": ("VIP customer?", None, lambda c: c["vip"], "approve:VIP customers skip review", "big"),
    "big": ("Refund of more", "than 100.00?", lambda c: c["amount"] > 100, "review:amount over 100.00", "approve:small amount"),
}
START = "late"
# Flowchart convention: the start and each end are ovals, each question is a diamond.
OUTCOMES = {"approve": ("Approved automatically", "event good"), "review": ("Sent to a person", "event hold"),
            "reject": ("Refused", "event risk")}


def walk(case):
    at = START
    while at in QUESTIONS:
        _, _, test, yes, no = QUESTIONS[at]
        at = yes if test(case) else no
    return at.split(":")[0]


def check():
    cases = [dict(amount=a, days=d, vip=v) for a, d, v in itertools.product((99.99, 100, 100.01), (30, 31), (True, False))]
    bad = [c for c in cases if walk(c) != decide(**c)]
    assert not bad, f"diagram disagrees with the code on {bad[:3]}"
    return len(cases)


def flow(direction):
    lines = [f"direction: {direction}", node("start", "Refund request", None, "event"), link("start", START)]
    n = 0
    for qid, (question, sub, _, yes, no) in QUESTIONS.items():
        lines.append(node(qid, question, sub, "decision"))
        for answer, target in (("yes", yes), ("no", no)):
            if target in QUESTIONS:
                lines.append(link(qid, target, answer))
            else:  # one outcome box per exit, each saying why: shared outcome boxes cause long crossing arrows
                kind, why = target.split(":")
                n += 1
                title, cls = OUTCOMES[kind]
                lines += [node(f"o{n}", title, why, cls), link(qid, f"o{n}", answer)]
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"checked {check()} cases against the function")
    out = sys.argv[1] if len(sys.argv) > 1 else "diagrams"
    opts = {"title": "When is a refund approved?",
            "key": [("event", "start"), ("decision", "yes / no question"), *[(c, t) for t, c in OUTCOMES.values()]]}
    sys.exit(0 if build({"refund-flow": (flow, ("down",), opts)}, out) else 1)
