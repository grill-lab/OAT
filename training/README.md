# Training container

## Intent classifier

#### Training
Currently, the only training that can be done through the training container is for the intent classifier. The training code, which is contained inside `train_intent_classifier.py` runs automatically when running the container with the command:

    $ docker compose up training

The training script takes the three datasets that are stored inside `training/datasets`, then saves the evaluation results from the test and validation sets in a folder `eval_results` after execution. The fine-tuned model will also be saved in the same `training` folder. 

**Important**: To train the intent classifier, the container should be run with a GPU available to it.

#### Adding new samples to the training set
In case you want to add new samples to the training set to fix intent misclassifications, you should add your samples to the `train_set.jsonl` file that can be found inside `training/datasets`.  The samples should have the same format as all the other samples inside the jsonl file, for example:

    {"system": "Step 3. In a third bowl, use a hand mixer to beat the egg whites 
    until soft peaks form.",
    "user": "Can you go to step 1 please", 
    "session_id": "", 
    "intent_pred": "", 
    "annotation": "step_select(1)"}

The `sesssion_id` and `intent_pred` fields can be left empty if the sample is not taken from the system logs. 

### Training parameters

The container is configured to allow arguments to be passed on the command line if you need to override any of the defaults. Run `docker compose run training -h` to see the available options. For example, to use a different batch size:
```
docker compose run training --batch_size 16
```
