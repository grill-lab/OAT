import torch
from tqdm import autonotebook as tqdm
import os
import re
import math
import random
import json
from sentence_transformers import SentenceTransformer, util


class TextClassifier(torch.nn.Module):
    def __init__(self, labels=['yes', 'no']):
        super().__init__()
        self.labels = labels
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',
                                            cache_folder="/shared/file_system/models/1_Pooling")
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(384, 128),
            torch.nn.Tanh(),
            torch.nn.Linear(128, len(labels)),
        )
        self.to(self.device)

    @property
    def device(self):
        return self.embedder.device

    def forward(self, str_list):
        with torch.no_grad():
            x = self.embedder.encode(str_list, convert_to_tensor=True).to(self.device)
        return self.layers(x)

    def predict(self, str_list):
        logits = self.forward(str_list)
        return [self.labels[i] for i in list(logits.argmax(dim=-1))]

    def save(self, out_dir='./text_classifier'):
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        state_dict = self.state_dict()
        torch.save(state_dict, os.path.join(out_dir, 'model.state_dict'))
        json.dump(self.labels, open(os.path.join(out_dir, 'labels.json'), 'w'))

    @staticmethod
    def from_pretrained(out_dir='./text_classifier'):
        state_dict = torch.load(os.path.join(out_dir, 'model.state_dict'), map_location=torch.device('cpu'))
        labels = json.load(open(os.path.join(out_dir, 'labels.json'), 'r'))
        model = TextClassifier(labels=labels)
        model.load_state_dict(state_dict)
        return model
