# External functionalities

This container contains the functionality that was created as a placeholder for functionality provided by Amazon during the [Amazon Alexa Prize TaskBot Challenge 2](https://www.amazon.science/alexa-prize/taskbot-challenge) as described in their [paper](https://assets.amazon.science/3d/3a/c4ab98eb4d6eb1dcc6d279e25af5/taskbot-2-alexa-prize-paper.pdf) here.

We currently have own versions of the following functionalities:
- [Dangerous Task Classifier](#dangerous-task-classifier)
- [Database functionalities](#database-functionalities)
- [Offensive speech classifier](#offensive-speech-classifier)
- [Response Relevance Classifier](#response-relevance-classifier)


### Individual component descriptions
#### Dangerous Task Classifier
By the Alexa team, this is called the "Harmful and Unauthorized Task Classifier" [[1]](https://assets.amazon.science/3d/3a/c4ab98eb4d6eb1dcc6d279e25af5/taskbot-2-alexa-prize-paper.pdf).
We have built a placeholder with a simple wordlist, but future work is training a classifier.

Task: Given a task, decide whether it is usable or not since it is harmful and unauthorized.
This includes tasks that are dangerous, such as tasks using equipment with further training required such as chainsaws.

#### Database functionalities
This includes all Dynamo DB specific functionality to manage the database.
We also include a `staged_enhance` functionality to enable computationally expensive LLM calls on specific tasks that are selected by users.
This functionality allows improving the task live.

#### Offensive speech classifier
This component is referred to as the "Offensive Classifier" [[1]](https://assets.amazon.science/3d/3a/c4ab98eb4d6eb1dcc6d279e25af5/taskbot-2-alexa-prize-paper.pdf) by the Alexa team.
We currently provide a wordlist, but future work is training a classifier.

Task: Given an utterance, check whether it is offensive or safe to be said out loud.

#### Response Relevance Classifier
As part of the CoBot APIs [[1]](https://assets.amazon.science/3d/3a/c4ab98eb4d6eb1dcc6d279e25af5/taskbot-2-alexa-prize-paper.pdf),
a response relevance classifier was provided.
This is currently just a placeholder always returning relevance, and needs to be implemented.



