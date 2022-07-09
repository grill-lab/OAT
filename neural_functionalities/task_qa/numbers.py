import regex as re
from num2words import num2words


class NumberSanitizer:
    def __init__(self):
        self.vulgar_fraction_table = [
            ('¼', 'one quarter'),
            ('½', 'one half'),
            ('¾', 'three quarters'),
            ('⅒', 'one tenth'),
            ('⅓', 'one third'),
            ('⅔', 'two thirds'),
            ('⅛', 'one eighth'),
            ('1/4', 'one quarter'),
            ('1/2', 'one half'),
            ('3/4', 'three quarters'),
            ('1/10', 'one tenth'),
            ('1/3', 'one third'),
            ('2/3', 'two thirds'),
            ('1/8', 'one eighth')
        ]

        self.fluent_unit_table = [
            ('tbsp ', 'tablespoon '),
            ('tsp ', 'teaspoon ')
        ]

        self.fraction_table = {}

        for fraction, string in self.vulgar_fraction_table:
            self.fraction_table[fraction] = string

        self.digits_with_fractions_regex = re.compile(r"(\d+\s?\L<words>)", words=self.fraction_table.keys())
        self.digits_regex = re.compile(r"(\d+[\.\d+]?)")
        self.fractions_regex = re.compile(r"(\L<words>)", words=self.fraction_table.keys())

    def __call__(self, utterance):
        for span in self.digits_with_fractions_regex.findall(utterance):
            fraction, = self.fractions_regex.search(span).groups()
            number = span.replace(fraction, "").strip()

            utterance = utterance.replace(fraction, " and " + self.fraction_table[fraction])
            utterance = utterance.replace(number, num2words(number))

        for pattern, replacement in self.vulgar_fraction_table:
            utterance = utterance.replace(pattern, replacement)

        for number in self.digits_regex.findall(utterance):
            utterance = utterance.replace(number, num2words(number))
        return utterance
