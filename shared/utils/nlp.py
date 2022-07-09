

def jaccard_sim(sentence_1, sentence_2):
    """ Given a 2x tokenised sentences calculate jaccard  """
    a = set(sentence_1)
    b = set(sentence_2)
    c = a.intersection(b)
    if len(a) == 0 and len(b) == 0:
        return 0.0
    return float(len(c)) / (len(a) + len(b) - len(c))
