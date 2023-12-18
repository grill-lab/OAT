# Orchestrator 

The orchestrator is the component responsible for receiving incoming client requests, running them through the system policies, and returning the generated response back to the client. 

* [Structure](#structure)
* [Policies](#policies)
* [Phase-specific policies](#phase-specific-policies)
    + [Intents](#intents)
    + [Domain](#domain)
    + [Planning](#planning)
        - [Theme](#theme)
        - [Elicitation](#elicitation)
    + [Validation](#validation)
    + [Execution](#execution)
        - [Condition](#condition)
        - [Extra info](#extra-info)
    + [Farewell](#farewell)
    + [Resuming](#resuming)

## Structure

[This diagram](../doc/OAT_architecture.png) shows the orchestrator in the context of the full system. [This diagram](../doc/policy.png) shows a simplified version of the policy structure and flow. 

The orchestrator itself is very simple at the top level:
 * incoming client requests will arrive at the `/run/` endpoint defined in `orchestrator/main.py`
 * this method creates or retrieves a `Session` from the database, and sets some fields based on the current request
 * the `Session` object contains a list of `ConversationTurn` objects (among a lot of other things!), and this method also adds a new empty one to the end of the existing list. This will be populated as the request is passed through the policy classes
 * the `Session` is passed to the `PhasedPolicy` class and an updated `Session` is returned, along with an `OutputInteraction` 
 * the orchestrator saves the updated `Session` to the database and returns a JSON-serialized version of the `OutputInteraction` to the client

All the details of how the client response is constructed are handled within `PhasedPolicy` or one of its sub-policies.

## Policies

The policies package contains a collection of classes that all subclass `policy.AbstractPolicy`. This involves implementing the abstract `step` method which takes a `Session` and returns a `(Session, OutputInteraction)` tuple:

```python
 def step(self, session: Session) -> (Session, OutputInteraction):
```

The `policy.PhasedPolicy` class is responsible for managing the whole policy flow, its `step` method is called by the orchestrator to start everything off. 

The `PhasedPolicy.step` method performs a safety check on the current user utterance and a check for any words/phrases indicating a desire to stop the interaction. In the latter case  `policy.FarewellPolicy` is triggered to generate an appropriate response and update the `Session`. 

In all other cases the response is produced by routing execution to one of several other policies based on the `Session` state through the `__route_policy` method. A slightly simplified version of this is shown below:

```python
if self.intents_policy.triggers(session):
    # Deals with sessions that have the following intents:
    #   - TimerIntent: manipulating/setting timers
    #   - HelpIntent: providing help/tutorial messages based on current phase
    #   - CancelIntent: closes a session immediately
    return self.intents_policy.step(session)
elif session.state != SessionState.RUNNING:
    # For resuming an interrupted session
    return self.resume_policy.step(session)
elif session.task.phase == Task.TaskPhase.DOMAIN:
    # The DomainPolicy deals with determining the domain of the task that
    # the user is interested in. It will produce a classification of either
    # Cooking or DIY before updating the phase to PLANNING. If the classifier
    # is unable to recognise the domain the phase remains set to DOMAIN
    return self.domain_policy.step(session)
elif session.task.phase == Task.TaskPhase.PLANNING:
    # Once a domain has been established, the PlanningPolicy takes over and
    # handles the process of selecting a TaskMap to execute, presenting a
    # set of choices to the user and checking if a selection has been made.
    # When this happens, the next phase is usually VALIDATING, although it
    # can also go directly to EXECUTING in some cases
    return self.planner_policy.step(session)
elif session.task.phase == Task.TaskPhase.VALIDATING:
    # The ValidationPolicy deals with displaying the list of required 
    # ingredients or tools to the user and confirming they are ready to 
    # proceed with the task. When this confirmation is received it changes
    # the phase to EXECUTING
    return self.validation_policy.step(session)
elif session.task.phase == Task.TaskPhase.EXECUTING:
    # The ExecutionPolicy is responsible for guiding the user through the steps
    # in the selected TaskMap. This phase will normally continue until the user
    # completes all the steps, or expresses a desire to stop/cancel. In either
    # case the result is to set the phase to CLOSING
    return self.execution_policy.step(session)
elif session.task.phase == Task.TaskPhase.CLOSING:
    # if no TaskMap has been selected or the task hasn't been completed, 
    # FarewellPolicy will simply call the close_session method from 
    # shared/utils/session.py to end the session, storing a transcript of the 
    # interaction in the Session object.
    #
    # If a TaskMap is set, the phase is CLOSING, and there is no StopIntent or
    # "stop" text in the current turn, it will generate a farewell/congratulatory
    # to message to return to the user indicating that the task is now
    # complete. 
    return self.farewell_policy.step(session)
else:
    logger.error("Invalid field for Task Phase")
    raise Exception("Invalid Task Phase")
```

Any request may pass through multiple policies to generate a final response. For example, an initial utterance of "pasta" will immediately be classified as the cooking domain by the `DomainPolicy`, and this will then execute the `PlanningPolicy` to produce the system response.

When a policy wants to change the current phase, it will typically update the `Session.task.phase` field and then trigger a `PhaseChangeException`. These exceptions are caught by `__route_policy` and the now-updated Session is passed through the if-statement above once again. Since this is effectively a recursive call to `__route_policy` it keeps a count of the number of levels of recursion that are active and generates an error if it goes beyond 5.

## Phase-specific policies

### Intents

The `IntentsPolicy` class has a set of "handler" objects (e.g. `TimerHandler`) and a `triggers` method which checks if a `Session` contains any of the intents that the handler objects can deal with. If such intents exists, it causes `PhasedPolicy` to call `IntentsPolicy.step()` which in turn calls the `step` method of the appropriate handler. 

Each of the handlers is an instance of `policy.AbstractIntentHandler`, which defines a `step` method identical to `policy.AbstractPolicy` and adds a `caught_intents` method which returns a list of the intents that the handler class can deal with. 

### Domain

The bulk of the `DomainPolicy` class is concerned with producing a domain classification result and then either moving the `Session` into the `PLANNING` phase or informing the user that the utterance wasn't understood. 

Domain classification is performed through an RPC to the `DomainClassifier` class in `functionalities/intent_classifier/intent_classifier.py`. If a valid result is returned, a `PhaseChangeException` is raised to trigger the `PlanningPolicy`. If the domain is unknown, an error response is constructed and returned to the user. 

### Planning

Once a domain has been established, the `PlanningPolicy` deals with searching the corpus for tasks that match the utterance received from the user, presenting the best matching tasks to the user, and allowing them to make a final selection. After a selection is made, a `PhaseChangeException` is raised to trigger either the `ValidationPolicy` or the `ExecutionPolicy`.

This policy currently has a complex `step` method that handles a lot of different situations. This is a very simplified pseudocode version:

```python
# if 'SomeIntent' means: is_in_user_interaction(..., intents_list=['SomeIntent'])

if no intents in session:
    get intent from PhaseIntentClassifier
if dangerous task detected:
    return fixed response

# a series of checks to see if routing to other policies is required
if 'ChitChatIntent' or 'QuestionIntent':
    return response from build_chat_screen helper method
if 'StopIntent':
    phase change to Farewell Policy
if 'ConfusedIntent' or '*TimerIntent':
    phase change to Intents Policy
if taskmap already selected:
    if user wants to continue:
        proceed to Validation/Execution Policy
    else:
        fallback/error response
# prompting the user to make a selection from the candidate taskmaps
if 'SelectIntent':
   display prompt containing task summary (ingredients/tools) and ask if ready to continue 
if 'YesIntent':
    repeat choice of existing candidate taskmaps
if 'NoIntent': 
    phase change back to Domain Policy
# find some candidate taskmaps if they haven't been retrieved already
search for taskmaps
populate response and return to client
```

#### Theme
Sub-policy of planning. It deals with retrieving curated `TaskMaps` from the database and mixing them with the results returned by the regular `TaskMap` searcher. This requires that the database be populated with curated themes first - see `offline/theme_upload`.

This policy is only activated in a specific set of circumstances:
 * if there are any curated `TaskMaps` in the database
 * if the call to the `PhaseIntentClassifier` in `PlanningPolicy` returns a `SearchIntent`
 * if calling `ThemePolicy.get_theme()` returns a theme match for the search (this makes an RPC to the `SemanticSearcher` service in `neural_functionalities`)

If these conditions are satisified, the `PlanningPolicy` will generate a response by calling `ThemePolicy.step` and returning that to the client. Otherwise a `SearchIntent` is handled by the `PlanningPolicy` itself.

The `ThemePolicy.step` method will return a "trivia" response if a `ChitChatIntent` is found. If a `SearchIntent` is found instead, it will retrieve theme results from the database and augment them with "normal" search results from the service in `functionalities` (this currently ultimately ends up calling `ComposedSearcher.search_taskmap` in `functionalities/searcher/composed_searcher.py`). It then takes the 3 top results and adds them to the `Session` and returns the same kind of "here are the results" response that the `PlanningPolicy` otherwise creates. 

#### Category

Sub-policy of planning. This policy is used to detect vague queries from the user, which
will allow refining the user query by suggesting helpful questions to narrow down what they wanted to search.

This is done for wikihow categories such as "Crafts" and "Home improvement", and for Cooking (from overview pages from seriouseats) such as "Mains", "Italian" and "Cake". Details about what categories are, what the ideas where, how to generate and how to curate the categories can be found in `offline/category/index/README.MD`


#### Elicitation

Sub-policy of planning, dealing with eliciting more detail from the user about a vague search. This happens if a call to the `PhaseIntentClassifier` in the `PlanningPolicy` returns a `SearchIntent` which is then determined to be non-specific enough to be classed as a `VagueSearchIntent`. If this happens, `PlanningPolicy` calls `ElicitationPolicy.step` and returns the response immediately. 

Inside the `ElicitationPolicy` class the system response is based on the data structures defined in `orchestrator/policy/planning_policy/schema.py`. 

If there have been no previous calls to the policy in the current `Session`, the response is generated by picking randomly from one of the `personality_prompts` in the `CONVERSATION_TREE` for the current domain, followed by a random `elicitiation_question`. For example, if you say "I want to cook something", the system might respond with "When I'm hungry, I enjoy making new york style pizza. What's your favourite thing to cook?".

If there have been previous calls to the policy, the process of generating the response is a bit more complex and depends on the results of previous elicitation turns. The response still ultimately comes from the `responses` section of the `CONVERSATION_TREE`, based on the domain and intent involved.

### Validation

The `ValidationPolicy` handles the transition from "selecting a task" to "executing a task". There is a lot of overlap with the structure of the `PlanningPolicy` class in the way that it uses the `PhaseIntentClassifier` to generate an intent (if needed) and then decides how to proceed based on the result. Some of the intents are handled in an almost identical way to `PlanningPolicy` (e.g. timer intents, QA, stop/cancel). 

The remainder of the policy covers:
 * returning a response listing the ingredients/tools necessary in response to a `ShowRequirementsIntent`
 * prompting the user to continue with the task if the requirements have already been displayed
 * managing cases where the number of requirements means splitting them over multiple "pages"
 * raising a `PhaseChangeException` to activate the `ExecutionPolicy` when the user confirms they want to start the task
 * routing back to `PlanningPolicy` if a 'CancelIntent' or 'NoIntent' is encountered

### Execution

The `ExecutionPolicy` class guides the user through the steps involved in performing the selected `TaskMap`. Like `ValidationPolicy` and `PlanningPolicy`, it starts by checking if no intents are associated with the current turn and calls the `PhaseIntentClassifier` if needed. 

The next step is *always* to call `ConditionPolicy.step` (see below for details). This method may or may not return a response for the client. If it does, it's returned immediately - this will indicate that a conditional question was asked in the previous response and an answer has been handled by `ConditionPolicy`. Otherwise the policy continues.

As with the other policies there are some simple handlers for selected intents (timers, stop, QA, cancel). 

There is also a check for utterances that indicate a desire to start playing a video (this may not be possible if no relevant video has been found or the device is headless), and videos may also be suggested if a `DetailsIntent` or a "more details"-type utterance is found. 

`PauseIntents` are also handled in this policy given that a task is now underway. This allows the user to request that the task execution be paused temporarily and resumed later. It looks like this uses a 30 minute timeout before the session will expire. 

The most important section of the `step` method for this policy deals with using the `TaskManager` service in `functionalities` to navigate the steps in the selected `TaskMap`, handling repeat/previous/go to/next navigation events. The remaining code populates the client response with the appropriate content given the (possibly updated) current step. 

#### Condition

Sub-policy of execution that handles `TaskMaps` that have conditional steps/questions. It has two methods that are called from `ExecutionPolicy.step`:
 * `get_condition` queries the `TaskManager` service to retrieve any conditions associated with the current `TaskMap`. If any are found, the condition text is appended to the speech text of the current `OutputInteraction` before it's returned to the client. 
 * the `step` method of this policy is set up to handle responses to the condition questions added to the previous response by `get_condition`. If no response is expected it does nothing and hands control back to `ExecutionPolicy`. Otherwise it will generate a response itself based on the intent(s) in the current interaction (e.g. confirming a Yes or No response to the question that was asked)

#### Extra info

Sub-policy of execution. This policy supports the process of adding different types of extra information to the ongoing interaction. These currently include:
 * fun facts
 * jokes
 * tips

These items are stored in the `TaskMap` and retrieved through the `TaskManager` service in `functionalities`. 

After retrieving a extra information item, the method performs a safety check on the text and a check for any words/phrases that are not appropriate or that indicate a desire to stop the interaction. 

### Farewell

This is a fairly simple policy. It checks if the `Session` phase is set to `CLOSING`, if a TaskMap has been selected, and if there is no `StopIntent` or "stop" text in the current turn. If these checks all pass, it generates an `OutputInteraction` containing a congratulatory message to the user for completing their task. 

In all other cases, it simply closes the session immediately and saves a transcript to the database. 

### Resuming

This policy checks if the `Session.resume_task` flag is set to `True`, and if so it "resets" the current `Session` by creating a fresh `Session` object but retaining the ID of the original `Session`. It may also trigger this reset if the current `Session.task.phase` is one of `DOMAIN`, `PLANNING`, `CLOSING`, `VALIDATING`. 

Finally, it updates `Session.state` to `RUNNING` to avoid triggering the policy again, and appends a `RepeatIntent` to the current turn which should cause the first action the system takes for a resumed session to be repeating the last instruction or output. 
