# Document Parser Documentation

## Food 52 Parser
### Step Parsing
Steps are identified using the "recipe__list--steps" tag. This list contains two type of elements one being actual steps to execute and the other being subheadings grouping the instructions into several parts (recipe__list-subheading).

Some recipes have various parts (eg. making homemade pasta bolognese, there might be one part to make the pasta and on for the sauce). The different parts identified using:
````
steps_object.find_all('ol')
````
For each part the parts datastructure is populated and returned as a list of parts. 
````
 [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]
 ````

In the abstract parser / non_linear_parsing_utils, these field are then treated as follows. The speech_text of the output interaction is populated with the actual step. The screen_text is populated with the concatenation of the text headling and the actual step, split by newlines. If there is no headline, the screen_text is just the actual step text.
```
output_interaction.speech_text = step.text
screen_text = f"{step.headline}<br><br>{step.text}"
```

## Wikihow Parsing
### Requirements
The requirement parsing is parsing both requirements lists of wikihow, the 'Things You’ll Need' list and the 'Ingredients' list.
Lists are identified by their ids. The lists are scraped, combined and then returned.

NOTE that the method_name has to start with Part to be handled properly by the `non_linear_parsing_utils`.

In case there is only one part the behaviour has not changed.

### Filter out non-English articles
New function `get_validity` pattern matches `https://www.wikihow.com`, because non-English entries all contain a country identififer after `www` like `'https://www.de.wikihow.com`. If there is a country code, `False` will be returned which will cause the taskgraph to be removed in the `abstract_parser`.
