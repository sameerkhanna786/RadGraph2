
# CheXbert_Task_1: Adaptation of CheXbert to perform task 1 in the change prediction framework

Our code is adapted from the original CheXbert paper (Accepted to EMNLP 2020): https://arxiv.org/abs/2004.09167. This model now predicts non exclusive change types for a given report.
In this case, the model predicts whether a report contains elements indicating change (i.e. 'Change') and if it contains elements indicating no change (i.e. 'No Change'). If neither kind of elements are present, we infer that report does not contain information about change.


## Prerequisites 
(Recommended) Install requirements, with Python 3.7 or higher, using pip.

```
pip install -r requirements.txt
```

OR

Create conda environment

```
conda env create -f environment.yml
```

Activate environment

```
conda activate chexbert
```

## Preprocessing step to train a model on labeled reports

Put all train/dev set reports in csv files under the column name "Report Impression". The labels for each of the change types should be in columns with the corresponding names.

Before training, you must tokenize and save all the report impressions in the train and dev sets as lists:

python bert_tokenizer.py -d={path to train/dev reports csv} -o={path to output list}

Then, the scripts provided can be used to train the model.