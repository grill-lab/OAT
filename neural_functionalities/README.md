# Neural functionalities

This container contains modules for system features which require GPU capacity to run.
They are most often called by other functionalities or the Orchestrator.

- [Category Relevance Scorer](#category-relevance-scorer)
- [Chit Chat Classifier](#chit-chat-classifier)
- [General QA](#general-qa)
- [Phase Intent Classifier](#phase-intent-classifier)
- [Semantic Searcher](#semantic-searcher)
- [Task QA](#task-qa)
- [Taskmap Scorer](#taskmap-scorer)
- [Video Searcher](#video-searcher)

### Individual components descriptions

#### Category Relevance Scorer
Task: Given a user query, we attempt to find a matching category. 
Categories are encoded using sBERT.

Called by: `category_searcher` in `functionalities`

#### Chit Chat Classifier
Task: Given a user utterance, we attempt to match various FAQ responses against it using sBERT.
If a matching utterance is found, we return it.
The set of prompts mapped to a set of responses are stored in utils/constants/prompts.

Called by: `chitchat_policy` in Orchestrator

#### General QA
Task: Given a general user question, generate a relevant system response. 
We use pretrained t5 huggingface QA model: https://huggingface.co/google/t5-small-ssm-nq for this task.

Called by: `composed_qa` in `functionalities`

#### Phase Intent Classifier
Task: Given a user session, translate this into a system action into the OAT Domain Specific
Language (DSL).
We also relate to this module as the NDP, which is the system's main way of understanding user commands in natural language.
For more information check out our paper or the modules [README](./phase_intent_classifier/README.md).

Called by: various policies in Orchestrator

#### Semantic Searcher
Task: Given a user query, we attempt to find a matching theme. 
Themes are encoded using sBERT.

Called by: `Domain` policy and theme policy in Orchestrator

#### Task QA
Task: Given a task specific question, generate a relevant system response.
We do this by using a pre-trained QA from huggingface: https://huggingface.co/google/flan-t5-base
and passing in context.

Called by: `composed_qa` in `functionalities`

#### Taskmap Scorer
Task: Given a task, we score its relevance for reranking purposes.
We currently do this using a T5-base model.

Called by: `feature_reranker` in searcher in `functionalities`

#### Video Searcher
Task: Given a step text that has a detected action method, we search for a video.
The video have their metadata encoded using sBERT.
If the video with the highest score is over a threshold, we return the relevant video.

Called by: `Execution` policy in Orchestrator

-------------
### Required models and offline artefacts
Upon spinning up, the container downloads required models and offline artefacts. If you want to define new models or artefacts, edit the download configuration in `neural_functionalities/downloads.toml`. 
