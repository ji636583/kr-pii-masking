"""Fit a linear BIO head on frozen KLUE-RoBERTa Base CPU features."""

import argparse
from dataclasses import dataclass
import json

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer

from .fixtures import Sample, make_splits, split_metadata
from .metrics import TAGS, decode, evaluate, token_labels

MODEL_ID = "klue/roberta-base"
MODEL_REVISION = "02f94ba5e3fcb7e2a58a390b8639b0fac974a8da"
DATA_SEED = 5090
BATCH_SIZE = 16


@dataclass
class EncodedSplit:
    features: torch.Tensor
    labels: torch.Tensor
    offsets: list[list[tuple[int, int]]]
    unaligned_spans: int


def encode(rows: list[Sample], tokenizer, encoder) -> EncodedSplit:
    inputs = tokenizer(
        [row.text for row in rows],
        padding=True,
        return_offsets_mapping=True,
        return_tensors="pt",
    )
    offsets = [
        [tuple(offset) for offset in document]
        for document in inputs.pop("offset_mapping").tolist()
    ]
    alignments = [
        token_labels(row.gold, positions)
        for row, positions in zip(rows, offsets, strict=True)
    ]
    labels, unaligned = zip(*alignments, strict=True)

    features = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = {key: value[start:start + BATCH_SIZE] for key, value in inputs.items()}
            features.append(encoder(**batch).last_hidden_state)
    return EncodedSplit(torch.cat(features), torch.tensor(labels), offsets, sum(unaligned))


def fit_head(train: EncodedSplit, hidden_size: int, epochs: int, seed: int):
    head = nn.Linear(hidden_size, len(TAGS))
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.008)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0] + [2.0] * (len(TAGS) - 1)))
    shuffler = torch.Generator().manual_seed(seed)
    epoch_losses = []

    for _ in range(epochs):
        losses = []
        batches = torch.randperm(len(train.labels), generator=shuffler).split(BATCH_SIZE)
        for indices in batches:
            optimizer.zero_grad()
            logits = head(train.features[indices])
            loss = criterion(logits.flatten(0, 1), train.labels[indices].flatten())
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        epoch_losses.append(sum(losses) / len(losses))

    return head.eval(), epoch_losses


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("expected an integer greater than zero")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=positive_int, default=1)
    parser.add_argument("--seed", type=int, default=5090)
    parser.add_argument("--threads", type=positive_int, default=4)
    parser.add_argument("--limit-per-split", type=positive_int)
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    splits = make_splits(DATA_SEED)
    rows = {name: splits[name][:args.limit_per_split] for name in ("train", "validation")}

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, use_fast=True)
    encoder = AutoModel.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, use_safetensors=True, add_pooling_layer=False,
    ).eval().requires_grad_(False)
    train = encode(rows["train"], tokenizer, encoder)
    validation = encode(rows["validation"], tokenizer, encoder)
    head, epoch_losses = fit_head(train, encoder.config.hidden_size, args.epochs, args.seed)

    with torch.no_grad():
        predictions = head(validation.features).argmax(dim=-1).tolist()
    spans = [
        decode(ids, offsets)
        for ids, offsets in zip(predictions, validation.offsets, strict=True)
    ]

    print(json.dumps({
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "data_seed": DATA_SEED,
        "head_seed": args.seed,
        "splits": split_metadata(rows),
        "unaligned_spans": {
            "train": train.unaligned_spans,
            "validation": validation.unaligned_spans,
        },
        "mean_batch_loss_by_epoch": epoch_losses,
        "validation": evaluate(rows["validation"], spans),
    }, indent=2))


if __name__ == "__main__":
    main()
