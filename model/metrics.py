"""Score typed exact spans and the characters a masking action would cover."""

from .fixtures import KINDS, Span


TAGS = ("O", *(tag for kind in KINDS for tag in (f"B-{kind}", f"I-{kind}")))


def overlapping_tokens(span, offsets):
    return [index for index, (start, end) in enumerate(offsets)
            if start < end and start < span.end and end > span.start]


def token_labels(gold, offsets):
    labels = [-100 if start == end else 0 for start, end in offsets]
    unaligned = 0
    for span in gold:
        indexes = overlapping_tokens(span, offsets)
        if not indexes or offsets[indexes[0]][0] != span.start or offsets[indexes[-1]][1] != span.end:
            unaligned += 1
        for position, index in enumerate(indexes):
            if labels[index] != 0:
                raise ValueError("A token crosses two annotated spans")
            prefix = "B-" if position == 0 else "I-"
            labels[index] = TAGS.index(prefix + span.kind)
    return labels, unaligned


def decode(ids, offsets):
    spans = []
    active = None
    for index, (start, end) in zip(ids, offsets, strict=True):
        tag = TAGS[index] if start < end else "O"
        kind = tag[2:]
        if active and (tag == "O" or tag.startswith("B-") or kind != active.kind):
            spans.append(active)
            active = None
        if tag != "O":
            active = Span(active.start if active else start, end, kind)
    if active:
        spans.append(active)
    return spans


def covered(spans):
    return {index for span in spans for index in range(span.start, span.end)}


def rates(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0}


def evaluate(rows, predictions):
    counts = {kind: [0, 0, 0] for kind in KINDS}
    unmasked, overmasked, exposed_rows, controls_masked, controls = 0, 0, 0, 0, 0
    for row, guessed in zip(rows, predictions, strict=True):
        gold, guessed = set(row.gold), set(guessed)
        for spans, column in ((gold & guessed, 0), (guessed - gold, 1), (gold - guessed, 2)):
            for span in spans:
                counts[span.kind][column] += 1
        expected, masked = covered(gold), covered(guessed)
        leaked = len(expected - masked)
        unmasked += leaked
        overmasked += len(masked - expected)
        exposed_rows += bool(leaked)
        controls += not gold
        controls_masked += not gold and bool(masked)
    return {
        "micro": rates(*(sum(column) for column in zip(*counts.values(), strict=True))),
        "per_type": {kind: rates(*values) for kind, values in counts.items()},
        "unmasked_private_characters": unmasked,
        "overmasked_public_characters": overmasked,
        "rows_with_unmasked_private_characters": exposed_rows,
        "negative_controls": controls,
        "negative_controls_overmasked": controls_masked,
    }
