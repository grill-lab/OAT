import re

import pytest
import jsonlines
import torch
import matplotlib.pyplot as pt
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


def define_model():
    """
    This can be used to plug and play intent parsel models
    """
    print("defining model")
    model_location = '/shared/file_system/models/policy_classification/UQA_intent_model_1185'
    model = AutoModelForSeq2SeqLM.from_pretrained(model_location)
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained("allenai/unifiedqa-t5-base")
    model.tokenizer = tokenizer

    if torch.cuda.is_available():
        model.to('cuda')

    print("finished defining model")
    return model


def load_inputs(filepath):
    """
    Loads inputs from specified file path and returns as list of dicts
    """
    input_list = []
    with jsonlines.open(filepath) as reader:
        for obj in reader.iter(type=dict, skip_invalid=True):
            input_list.append(obj)
    return input_list


def create_contextual_intent_pair(annot, all_intents):
    """
    Converts input dicts into sample format required by model
    'system' : system_utterance, 'user' : user_utterance
    """
    return f"User: {annot['user']}\nSystem: {annot['system']}\nFunctions: {' | '.join(all_intents)}", f"<pad>{annot['annotation'] if 'annotation' in annot else None}</s>"


def run_intent_parser(samples, model, all_intents):
    """
    Runs the relevant intent parser model, using a list of sample
    model inputs
    """
    print("testing model")
    device = model.device
    predictions = []
    model_inputs = []
    for sample in samples:
        batch_inp = []
        inp, _ = create_contextual_intent_pair(sample, all_intents)
        batch_inp += inp
        model_inputs += batch_inp
        inputs = model.tokenizer(batch_inp, return_tensors='pt', padding=True).to(device)
        with torch.no_grad():
            output_ids = model.generate(input_ids=inputs.input_ids,
                                attention_mask=inputs.attention_mask,
                                num_beams=1)
        generated_responses = model.tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        predictions += generated_responses

    for i in range(len(samples)):
        samples[i]['intent_pred'] = predictions[i].replace('<pad>','').replace('</s>','')
        samples[i]['model_input'] = model_inputs[i]

    with jsonlines.open('outputs.jsonl',mode ='w') as writer:
        for obj in samples:
            writer.write(obj)
    return samples


def extract_args(with_args, string_param):
    """
    uses regular expressions to extract int arguments from model predictions
    and input annotations
    """
    print("extracting args")
    without_args = []
    for x in with_args:
        temp_dict = {}
        temp_dict.update({string_param : x.get(string_param)})
        args = re.search(r"\((.+)\)", x.get(string_param))
        if args:
            temp_dict.update({'args': args.group(0)})
        else:
            temp_dict.update({'args': args})
        temp_dict.update({string_param : re.sub(r"\((.+)\)", "", x.get(string_param))})
    without_args.append(temp_dict)
    return without_args


def check_matches(inputs, outputs, clean_intents):
    """
    This function checks if input 'annotation' matches output 'intent_pred'
    increments 'count' 'match' and 'args' for each annotations
    """
    print("checking matches")
    results = {}
    for x in clean_intents:
        results[x] = { 'count' : 0, 'match' : 0,'argmatch' : 0 }

    for x in range(len(inputs)):
        if inputs[x].get('annotations') == outputs[x].get('intent_pred'):
            results[inputs.get('annotation')]['match'] += 1
            if inputs[x].get('args') == outputs[x].get('args'):
                results[inputs[x].get('annotation')]['argmatch'] += 1
    results[inputs[x].get('annotation')]['count'] += 1

    return results


def create_bar_chart(results, clean_intents, output_path):
    width = 0.35

    fig, ax = pt.subplots()
    for x in clean_intents:
        ax.bar(results[x], results[x].get('match'), width, label='match', color='tab:green')
        ax.bar(results[x], results[x].get('count'), width, bottom=results[x].get('match'),
        label='count', color='tab:red')

    ax.set_ylabel('Number of occurances')
    ax.set_title('Test results')

    pt.savefig(output_path + 'test_intent_parser_outputs.jpg')


@pytest.mark.slow
def test_intent_parser_model(intent_parser_input_path, intent_parser_output_path):
    """
    Tests the model 'UnifiedQA_intent_prediction'
    Avoids boilerplate code in phase_intent_classifier
    to do this the model is isolated in this container
    Requires inputs in jsonl format
    """

    print('PARAMS')
    print(intent_parser_input_path)
    print(intent_parser_output_path)

    all_intents = ["next()",
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
                "set_timer(span: string)",
                "show_more_results()",
                "show_requirements()",
                "show_more_details()",
                "answer_question()",
                "confused"]

    clean_intents = ["next()",
                "previous()",
                "repeat()",
                "restart()",
                "chit_chat()",
                "select()",
                "step_select()",
                "search()",
                "start_task()",
                "no()",
                "yes()",
                "ASR_error()",
                "stop()",
                "pause()",
                "cancel()",
                "inform_capabilities()",
                "set_timer()",
                "show_more_results()",
                "show_requirements()",
                "show_more_details()",
                "answer_question()",]

    inputs = load_inputs(intent_parser_input_path)
    model = define_model()

    samples = []
    for i in inputs:
        sample = {}
        sample.update({'system' : i.get('system')})
        sample.update({'user': i.get('user')})
        samples.append(sample)

    outputs = run_intent_parser(samples, model, all_intents)
    inputs = extract_args(inputs, "annotation")
    outputs = extract_args(outputs, "intent_pred")

    results = check_matches(inputs, outputs, clean_intents)

    create_bar_chart(results, clean_intents, intent_parser_output_path)
