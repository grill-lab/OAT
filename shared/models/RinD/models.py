
from pytorch_lightning.core.lightning import LightningModule
from .model_utils import chunks, UnifiedQA_intent_prediction

from transformers import BartModel, BertTokenizer, BartForConditionalGeneration, BartTokenizer, T5TokenizerFast, \
    T5ForConditionalGeneration
import torch
from torch.nn import functional as F
from torch import nn
from tqdm import autonotebook as tqdm
import os
import re
import math
import random

from transformers.generation_logits_process import LogitsProcessor
from transformers.modeling_outputs import BaseModelOutput, BaseModelOutputWithPastAndCrossAttentions, Seq2SeqLMOutput, \
    Seq2SeqModelOutput


class CategoricalAccuracy():
    def __init__(self):
        self.val = 0.0
        self.count = 0.0

    def reset(self):
        self.__init__()

    def __call__(self, success):
        self.count += 1
        self.val += (1.0 if success else 0.0) / self.count

    def get_metric(self):
        return self.val


class T5_Cond_Gen_Wrapper(T5ForConditionalGeneration):
    def prepare_inputs_for_generation(
            self, input_ids, past=None, attention_mask=None, decoder_attention_mask=None, use_cache=None,
            encoder_outputs=None, **kwargs
    ):
        padding_delta = input_ids.shape[1] - decoder_attention_mask.shape[1]
        batch_size = input_ids.shape[0]

        new_decoder_mask = torch.cat(
            [decoder_attention_mask, torch.ones(batch_size, padding_delta, device=self.device)], dim=1)

        return {
            "decoder_input_ids": input_ids,
            # (input_ids!=self.config.pad_token_id).to(torch.float),
            "decoder_attention_mask": new_decoder_mask,
            "past_key_values": past,
            "encoder_outputs": encoder_outputs,
            "attention_mask": attention_mask,
            "use_cache": use_cache,
        }

    def _prepare_decoder_input_ids_for_generation(
            self, input_ids: torch.LongTensor, decoder_start_token_id: int = None, bos_token_id: int = None
    ) -> torch.LongTensor:
        return input_ids

class ScoredPrefixConstrainedLogitsProcessor(LogitsProcessor):
    r"""
    :class:`transformers.LogitsProcessor` that enforces constrained generation and is useful for prefix-conditioned
    constrained generation. See `Autoregressive Entity Retrieval <https://arxiv.org/abs/2010.00904>`__ for more
    information.

    Args:
        prefix_allowed_tokens_fn: (:obj:`Callable[[int, torch.Tensor], List[int]]`):
            This function constraints the beam search to allowed tokens only at each step. This function takes 2
            arguments :obj:`inputs_ids` and the batch ID :obj:`batch_id`. It has to return a list with the allowed
            tokens for the next generation step conditioned on the previously generated tokens :obj:`inputs_ids` and
            the batch ID :obj:`batch_id`.
    """

    def __init__(self, prefix_allowed_tokens_fn, num_beams):
        self._prefix_allowed_tokens_fn = prefix_allowed_tokens_fn
        self._num_beams = num_beams

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        mask = torch.full_like(scores, -math.inf)
        for batch_id, beam_sent in enumerate(input_ids.view(-1, self._num_beams, input_ids.shape[-1])):
            for beam_id, sent in enumerate(beam_sent):
                mask[batch_id * self._num_beams + beam_id, self._prefix_allowed_tokens_fn(batch_id, sent, scores,
                                                                                          self._num_beams)] = 0

        return scores + mask


class Reasoning_in_Decoder(LightningModule):
    def __init__(self, args={}, t5_type='t5-base', state_dict_path=None, only_answer_grads=False):
        """
        R1 = Raw 1

        Training:
        R1 + R2 + R3 -> M3
        """
        super().__init__()
        self.args = args
        self.only_answer_grads = only_answer_grads
        self.lr = 0.0001
        self.tokenizer = T5TokenizerFast.from_pretrained('t5-base')
        if state_dict_path:
            state_dict = torch.load(state_dict_path, map_location='cpu')
            config = state_dict['config']
            del state_dict['config']
            self.transformer = T5_Cond_Gen_Wrapper.from_pretrained(pretrained_model_name_or_path=None, config=config,
                                                                   state_dict=state_dict)
        else:
            self.transformer = T5_Cond_Gen_Wrapper.from_pretrained(t5_type)
        self.EM_accuracy = CategoricalAccuracy()

        self.decoder_tokenizer = T5TokenizerFast.from_pretrained('t5-base')
        self.decoder_tokenizer.padding_side = 'left'  # necessary since initial decoding sequences could have different length

        self.validation_scores = []
        self.best_checkpoint = None

        self.encoder = self.transformer.encoder
        self.decoder = self.transformer.decoder
        self.lm_head = self.transformer.lm_head

        self.transformer.old_get_logits_processor = self.transformer._get_logits_processor
        self.transformer._get_logits_processor = self.new_get_logits_processor

    def new_get_logits_processor(self, *args, **kwargs):
        tokenizer = self.tokenizer
        self = self.transformer
        default_logit_processors = self.old_get_logits_processor(*args, **kwargs)

        def prefix_allowed_tokens_fn(batch_id, input_ids, scores, num_beams):

            if self.batch_regex_constraints[batch_id] == []:
                return list(range(tokenizer.vocab_size))

            assert len(self.batch_regex_offsets) == len(
                self.batch_regex_constraints), f"regex constraints aren't same length: {len(self.batch_regex_offsets)} vs {len(self.batch_regex_constraints)}"

            top_ids = scores.argsort(descending=True)
            valid_ids = []
            for i, top_id in enumerate(top_ids[0].tolist()):
                if len(valid_ids) >= num_beams:
                    break
                if top_id == 2:
                    continue
                new_seq = input_ids.tolist() + [top_id]
                decoded_new_seq = tokenizer.decode(new_seq)
                new_section_of_decoded_seq = decoded_new_seq[self.batch_regex_offsets[batch_id]:]
                is_valid = floating_match(new_section_of_decoded_seq, self.batch_regex_constraints[batch_id])
                # print(f"checking: {decoded_new_seq}, is {is_valid} valid")
                if is_valid:
                    valid_ids.append(top_id)
                    print(f"Found: '{decoded_new_seq}' at depth {i}")

            if valid_ids == []:
                print("No IDs were valid")
                valid_ids = list(range(tokenizer.vocab_size))

            return valid_ids

        regex_processor = ScoredPrefixConstrainedLogitsProcessor(prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
                                                                 num_beams=kwargs['num_beams'])
        default_logit_processors.append(regex_processor)
        return default_logit_processors

    def sample_to_train_target_text(self, sample):
        # we use lower since it is one token for true and false
        if 'decoder_text' in sample:
            return sample['decoder_text']
        else:
            return f"<pad> Claim: {str(sample['question'])} Answer: {sample['answer']} Proof: {sample['proof']}</s>"

    def sample_to_inference_target_text(self, sample):
        if 'decoder_text' in sample:
            return sample['decoder_text']
        return f"<pad> Claim: {str(sample['question'])}"

    def extract_answer_from_prediction(self, sample):
        return sample['top_output']

    def samples_to_input(self, input_samples):
        fusion_map = []
        flat_sample_text = []
        for s, i in zip(input_samples, range(len(input_samples))):
            fusion_map.append([len(flat_sample_text), len(flat_sample_text) + len(s['facts'])])
            flat_sample_text += s['facts']
        return flat_sample_text, fusion_map

    def metric_reset(self):
        self.EM_accuracy.reset()

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.95)
        return [optimizer], [scheduler]

    def save(self, save_dir, save_file_name='model.state_dict'):
        checkpoint_path = os.path.join(save_dir, save_file_name)
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        state_dict = self.transformer.state_dict()
        state_dict['config'] = self.transformer.config
        torch.save(state_dict, checkpoint_path)

    def load(self, checkpoint_path):
        d = torch.load(checkpoint_path, map_location='cpu')
        del d['config']
        self.transformer.load_state_dict(d)

    def encoder_forward(self, fusion_map, input_ids, attention_mask, return_hidden_states=False):
        embed_dim = self.transformer.config.hidden_size
        batch_size = len(fusion_map)
        encoder_outputs = self.transformer.encoder(input_ids=input_ids, attention_mask=attention_mask,
                                                   output_hidden_states=return_hidden_states, return_dict=True)
        encoder_hidden_states = encoder_outputs.last_hidden_state

        longest_fused_seq = max([attention_mask[start:end].sum() for start, end in fusion_map])
        encoder_fused_states = torch.zeros((batch_size, longest_fused_seq, embed_dim), device=self.device)
        fused_attention_mask = torch.zeros((batch_size, longest_fused_seq), device=self.device)

        layer_fused_encoder_states = []
        if return_hidden_states:
            encoder_layers_hidden_states = encoder_outputs.hidden_states
            layers = len(encoder_layers_hidden_states)
            encoder_layers_fused_states = torch.zeros((batch_size, longest_fused_seq, layers, embed_dim),
                                                      device=self.device)
            for (start, end), i in zip(fusion_map, range(batch_size)):
                encoder_layers_hidden_states = torch.einsum('ijkl->jkil',
                                                            torch.stack(encoder_layers_hidden_states)) if isinstance(
                    encoder_layers_hidden_states, tuple) else encoder_layers_hidden_states
                selected_states = encoder_layers_hidden_states[start:end]

                encoder_attention_mask = attention_mask[start:end].reshape(-1).to(torch.bool)

                flat_encoder_layer_states = selected_states.reshape(-1, layers, embed_dim)[encoder_attention_mask]
                encoder_layers_fused_states[i, :flat_encoder_layer_states.shape[0]] = flat_encoder_layer_states

        fused_encoder_states = []
        for (start, end), i in zip(fusion_map, range(batch_size)):
            selected_states = encoder_hidden_states[start:end]
            encoder_attention_mask = attention_mask[start:end].reshape(-1).to(torch.bool)
            flat_encoder_states = selected_states.reshape(-1, embed_dim)[encoder_attention_mask]

            encoder_fused_states[i, :flat_encoder_states.shape[0]] = flat_encoder_states
            fused_attention_mask[i, :flat_encoder_states.shape[0]] = 1

        encoder_outputs = BaseModelOutput(
            last_hidden_state=encoder_fused_states,
            hidden_states=encoder_layers_fused_states if return_hidden_states else None,
            attentions=fused_attention_mask
        )
        return encoder_outputs

    def forward(self, fusion_map, input_ids, attention_mask, decoder_input_ids, decoder_attention_mask,
                return_hidden_states=False, **kwargs):
        encoder_outputs = self.encoder_forward(fusion_map, input_ids, attention_mask)
        encoder_fused_states = encoder_outputs.last_hidden_state
        fused_attention_mask = encoder_outputs.attentions
        encoder_layer_states = encoder_outputs.hidden_states

        dec_outputs = self.decoder(input_ids=decoder_input_ids,
                                   attention_mask=decoder_attention_mask,
                                   encoder_hidden_states=encoder_fused_states,
                                   encoder_attention_mask=fused_attention_mask,
                                   output_hidden_states=return_hidden_states)
        sequence_output = dec_outputs[0]
        lm_logits = self.lm_head(sequence_output)

        return Seq2SeqLMOutput(logits=lm_logits,
                               encoder_hidden_states=encoder_layer_states)

    def training_step(self, batch, batch_idx):
        try:
            input_ids = batch["encoder_ids"].to(self.device)
            attention_mask = batch['encoder_att_mask'].to(self.device)
            fusion_map = batch['fusion_map']

            decoder_input_ids = batch['decoder_input_ids'].to(self.device)
            decoder_target_ids = batch['decoder_target_ids'].to(self.device)
            decoder_attention_mask = batch['decoder_att_mask'].to(self.device)

            logits = self.forward(fusion_map=fusion_map,
                                  input_ids=input_ids,
                                  attention_mask=attention_mask,
                                  decoder_input_ids=decoder_input_ids,
                                  decoder_attention_mask=decoder_attention_mask,
                                  use_cache=False).logits

            loss_fct = nn.CrossEntropyLoss(ignore_index=self.transformer.config.pad_token_id)
            # this is to mask the query gradients since they can add noise. Only listening to tokens after "Answer" -> 11801
            if self.only_answer_grads:
                answer_token_id = 11801
                answer_mask = (decoder_target_ids == answer_token_id).cumsum(-1).to(torch.bool)
                flat_mask = answer_mask.reshape(-1)
                loss = loss_fct(logits.reshape(-1, self.transformer.config.vocab_size)[flat_mask],
                                decoder_target_ids.reshape(-1)[flat_mask])
            else:
                loss = loss_fct(logits.reshape(-1, self.transformer.config.vocab_size), decoder_target_ids.reshape(-1))

            if torch.isnan(loss):
                print(f'Got NaN my dude...')

            return loss
        except Exception as e:
            print("--------------- ERROR IN TRAINING STEP --------------")
            print(f"forward on batch {batch_idx}")
            print(batch)
            print("-----------------------------------------------------")
            raise e
            
    def train_from(self, samples, grad_steps=1000, batch_size=32, grad_accum=1):
        def get_train_iterator(data):
            while True:
                random.shuffle(data)
                for d in data:
                    yield d
        data_iterator = get_train_iterator(samples)
        pbar = tqdm.tqdm(range(grad_steps), desc="training")
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        for i in pbar:
            for k in range(grad_accum):
                batch = [next(data_iterator) for j in range(batch_size)]
                batch = self.collate(batch)
                loss = self.training_step(batch,0)
                loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            pbar.set_postfix({'loss': loss.tolist()})

    def collate(self, input_samples):
        """
        input_samples: [dict]: these are samples obtained through the __getitem__ method
        """
        batch_input_text, fusion_map = self.samples_to_input(input_samples)
        collated_samples = {'fusion_map': fusion_map}
        batch_target_text = [self.sample_to_train_target_text(s) for s in input_samples]

        encoder_tok_obj = self.tokenizer(batch_input_text, return_tensors='pt', padding=True, truncation=True)
        collated_samples['encoder_ids'] = encoder_tok_obj['input_ids']
        collated_samples['encoder_att_mask'] = encoder_tok_obj['attention_mask']

        decoder_tok_obj = self.decoder_tokenizer(batch_target_text, return_tensors='pt', padding=True,
                                                 add_special_tokens=False, truncation=True)
        collated_samples['decoder_input_ids'] = decoder_tok_obj['input_ids'][:, :-1]
        collated_samples['decoder_target_ids'] = decoder_tok_obj['input_ids'][:, 1:]
        collated_samples['decoder_att_mask'] = decoder_tok_obj['attention_mask'][:, 1:]

        if 'sample_index' in input_samples[0]:
            collated_samples['sample_idxs'] = [s['sample_index'] for s in input_samples]

        return collated_samples

    def perplexity_inference(self, input_samples, chunk_size=64, **kwargs):
        """
        input_samples: [{'all_raw_queries':['sadfad','adfad'], ...}]
        """
        self.eval()
        with torch.no_grad():
            new_samples = []
            for chunk_samples in tqdm.tqdm(list(chunks(input_samples, chunk_size)), desc="Inference"):
                flat_sample_text, fusion_map = self.samples_to_input(chunk_samples)
                encoder_tok_obj = self.tokenizer(flat_sample_text, return_tensors='pt', padding=True, truncation=True)
                input_ids = encoder_tok_obj['input_ids'].to(self.device)
                attention_mask = encoder_tok_obj['attention_mask'].to(self.device)

                encoder_outputs = self.encoder_forward(fusion_map, input_ids, attention_mask,
                                                       return_hidden_states=return_hidden_states)
                fused_attention_mask = encoder_outputs.attentions
                encoder_layer_states = encoder_outputs.hidden_states if return_hidden_states else [None] * len(
                    chunk_samples)

                batch_target_text = [self.sample_to_inference_target_text(s) for s in chunk_samples]
                decoder_tok_obj = self.decoder_tokenizer(batch_target_text, return_tensors='pt', padding=True,
                                                         add_special_tokens=False)
                decoder_input_ids = decoder_tok_obj['input_ids'].to(self.device)
                decoder_attention_mask = decoder_tok_obj['attention_mask'].to(self.device)

                kwargs.update({'encoder_outputs': encoder_outputs, 'decoder_attention_mask': decoder_attention_mask})

                def prefix_allowed_tokens_fn(batch_id, input_ids):
                    if not constrain_beam:
                        return list(range(self.decoder_tokenizer.vocab_size))
                    # print(input_ids.shape[0], '<', decoder_input_ids[batch_id].shape[0])
                    possible_sequences = [input_ids.tolist() + [i] for i in range(self.decoder_tokenizer.vocab_size)]
                    possible_strings = self.tokenizer.batch_decode(possible_sequences)

                    valid_idx = []
                    for i in range(len(possible_strings)):
                        if floating_match(possible_strings[i], input_samples[0]['valid_sequences']):
                            valid_idx.append(i)
                    return valid_idx

                # this is pretty horrendous, but I really didn't want to copy all the huggingface generate code
                self.transformer.batch_regex_constraints = []
                for sample in chunk_samples:
                    if 'regex_constraints' in sample:
                        self.transformer.batch_regex_constraints.append(sample['regex_constraints'])
                    else:
                        self.transformer.batch_regex_constraints.append([])

                outputs = self.transformer.generate(decoder_input_ids,
                                                    attention_mask=fused_attention_mask,
                                                    num_return_sequences=num_return_sequences,
                                                    num_beams=num_return_sequences,
                                                    max_length=max_len,
                                                    early_stopping=True,
                                                    output_hidden_states=True,
                                                    return_dict_in_generate=True,
                                                    output_scores=True,
                                                    # prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
                                                    use_cache=False,
                                                    **kwargs)
                output_ids = outputs.sequences
                output_scores = outputs.sequences_scores if num_return_sequences > 1 else torch.tensor(
                    [1.0] * len(chunk_samples))

    def inference(self, input_samples, max_len=60, chunk_size=64, num_return_sequences=1, return_hidden_states=False,
                  constrain_beam=False, **kwargs):
        """
        input_samples: [{'all_raw_queries':['sadfad','adfad'], ...}]
        """
        self.eval()
        with torch.no_grad():
            new_samples = []
            for chunk_samples in tqdm.tqdm(list(chunks(input_samples, chunk_size)), desc="Inference"):
                flat_sample_text, fusion_map = self.samples_to_input(chunk_samples)
                encoder_tok_obj = self.tokenizer(flat_sample_text, return_tensors='pt', padding=True, truncation=True)
                input_ids = encoder_tok_obj['input_ids'].to(self.device)
                attention_mask = encoder_tok_obj['attention_mask'].to(self.device)

                encoder_outputs = self.encoder_forward(fusion_map, input_ids, attention_mask,
                                                       return_hidden_states=return_hidden_states)
                fused_attention_mask = encoder_outputs.attentions
                encoder_layer_states = encoder_outputs.hidden_states if return_hidden_states else [None] * len(
                    chunk_samples)

                batch_target_text = [self.sample_to_inference_target_text(s) for s in chunk_samples]
                decoder_tok_obj = self.decoder_tokenizer(batch_target_text, return_tensors='pt', padding=True,
                                                         add_special_tokens=False)
                decoder_input_ids = decoder_tok_obj['input_ids'].to(self.device)
                decoder_attention_mask = decoder_tok_obj['attention_mask'].to(self.device)

                kwargs.update({'encoder_outputs': encoder_outputs, 'decoder_attention_mask': decoder_attention_mask})

                def prefix_allowed_tokens_fn(batch_id, input_ids):
                    if not constrain_beam:
                        return list(range(self.decoder_tokenizer.vocab_size))
                    # print(input_ids.shape[0], '<', decoder_input_ids[batch_id].shape[0])
                    possible_sequences = [input_ids.tolist() + [i] for i in range(self.decoder_tokenizer.vocab_size)]
                    possible_strings = self.tokenizer.batch_decode(possible_sequences)

                    valid_idx = []
                    for i in range(len(possible_strings)):
                        if floating_match(possible_strings[i], input_samples[0]['valid_sequences']):
                            valid_idx.append(i)
                    return valid_idx

                # this is pretty horrendous, but I really didn't want to copy all the huggingface generate code
                self.transformer.batch_regex_constraints = []
                for sample in chunk_samples:
                    if 'regex_constraints' in sample:
                        self.transformer.batch_regex_offsets = [len(decoder_text) for decoder_text in batch_target_text]
                        self.transformer.batch_regex_constraints.append(sample['regex_constraints'])
                    else:
                        self.transformer.batch_regex_constraints.append([])

                outputs = self.transformer.generate(decoder_input_ids,
                                                    attention_mask=fused_attention_mask,
                                                    num_return_sequences=num_return_sequences,
                                                    num_beams=num_return_sequences,
                                                    max_length=max_len,
                                                    early_stopping=True,
                                                    output_hidden_states=True,
                                                    return_dict_in_generate=True,
                                                    output_scores=True,
                                                    # prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
                                                    use_cache=False,
                                                    **kwargs)
                output_ids = outputs.sequences
                output_scores = outputs.sequences_scores if num_return_sequences > 1 else torch.tensor(
                    [1.0] * len(chunk_samples))
                output_text = [self.tokenizer.decode(single_output_ids, skip_special_tokens=True) for single_output_ids
                               in output_ids]
                output_chunks = list(chunks(output_text, num_return_sequences))
                output_score_chunks = list(chunks(output_scores, num_return_sequences))

                decoder_layer_states = torch.einsum('ijkl->jkil', torch.stack(
                    outputs.decoder_hidden_states[-1])) if return_hidden_states else [None] * len(chunk_samples)

                for i in range(len(chunk_samples)):
                    chunk_samples[i]['all_generations'] = output_chunks[i]
                    chunk_samples[i]['scores'] = output_score_chunks[i].softmax(-1).tolist()
                    chunk_samples[i]['top_output'] = output_chunks[i][0]
                    pred_answer = self.extract_answer_from_prediction(chunk_samples[i])
                    chunk_samples[i]['pred_answer'] = pred_answer
                    start, end = fusion_map[i]
                    chunk_samples[i]['model_inputs'] = flat_sample_text[start:end]
                    if return_hidden_states:
                        chunk_samples[i]['encoder_input_ids'] = input_ids[start:end]
                        chunk_samples[i]['decoder_input_ids'] = output_ids[i]
                        chunk_samples[i]['encoder_hidden_states'] = encoder_layer_states[i]
                        chunk_samples[i]['decoder_hidden_states'] = decoder_layer_states[i]
                    if 'targets' in chunk_samples[i]:
                        is_same = ems(pred_answer, chunk_samples[i]['targets'])
                        self.EM_accuracy(is_same)
                        chunk_samples[i]['EM'] = is_same

                new_samples += chunk_samples
            return new_samples

    def visualise(self, sample, embedding_mask=None):
        sample = self.inference([sample], return_hidden_states=True)[0]
        encoder_ids = sample['encoder_input_ids'].flatten()
        decoder_ids = sample['decoder_input_ids']
        all_ids = encoder_ids.tolist() + decoder_ids.tolist()

        encoder_tokens = self.tokenizer.batch_decode(encoder_ids.view(-1, 1))
        decoder_tokens = self.tokenizer.batch_decode(decoder_ids.view(-1, 1))
        all_tokens = encoder_tokens + decoder_tokens
        all_token_and_ids = [f"{idx}->{tok}" for idx, tok in zip(all_ids, all_tokens)]

        ipyw.interact(self.visualise_for_token, sample=ipyw.fixed(sample), embedding_mask=ipyw.fixed(embedding_mask),
                      target_id=ipyw.SelectionSlider(
                          options=all_token_and_ids,
                          value=all_token_and_ids[0],
                          description='Selected token:',
                          disabled=False,
                          continuous_update=False,
                          orientation='horizontal',
                          readout=True
                      ))

    def visualise_for_token(self, sample, target_id, embedding_mask=None):
        target_id = int(target_id.split('->')[0]) if isinstance(target_id, str) else target_id
        sample = self.inference([sample], return_hidden_states=True)[0]

        if embedding_mask == None:
            embedding_mask = torch.full((sample['encoder_hidden_states'].shape[-1],), True)

        sample['encoder_hidden_states'][:, :, ~embedding_mask] = 0.0
        sample['decoder_hidden_states'][:, :, ~embedding_mask] = 0.0

        encoder_dots = self.transformer.lm_head(sample['encoder_hidden_states']).argsort(descending=True).tolist()
        decoder_dots = self.transformer.lm_head(sample['decoder_hidden_states']).argsort(descending=True).tolist()

        encoder_ids = sample['encoder_input_ids'].flatten()
        decoder_ids = sample['decoder_input_ids']

        encoder_tokens = self.tokenizer.batch_decode(encoder_ids.view(-1, 1))
        decoder_tokens = self.tokenizer.batch_decode(decoder_ids.view(-1, 1))

        layers = sample['encoder_hidden_states'].shape[1]
        encoder_plot = torch.zeros((layers, len(encoder_ids)), dtype=torch.int)
        decoder_plot = torch.zeros((layers, len(decoder_ids) - 1), dtype=torch.int)

        # encoder
        for row in tqdm.tqdm(range(layers)):
            for column in range(len(encoder_ids)):
                rank = encoder_dots[column][row].index(target_id)  # (input_ids[column+1])
                encoder_plot[row, column] = rank

        # decoder
        for row in tqdm.tqdm(range(layers)):
            for column in range(len(decoder_ids) - 1):
                rank = decoder_dots[column][row].index(target_id)  # (input_ids[column+1])
                decoder_plot[row, column] = rank

        fig = plt.figure(figsize=(20, 6))
        ax1 = plt.subplot2grid((1, 3), (0, 0), colspan=2)
        ax2 = plt.subplot2grid((1, 3), (0, 2), colspan=1)

        gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1])
        h1 = ax1.imshow(encoder_plot + 1, norm=LogNorm(vmin=1), cmap=plt.cm.GnBu_r, aspect='auto')
        h2 = ax2.imshow(decoder_plot + 1, norm=LogNorm(vmin=1), cmap=plt.cm.GnBu_r, aspect='auto')

        ax1.xaxis.set_ticks(range(len(encoder_tokens)))
        ax1.set_xticklabels(encoder_tokens, minor=False, rotation=45)

        # Loop over data dimensions and create text annotations.
        for i in range(layers):
            for j in range(len(encoder_tokens)):
                if encoder_plot[i, j] < 100:
                    text = ax1.text(j, i, int(encoder_plot[i, j]),
                                    ha="center", va="center", color="w")

        for i in range(layers):
            for j in range(len(decoder_tokens) - 1):
                if decoder_plot[i, j] < 100:
                    text = ax2.text(j, i, int(decoder_plot[i, j]),
                                    ha="center", va="center", color="w")

        ax2.xaxis.set_ticks(range(len(decoder_tokens)))
        ax2.set_xticklabels(decoder_tokens, minor=False, rotation=45)
        ax1.xaxis.tick_top()
        ax2.xaxis.tick_top()

        ax1.set_title("Encoder")
        ax2.set_title("Decoder")
        fig.suptitle(f"T5 logit similarity rank for tok '{self.tokenizer.decode([target_id])}'", fontsize=16, y=1.1)

        fig.colorbar(h2, ax=ax2)
        plt.show(block=False)


def floating_match(input_str, regex_list):
    get_prefixes = lambda s: [s[:i + 1] for i in range(len(s))]
    for regex in regex_list:
        for regex_prefix in get_prefixes(regex)[::-1]:
            try:
                pattern = re.compile(regex_prefix)
                match = pattern.match(input_str)
                if match != None:
                    if match.span()[1] >= len(input_str):
                        return True
            except:
                continue
    return False