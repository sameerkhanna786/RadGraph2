# RadGraph-Change

Chest X-ray reports frequently incorporate valuable information about the changes in the clinical state of patients since previous studies. The ability to automatically extract this information in a structured form can enable a variety of useful clinical applications, such as the modelling of patient healthcare trajectories or training of image models capable of identifying changes between subsequent radiographs. In this paper, we introduce RadGraph-Change, a dataset of 800 chest radiology reports annotated using a novel schema designed to capture a fine-grained notion of change along with rich contextual information. Our schema represents the information contained in radiology notes in the form of a knowledge graph composed of clinically relevant entities and relations. The types of entities form a hierarchy enabling principled modelling of the various sub-types of changes and observations that might be noted in each report. In addition to the RadGraph-Change dataset, we propose a novel type of model, Hierarchical DyGIE++, for efficient joint entity and relation recognition on hierarchical schemas. We find that our model achieves good performance even in environments with an imbalanced distribution of entity type. We release our dataset and the trained model as publicly available benchmarks.

## Setup

For model setup, navigate to the heirarchical-dygiepp folder.

For dataset setup, we need to convert the RadGraph-Change dataset into the PURE format. We showcase the process below for the training set, assuming its intial location is `data/radgraph_change_train_joint_final.json`

```
cd annotations_tools

cp ../data/radgraph_change_train_joint_final.json ./radgraph_change_train_joint_final.json

python process_dygie.py --reports_json ./radgraph_change_train_joint_final.json --save_path radgraph_change_train_joint_final_processed --model_name pure

echo radgraph_change_train_joint_final_processed.json | python3 split_json_for_dygie.py

cp radgraph_change_train_joint_final_processed_split.json ../data/dygie_train.json

cd ..
```

## Training a model

*Warning about coreference resolution*: The coreference code will break on sentences with only a single token. If you have these in your dataset, either get rid of them or deactivate the coreference resolution part of the model.

We rely on [Allennlp train](https://docs.allennlp.org/master/api/commands/train/) to handle model training. The `train` command takes a configuration file as an argument, and initializes a model based on the configuration, and serializes the traing model. More details on the configuration process for DyGIE can be found in [doc/config.md](doc/config.md).

To train a model, enter `./train_hierarchical_dygie.sh [BERT INITIALIZATION NAME]` at the command line, where the `[BERT INITIALIZATION NAME]` is the name of an intialization found in the `hdygie_config` directory.

## Evaluation

Model evaluation first requires the usage of the `allenlp predict` command. For example, to run predictions for H-DyGIE with PubMedBERT initialization, run the following command:

```
allennlp predict models/dygie-radgraph-pubmedbert/model.tar.gz \
./data/dygie_test.json \
--predictor dygie \
--include-package dygie \
--use-dataset-reader \
--output-file models/dygie-radgraph-pubmedbert/test_predictions.jsonl \
--cuda-device 0 \
--silent
```

Once predictions have been made for all intializations, run the script `evaluation/hdygie/evaluate.py` to obtain evaluation metric values.