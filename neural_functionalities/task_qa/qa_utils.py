from transformers import GPT2TokenizerFast
from typing import Literal

cached_tokenizers = dict()


def _find_end_character_mapping(offset_mapping, offset):
    """assumes sorted offset_mapping. unless this was modified 
       this will be the default from the tokenizer
    """
    # if the max length is bigger we just return the last index
    if offset >= max(offset_mapping[-1]):
        return [offset_mapping[-1]]
    return [ind for ind in offset_mapping if _lies_between(ind, offset)]


def _lies_between(offset_tuple, offset):
    """ 
    given a tuple of ints, determine if offset lies between them
    """
    return offset_tuple[0] <= offset < offset_tuple[1]


def get_token_indices(text: str, token_limit: int,
                      method: Literal['start', 'end', 'center', 'offset'] = 'start',
                      tokenizer=None,
                      offset: int = None):
    # leave it here instead of a parameter
    default_tokenizer = 'gpt2'

    if tokenizer is None:
        if default_tokenizer not in cached_tokenizers:
            tokenizer = GPT2TokenizerFast.from_pretrained(default_tokenizer)
            cached_tokenizers[default_tokenizer] = tokenizer
        else:
            tokenizer = cached_tokenizers[default_tokenizer]

    tokenized_text = tokenizer(text, return_offsets_mapping=True)
    token_ids = tokenized_text['input_ids']
    character_offsets = tokenized_text['offset_mapping']
    text_token_len = len(token_ids)

    # need to get the offset from the start to hit the full size
    delta = text_token_len - token_limit

    # nothing to do if it fits already
    if delta <= 0:
        return [character_offsets[0], character_offsets[-1]]

    # convert offset into token space
    character_offset_tuple = _find_end_character_mapping(character_offsets, offset)
    token_offset = character_offsets.index(character_offset_tuple[0])

    is_odd_offset = 1
    if token_limit % 2 == 1: is_odd_offset = 0

    if method == 'start':
        ind_start = character_offsets[0]
        ind_end = character_offsets[token_limit - 1]

    elif method == 'end':
        ind_start = character_offsets[delta]
        ind_end = character_offsets[-1]

    elif method == 'center':
        center_token = text_token_len // 2
        left_ind = max(center_token - token_limit // 2, 0)
        right_ind = min(center_token + token_limit // 2, text_token_len)
        ind_start = character_offsets[left_ind]
        ind_end = character_offsets[right_ind - is_odd_offset]

    elif method == 'offset':
        center_token = token_offset
        left_ind = max(center_token - token_limit // 2, 0)
        right_ind = min(center_token + token_limit // 2, text_token_len)
        ind_start = character_offsets[left_ind]
        ind_end = character_offsets[right_ind - is_odd_offset]

    else:
        raise RuntimeError("incorrect method specified")

    return ind_start, ind_end


def find_highlight_index_in_text(text, highlight):
    """ 
    return start and end character indices for the sub-string (highlight)
    """
    if highlight not in text:
        return None, None

    # returns left right
    left_ind = text.index(highlight)
    right_ind = left_ind + len(highlight)

    return left_ind, right_ind


def truncate_text(text, token_limit, highlight=None):
    """ 
    truncates text to a token limit centered on the highlight text
    """

    if highlight is None:
        method = 'start'
        center_ind = 0  # this will not be used for this start method
    else:
        # TODO the full context may ot get used if the highlight is not centered    
        # we would need to add the excess to the end/start

        method = 'offset'
        # get indices of highlight
        inds = find_highlight_index_in_text(text, highlight)
        # get the center of the highlight in chars
        center_ind = (max(inds) - min(inds)) // 2 + min(inds)
        # now map this to tokens and get the left/right char indices to achieve token limit

    ind_left, ind_right = get_token_indices(text, token_limit, method=method, offset=center_ind)
    trunc_text = text[min(ind_left):max(ind_right)]

    return trunc_text
