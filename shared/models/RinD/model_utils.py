import pandas as pd
import json
import urllib
from tqdm import tqdm
import os
import requests
import wandb
from pytorch_lightning import Trainer, Callback, seed_everything
import re
import torch

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
            "stop()",
            "pause()",
            "cancel()",
            "inform_capabilities()",
            "set_timer(span: string)",
            "show_more_results()",
            "show_requirements()",
            "show_more_details()",
            "answer_question()",
            "confused()",]

def create_contextual_intent_pair(annot):
    return f"User: {annot['user']}\nSystem: {annot['system']}\nFunctions: {' | '.join(all_intents)}", f"<pad>{annot['annotation'] if 'annotation' in annot else None}</s>"

def UnifiedQA_intent_prediction(samples, model, batch_size=32):
    """
    samples: [{system:..., user:...}]
    model
    """
    device = model.device
    task_question_chunks = chunks(samples, batch_size)
    predictions = []
    model_inputs = []
    for chunk in task_question_chunks:
        batch_inp = []
        for sample in chunk:
            inp, _ = create_contextual_intent_pair(sample)
            batch_inp.append(inp)
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
    return samples

class ModelFormatter():
    def format_data_for_RinD(self, samples, format_as_test=False):

        def format_encoder_kwargs(encoder_kwargs):
            facts = []
            for k, v in encoder_kwargs.items():
                if k == "options":
                    values = []
                    for i, opt in enumerate(v):
                        value_text = f"({i + 1})"
                        if 'title' in opt and opt.get('title') != "":
                            value_text += f" {opt['title']}"
                        if 'author' in opt and opt.get('author') != "":
                            value_text += f" by {opt['author']}"
                        values.append(value_text)
                    facts.append(f"{k}: {values}")
                else:
                    facts.append(f"{k}: {v}")
            return facts

        for sample in samples:

            sample['facts'] = format_encoder_kwargs(sample['encoder_kwargs'])
            sample['decoder_text'] = f"<pad> Last utterance: {sample['utterance']} | Function call:"

            if 'generated_kwargs' in sample and 'function_call' in sample and format_as_test == False:
                generated_kwargs_string = ', '.join([f'{k}={v}' for k, v in sample['generated_kwargs'].items()])
                sample['decoder_text'] += f" {sample['function_call']}({generated_kwargs_string})</s>"
        return samples

    def parse_inference(self, samples):
        for sample in samples:
            try:
                sample['pred_function'] = re.search('call: (.*)\(', sample['top_output']).group(1)
                string_kwargs = re.search('\((.*)\)', sample['top_output']).group(1)
                sample['pred_kwargs'] = {s.split('=')[0]: s.split('=')[1] for s in
                                         string_kwargs.split(', ')} if string_kwargs != '' else {}
            except Exception as e:
                print("PARSE ERROR")
                print(f"Model generated: {sample['top_output']}")
                sample['pred_function'] = 'ERROR'
                sample['pred_kwargs'] = {}
        return samples
    
def print_cm(cm, labels, hide_zeroes=False, hide_diagonal=False, hide_threshold=None):
    """pretty print for confusion matrixes"""
    columnwidth = max([len(x) for x in labels] + [5])  # 5 is value length
    empty_cell = " " * columnwidth
    
    # Begin CHANGES
    fst_empty_cell = (columnwidth-3)//2 * " " + "t/p" + (columnwidth-3)//2 * " "
    
    if len(fst_empty_cell) < len(empty_cell):
        fst_empty_cell = " " * (len(empty_cell) - len(fst_empty_cell)) + fst_empty_cell
    # Print header
    print("    " + fst_empty_cell, end=" ")
    # End CHANGES
    
    for label in labels:
        print("%{0}s".format(columnwidth) % label, end=" ")
        
    print()
    # Print rows
    for i, label1 in enumerate(labels):
        print("    %{0}s".format(columnwidth) % label1, end=" ")
        for j in range(len(labels)):
            cell = "%{0}.1f".format(columnwidth) % cm[i, j]
            if hide_zeroes:
                cell = cell if float(cm[i, j]) != 0 else empty_cell
            if hide_diagonal:
                cell = cell if i != j else empty_cell
            if hide_threshold:
                cell = cell if cm[i, j] > hide_threshold else empty_cell
            print(cell, end=" ")
        print()

class KStepCallback(Callback):
    def __init__(self, steps_to_call=500, callback_fns=[]):
        self.steps_to_call = steps_to_call
        self.callback_fns = callback_fns
        self.latest_global_step = -1

    def on_batch_end(self, trainer, pl_module):
        if trainer.global_step % self.steps_to_call == 0 and trainer.global_step != self.latest_global_step:
            self.latest_global_step = trainer.global_step
            for callback in self.callback_fns:
                callback(trainer)


class CustomTrainer(Trainer):
    def __init__(self, *args, steps_to_call=500, callback_fns=[], **kwargs):
        k_step_callback = KStepCallback(steps_to_call, callback_fns)
        callbacks = [k_step_callback] if callback_fns != [] else []
        super().__init__(*args, callbacks=callbacks, **kwargs)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def download_from_url(url, dst):
    """
    @param: url to download file
    @param: dst place to put the file
    """
    file_size = int(urllib.request.urlopen(url).info().get('Content-Length', -1))
    if os.path.exists(dst):
        first_byte = os.path.getsize(dst)
    else:
        first_byte = 0
    if first_byte >= file_size:
        return file_size
    header = {"Range": "bytes=%s-%s" % (first_byte, file_size)}
    pbar = tqdm(
        total=file_size, initial=first_byte,
        unit='B', unit_scale=True, desc=url.split('/')[-1])
    req = requests.get(url, headers=header, stream=True)
    with(open(dst, 'ab')) as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()
    return file_size


class Info_Plotter:
    def __init__(self):
        pass

    def tabulate_rewrites(self, samples):
        table = wandb.Table(
            columns=["q_id", "Raw query", "Re-write", "Manual", "Model output", "ndcg_cut_3", 'recall_1000'])
        for sample_obj in samples:
            model_output = sample_obj['model output'] if "model output" in sample_obj else 0
            ndcg_cut_3 = sample_obj['ndcg_cut_3'] if "ndcg_cut_3" in sample_obj else 0
            recall_1000 = sample_obj['recall_1000'] if "recall_1000" in sample_obj else 0
            table.add_data(sample_obj['q_id'], sample_obj['raw query'], sample_obj['re-write'],
                           sample_obj['manual query'], model_output, ndcg_cut_3, recall_1000)
        return {'rewrites table': table}

    def get_turn_counts(self, samples):
        counts = {}
        for turn in samples:
            id = turn['q_id'].split('_')[1]
            if id in counts:
                counts[id] += 1
            else:
                counts[id] = 1
        return counts

    def per_turn_plots(self, samples):
        metrics = ['recall_500', 'recall_1000', 'ndcg_cut_3', 'ndcg_cut_5', 'ndcg_cut_1000', 'map_cut_1000']
        charts = {}
        turn_counts = self.get_turn_counts(samples)
        for metric in metrics:
            metric_dict = {}
            for turn in samples:
                id = turn['q_id'].split('_')[1]
                if id in metric_dict:
                    try:
                        metric_dict[id] += turn[metric]  # not all turns might have a given metric
                    except:
                        pass
                else:
                    metric_dict[id] = turn[metric]

            turns = [*metric_dict]
            values = [metric_dict[turn] / turn_counts[turn] for turn in turns]
            #
            # fig, ax = plt.subplots()
            # ax.set_ylabel(metric)
            # ax.bar(turns, values)

            charts[f"per_turn_{metric}"] = wandb.Image(fig)

        return charts


