import sys
import os

sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../shared/'))
sys.path.insert(0, os.path.abspath('../orchestrator'))
sys.path.insert(0, os.path.abspath('../functionalities'))
sys.path.insert(0, os.path.abspath('../neural_functionalities'))
sys.path.insert(0, os.path.abspath('../external_functionalities'))
sys.path.insert(0, os.path.abspath('../shared/compiled_protobufs'))
sys.path.insert(0, os.path.abspath('../offline'))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'OAT'
copyright = '2023, OAT team'
author = 'OAT team'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.napoleon',      # Supports Google / Numpy docstring 
    'sphinx.ext.autodoc',       # Documentation from docstrings
    'sphinx.ext.doctest',       # Test snippets in documentation
    'sphinx.ext.todo',          # to-do syntax highlighting
    'sphinx.ext.ifconfig',      # Content based configuration
    'sphinx.ext.viewcode',

    'sphinx_rtd_theme',
]
source_suffix = ['.rst', '.md']
templates_path = ['_templates']
exclude_patterns = []

# packages that get imported but won't be available in the sphinx_docs container
autodoc_mock_imports = ['spacy', 'torch', 'pyserini', 'tqdm', 'transformers', 'isodate', 'waitress',
                        'scikit-learn', 'dateparser', 'word2number', 'pandas', 'faiss', 'wandb',
                        'sentence_transformers', 'marqo', 'clip', 'num2words', 'pytorch_lightning',
                        'dotmap', 'whisper', 'stream', 'bs4', 'IPython', 'ujson', 'pydot', 'PIL',
                        'jsonlines', 'sklearn', 'numpy', 'regex', 'boto3', 'botocore', 'draw',
                        'nltk', 'openai', 'flask', 'google', 'dateutil', 'yaml', 'grpc', 'parsers',
                        'forbiddenfruit', 'grpc_interceptor', 'scheduler_implementation', 
                        'purgo_malum', ]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
