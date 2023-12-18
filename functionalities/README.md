# Functionalities Container

This container contains modules for system features which do not require GPU capacity to run.
They are most often called by the orchestrator.

Functionalities contains the following system functionalities:
- [Action Method Classifier](#action-method-classifier)
- [Category Searcher](#category-searcher)
- [Execution Search Manager](#execution-search-manager)
- [Intent Classifier](#intent-classifier)
- [Joke Retriever](#joke-retriever)
- [LLM Chit Chat](#llm-chit-chat)
- [LLM Description Generation](#llm-description-generation)
- [LLM Ingredient Substitution](#llm-ingredient-substitution)
- [LLM Proactive Question Generation](#llm-proactive-question-generation)
- [LLM Summary Generation](#llm-summary-generation)
- [Personality](#personality)
- [QA](#qa)
- [Query Builder](#query-builder)
- [Safety Check](#safety-check)
- [Searcher](#searcher)
- [Task Manager](#task-manager)

### Individual components descriptions
#### Action Method Classifier
Task: Given a step text, decide whether the step contains an action method (only currently implemented for cooking methods). 
If an action method is found, later functionality attempts to retrieve a matching video. 

Called by: `Execution` policy in Orchestrator

#### Category Searcher
Task: If a vague search is detected, we call the category searcher to find a matching category from our category index.
For more details, see the specific [README](./category_searcher/README.md).

Called by: `Planner` Policy in Orchestrator

#### Execution Search Manager
Task: Any response given by the user in execution that is classified by the NDP to be a SearchIntent we fact check with our LLM.
The LLM is zero-shot prompted to classify the user utterance into one the following:
['recommend_new_search', 'continue_current_task', 'ask_clarifying_question']. 
Depending on the classification, the orchestrator calls different modules next.

Called by: `Execution` Policy in Orchestrator

#### Intent Classifier
Task: Responsible for domain classification. Also contains a fallback classifiers for intent and question classification.
Given a user utterance, it can classify what the domain is (i.e. Cooking or DIY or Undefined).

Called by: various policies in Orchestrator

#### Joke Retriever
Functionality: Retrieves jokes via keyword.

Called by: `chitchat_policy` in Orchestrator

#### LLM Chit Chat
Task: If the user utterance is classified as chit chat, this module calls the LLM to generate an appropriate response.
It also processes the response and handles timeouts by the LLM or the LLM being down.

Called by: `chitchat_policy` in Orchestrator

#### LLM Description Generation
Task: Given a task name and its requirements, we call the LLM to generate a description that describes the task.
For example, this could be a description for a recipe viewed on the overview page.

Called by: `staged_enhancer` in `external_functionalities` 

#### LLM Ingredient Substitution
Task: If the QA module detects a replacement request (e.g. "can you replace the onions"), we answer with QA as normally. 
This module uses the LLM to parse the QA response into name and amount with the `LLMIngredientSubstitutionGenerator`.
We then use a mix of rules and SpaCy to replace the original ingredient with the new ingredient with the help of the `LLMIngredientStepTextRewriter`,
which rewrites step texts and recipe ingredients.

Called by: `substitution_helper` in `/qa/` functionality.

#### LLM Proactive Question Generation
Task: Based on task name, previous step and next step we generate proactive questions that the system can ask.
The goal is to generate a question about their experience with one of the previous steps or how the results turned out.
This is done by prompting the LLM.

Called by: `staged_enhancer` in `external_functionalities`

#### LLM Summary Generation
Task: Given a task step and all more details available for a step, we use the LLM to condense the information 
to create a step of better length. We do this live since this is a computationally expensive step.

Called by: `staged_enhancer` in `external_functionalities`

#### Personality
Task: This module is used for FAQs that convey a personality. If you want a standard response to certain phrases, this is where the QA pairs go.

Called by:

#### QA
Task: Given a user question, we generate an appropriate response. 
This module combines calling a few of different QA modules, including:
- IntraTaskMapQA - calling neural_functionalities
- GeneralQA - calling neural_functionalities
- LLMQA - calling llm_functionalities

The `composed_qa` module manages calling the submodules and ranks responses.
The `substitution_helper` module is used to handle replacement requests as described in [LLM Ingredient Substitution](#llm-ingredient-substitution).

Called by: qa_policy in Orchestrator

#### Query Builder
Task: Given a user session, we run some basic cleaning and tokenization on the parts of the session that need to be part of the search query.
Similarly, this module also builds theme queries.

Called by: `planner` policy and `theme_policy` in Orchestrator

#### Safety Check
Task: Given an utterance, we want to check it for privacy, sensitivity and dangerousness.
We also check if it contains offensive words or can be considered suicidal.

Called by: `phased_policy` in Orchestrator

#### Searcher
Task: Given a session, find and return a task that matches the user's information need.
This is done with different search indices, searching algorithms and a reranker.
This is one of the most important system functionalities.

Called by: various policies of the Orchestrator

#### Task Manager
Task: Given a NDP task system action classification (like go to step 3, telling a joke, telling more details), this module handles
scheduling new nodes from the TaskGraph.
It acts as the interface between system and TaskGraph.

Called by: various policies of the Orchestrator (those that handle task progression, aka validation, execution and farewell)

---------------
### Required models and offline artefacts for functionalities
Upon spinning up, the container downloads required models and offline artefacts. If you want to define new models or artefacts, edit the download configuration in `functionalities/downloads.toml`. 

