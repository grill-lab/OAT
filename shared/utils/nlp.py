from typing import List

def jaccard_sim(sentence_1: List[str], sentence_2: List[str]) -> float:
    """Given a 2x tokenised sentences calculate Jaccard Index

    https://en.wikipedia.org/wiki/Jaccard_index

    Returns:
        Jaccard index coefficient (float)
    """
    a = set(sentence_1)
    b = set(sentence_2)
    c = a.intersection(b)
    if len(a) == 0 and len(b) == 0:
        return 0.0
    return float(len(c)) / (len(a) + len(b) - len(c))
