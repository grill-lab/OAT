import argparse
import json
import os
import random
import re

import jsonlines
import numpy as np
import torch
import tqdm
from pytorch_lightning import seed_everything
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.nn import CrossEntropyLoss
from transformers import AdamW, AutoModelForSeq2SeqLM, AutoTokenizer

from utils import Downloader, logger

annotations_file = "/shared/test_data/GRILL_intent_annotations.jsonl"

all_intents = [
    "next()",
    "previous()",
    "repeat()",
    "restart()",
    "chit_chat()",
    "select(int)",
    "step_select(int)",
    "search(query: string)",
    "start_task()",
    "no()",
    "yes()",
    "ASR_error()",
    "stop()",
    "pause()",
    "cancel()",
    "inform_capabilities()",
    "set_timer(span:string)",
    "show_more_results()",
    "show_requirements()",
    "show_more_details()",
    "answer_question()",
]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def create_contextual_intent_pair(annot):
    return (
        f"User: {annot['user']}\nSystem: {annot['system']}\nFunctions: {' | '.join(all_intents)}",
        f"<pad>{annot['annotation'] if 'annotation' in annot else None}</s>",
    )


def infinite_iterator(data):
    while True:
        for d in data:
            yield d


def UnifiedQA_intent_prediction(samples, model, batch_size=32, device="cpu"):
    """
    samples: [{system:..., user:...}]
    model
    """
    device = model.device
    task_question_chunks = chunks(samples, batch_size)
    predictions = []
    for chunk in task_question_chunks:
        batch_inp = []
        for sample in chunk:
            inp, _ = create_contextual_intent_pair(sample)
            batch_inp.append(inp)
        inputs = model.tokenizer(batch_inp, return_tensors="pt", padding=True).to(
            device
        )
        with torch.no_grad():
            output_ids = model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                num_beams=1,
            )
        generated_responses = model.tokenizer.batch_decode(
            output_ids, skip_special_tokens=True
        )
        predictions += generated_responses
    for i in range(len(samples)):
        samples[i]["intent_pred"] = (
            predictions[i].replace("<pad>", "").replace("</s>", "")
        )
    return samples


def eval_metrics(pretrained_name, base, samples, filtered_intents):
    # replace () and anything inside with empty string in intents
    intents = [re.sub(r"\([^)]*\)", "", intent) for intent in filtered_intents]

    wrong_generations = []
    for s in samples:
        if s["intent_pred"].split("(")[0] not in intents:
            wrong_generations.append(s["intent_pred"].split("(")[0])

    logger.info(f"Wrong generations: {wrong_generations}")

    filtered_samples = [s for s in samples if s["annotation"].split("(")[0] in intents]
    filtered_predictions = [s["intent_pred"].split("(")[0] for s in filtered_samples]
    filtered_labels = [s["annotation"].split("(")[0] for s in filtered_samples]

    cm = confusion_matrix(filtered_labels, filtered_predictions)
    f1 = f1_score(filtered_labels, filtered_predictions, average="macro")
    precision = precision_score(filtered_labels, filtered_predictions, average="macro")
    recall = recall_score(filtered_labels, filtered_predictions, average="macro")
    accuracy = accuracy_score(filtered_labels, filtered_predictions)

    # Print the total number of elements of each class
    print("\nTotal elements per class:")
    for i, intent in enumerate(intents):
        total_elements = np.sum(cm[i])
        print(f"{intent}: {total_elements}")

    # Print the number of misclassifications in every class
    print("\nMisclassifications per class:")
    for i, intent in enumerate(intents):
        misclassifications = np.sum(cm[i]) - cm[i, i]
        print(f"{intent}: {misclassifications}")

    # Print precision and recall for each class
    print("\nPrecision and Recall per class:")
    for i, intent in enumerate(intents):
        precision_class = precision_score(
            filtered_labels, filtered_predictions, labels=[intent], average=None
        )
        recall_class = recall_score(
            filtered_labels, filtered_predictions, labels=[intent], average=None
        )
        f1_class = f1_score(
            filtered_labels, filtered_predictions, labels=[intent], average=None
        )
        print(
            f"{intent}: Precision = {float(precision_class):.4f}, Recall = {float(recall_class):.4f},  F1 = {float(f1_class):.4f}"
        )

    print("\n------AVERAGE-------")
    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print(f"F1: {f1}")
    print(f"Accuracy: {accuracy}")

    # Create eval_results folder
    if not os.path.exists("eval_results"):
        os.makedirs("eval_results")

    with open(
        f'eval_results/{"_".join(pretrained_name.split("/"))}_{"_".join(base.split("/"))}.json',
        "w",
    ) as f:
        json.dump(
            {
                "model_name": pretrained_name,
                "base": base,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": accuracy,
            },
            f,
            indent=4,
        )

    return cm, recall, precision


def evaluate(model, pretrained_name, base, samples, predict_fn):
    """
    samples: [{system:, user:, annotation:}]
    predict_fn: fn([{sample}], model) -> [{sample+intent_pred}]
    """
    # get all gold intents from samples
    gold_intents = set([s["annotation"].split("(")[0] for s in samples])
    # remove empty intents
    gold_intents.discard("")

    samples = predict_fn(samples, model)
    [s["intent_pred"] for s in samples]
    [s["annotation"] for s in samples]

    confusion_matrix, precision, recall = eval_metrics(
        pretrained_name, base, samples, sorted(list(gold_intents))
    )


def train(args: argparse.Namespace) -> None:
    batch_size = args.batch_size
    seed = args.seed
    batch_accum = args.batch_accum
    grad_steps = args.grad_steps
    dev_steps = args.dev_steps
    only_eval = args.only_eval

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    base = "allenai/unifiedqa-t5-base"
    pretrained_name = "UQA_intent_model_1076"

    # get model path from the downloader
    downloader = Downloader()
    downloader.download([pretrained_name])
    model = AutoModelForSeq2SeqLM.from_pretrained(
        downloader.get_artefact_path(pretrained_name), from_tf=False
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained(base)
    model.tokenizer = tokenizer
    optimizer = AdamW(model.parameters(), lr=5e-5)

    seed_everything(seed)
    train_data = list(jsonlines.Reader(open("datasets/train_set.jsonl", "r")).iter())
    dev_data = list(jsonlines.Reader(open("datasets/dev_set.jsonl", "r")).iter())
    test_data = list(jsonlines.Reader(open("datasets/testset.jsonl", "r")).iter())
    random.shuffle(train_data)
    train_iterator = infinite_iterator(train_data)

    ########## Training ############
    if not only_eval:
        logger.info("Intent Classifier training has started...")
        grad_accumulation_steps = batch_accum
        loss_fct = CrossEntropyLoss()
        pbar = tqdm.tqdm(range(grad_steps), desc="training")
        rolling_loss = [0.0] * 10
        for i in pbar:
            for _ in range(grad_accumulation_steps):
                batch_inp = []
                batch_tgt = []
                for _ in range(batch_size):
                    sample = next(train_iterator)
                    inp, tgt = create_contextual_intent_pair(sample)
                    batch_inp.append(inp)
                    batch_tgt.append(tgt)
                inputs = tokenizer(batch_inp, return_tensors="pt", padding=True).to(
                    device
                )
                targets = tokenizer(batch_tgt, return_tensors="pt", padding=True).to(
                    device
                )
                prediction = model(
                    input_ids=inputs.input_ids,
                    attention_mask=inputs.attention_mask,
                    decoder_input_ids=targets.input_ids[:, :-1],
                    decoder_attention_mask=targets.attention_mask[:, :-1],
                )
                logits = prediction.logits
                labels = targets.input_ids[:, 1:]
                loss = loss_fct(logits.view(-1, logits.size(-1)), labels.flatten())
                loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            rolling_loss.append(float(loss))
            rolling_loss.pop(0)
            pbar.set_postfix({"loss": np.average(rolling_loss)})
            if i % 100 == 0:
                print(pbar)
            if i != 0 and i % dev_steps == 0:
                evaluate(
                    model, pretrained_name, base, dev_data, UnifiedQA_intent_prediction
                )

    model.save_pretrained(f"UQA_intent_model_{len(train_data)}")
    print("saved model")
    print("##### EVALUATION ######")
    evaluate(model, pretrained_name, base, test_data, UnifiedQA_intent_prediction)
