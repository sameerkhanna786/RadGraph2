import json
import numpy as np
import math
from collections import defaultdict
from argparse import ArgumentParser
from enum import Enum
import csv
import pandas as pd

class Datasets(Enum):
    ALL = 0
    MIMIC_CXR = 1
    CHEXPERT = 2

MODELS = [
    "dygie-radgraph-bert",
    "dygie-radgraph-biobert",
    "dygie-radgraph-bioclinicalbert",
    "dygie-radgraph-bluebert",
    "dygie-radgraph-pubmedbert",
]
ORIGINAL_MODEL = "dygie-radgraph-original"
RADGRAPH_CLASSES = [
    "CHAN-CON-AP",
    "CHAN-WOR",
    "CHAN-IMP",
    "CHAN-CON-RES",
    "CHAN-NC",
    "CHAN-DEV-AP",
    "CHAN-DEV-PLACE",
    "CHAN-DEV-DISA",
    "ANAT-DP",
    "OBS-DP",
    "OBS-U",
    "OBS-DA"
]
ORIGINAL_CLASSES = [
    "ANAT-DP",
    "OBS-DP",
    "OBS-U",
    "OBS-DA"
]
RADGRAPH_RELATION_CLASSES = ['modify', 'located_at', 'suggestive_of']

def load_graph(filename):
    graph = []
    with open(filename) as f:
        lines = f.readlines()
    graph = [json.loads(line) for line in lines]
    graph = {r["doc_key"]: r for r in graph}
    return graph

def print_metrics(metrics_dict, radgraph_classes):
    total_tps = 0
    total_fps = 0
    total_fns = 0
    macro_precision = 0
    macro_recall = 0
    macro_f1 = 0
    for radgraph_class in radgraph_classes:
        tps = np.float64(metrics_dict[radgraph_class]['tps'])
        total_tps += tps
        fps = np.float64(metrics_dict[radgraph_class]['fps'])
        total_fps += fps
        fns = np.float64(metrics_dict[radgraph_class]['fns'])
        total_fns += fns
        total_actual = metrics_dict[radgraph_class]['total_actual']
        total_predicted = metrics_dict[radgraph_class]['total_predicted']
        precision = tps / (tps + fps)
        macro_precision += np.nan_to_num(precision, nan=0)
        recall = tps / (tps + fns)
        macro_recall += np.nan_to_num(recall, nan=0)
        f1 = 2 * precision * recall / (precision + recall)
        macro_f1 += np.nan_to_num(f1, nan=0)
        print(f"* Class {radgraph_class}")
        print(f"  - Precision: {precision}")
        print(f"  - Recall: {recall}")
        print(f"  - F1: {f1}")
        print(f"  - Total actual: {total_actual}")
        print(f"  - Total predicted: {total_predicted}")
    micro_precision = total_tps / (total_tps + total_fps)
    micro_recall = total_tps / (total_tps + total_fns)
    micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall)
    macro_precision /= len(radgraph_classes)
    macro_recall /= len(radgraph_classes)
    macro_f1 /= len(radgraph_classes)
    print(f"* Micro precision: {micro_precision}")
    print(f"* Micro recall: {micro_recall}")
    print(f"* Micro F1: {micro_f1}")
    print(f"* Macro precision: {macro_precision}")
    print(f"* Macro recall: {macro_recall}")
    print(f"* Macro F1: {macro_f1}")
    
def to_tuples_set(array):
    return {tuple(e) for e in array}

def add_statistics(metrics_dict, radgraph_class, ner_labels_of_class, ner_predictions_of_class):
    metrics_dict[radgraph_class]['tps'] += len(ner_labels_of_class & ner_predictions_of_class)
    metrics_dict[radgraph_class]['fps'] += len(ner_predictions_of_class - ner_labels_of_class)
    metrics_dict[radgraph_class]['fns'] += len(ner_labels_of_class - ner_predictions_of_class)
    metrics_dict[radgraph_class]['total_actual'] += len(ner_labels_of_class)
    metrics_dict[radgraph_class]['total_predicted'] += len(ner_predictions_of_class)

def evaluate(model_name, radgraph_change, models_path, original_radgraph=None, evaluate_original=False, model_original=False, dataset=Datasets.ALL):
    print(f"———————————————————[ Evaluating {model_name} ({'original model head-to-head' if model_original else ('new model head-to-head' if evaluate_original else 'new model')}, dataset {dataset}) ]———————————————————")
    with open(f'{models_path}/{model_name}/test_predictions.jsonl', 'r') as f:
        lines = f.readlines()
    model_predictions = [json.loads(line) for line in lines]
    
    ner_metrics_dict = defaultdict(lambda: {'tps': 0, 'fps': 0, 'fns': 0, 'total_actual': 0, 'total_predicted': 0})
    relations_metrics_dict = defaultdict(lambda: {'tps': 0, 'fps': 0, 'fns': 0, 'total_actual': 0, 'total_predicted': 0})
    
    for data_sample in model_predictions:
        if dataset is not Datasets.ALL:
            if dataset is Datasets.MIMIC_CXR and "/" not in data_sample["doc_key"]:
                continue
            elif dataset is Datasets.CHEXPERT and "/" in data_sample["doc_key"]:
                continue
        
        if evaluate_original and original_radgraph is not None:
            ner_classes = ORIGINAL_CLASSES
            
            change_ner_labels = to_tuples_set(radgraph_change[data_sample["doc_key"]]['ner'][0])
            original_ner_labels = to_tuples_set(original_radgraph[data_sample["doc_key"]]['ner'][0])
            ner_labels = change_ner_labels & original_ner_labels
            if not model_original:
                ignored_ner = change_ner_labels - ner_labels
            else:
                ignored_ner = original_ner_labels - ner_labels
                
            change_relation_labels = to_tuples_set(radgraph_change[data_sample["doc_key"]]['relations'][0])
            original_relation_labels = to_tuples_set(original_radgraph[data_sample["doc_key"]]['relations'][0])
            relation_labels = change_relation_labels & original_relation_labels
            if not model_original:
                ignored_relations = change_relation_labels - relation_labels
            else:
                ignored_relations = original_ner_labels - relation_labels
        else:
            ner_classes = RADGRAPH_CLASSES
            ner_labels = to_tuples_set(data_sample['ner'][0])
            ignored_ner = set()
            relation_labels = to_tuples_set(data_sample['relations'][0])
            ignored_relations = set()

        ner_predictions = to_tuples_set([prediction[:3] for prediction in data_sample['predicted_ner'][0]])
        relation_predictions = to_tuples_set([prediction[:5] for prediction in data_sample['predicted_relations'][0]])
        
        for radgraph_class in ner_classes:
            ner_labels_of_class = {l for l in ner_labels if l[2] == radgraph_class}
            ner_predictions_of_class = {p for p in ner_predictions if p[2] == radgraph_class and p not in ignored_ner}
            add_statistics(ner_metrics_dict, radgraph_class, ner_labels_of_class, ner_predictions_of_class)
            
        for radgraph_class in RADGRAPH_RELATION_CLASSES:
            relation_labels_of_class = {l for l in relation_labels if l[4] == radgraph_class}
            relation_predictions_of_class = {p for p in relation_predictions if p[4] == radgraph_class and p not in ignored_relations}
            add_statistics(relations_metrics_dict, radgraph_class, relation_labels_of_class, relation_predictions_of_class)
       
    print("NER results")
    print_metrics(ner_metrics_dict, ner_classes)
    print()
    print("Relations results")
    print_metrics(relations_metrics_dict, RADGRAPH_RELATION_CLASSES)
    print()
    print()
    

    

if __name__ == "__main__":
    parser = ArgumentParser(description='Computes statistics for all models')
    parser.add_argument('--models_path', type=str, required=True,
                        help='path to the folder with the saved models and predictions')
    parser.add_argument('--graph_path', type=str, required=True,
                        help='path to the RadGraph-Change graph file')
    parser.add_argument('--original_graph_path', type=str,
                        help='path to the original RadGraph version 1 file, required for head-to-head comparison')
    args = parser.parse_args()
    
    models_path = args.models_path
    
    radgraph_change = load_graph(args.graph_path)
    if args.original_graph_path is not None:
        original_radgraph = load_graph(args.original_graph_path)
    else:
        original_radgraph = None
        
        
    print("#######################################################")
    print("# Evaluating RadGraph-Change models on whole test set #")
    print("#######################################################")
    for model in MODELS:
        evaluate(model, radgraph_change, models_path)
    
    print("###############################################################")
    print("# Evaluating RadGraph-Change models head-to-head on MIMIC-CXR #")
    print("###############################################################")
    for model in MODELS:
        evaluate(model, radgraph_change, models_path, original_radgraph=original_radgraph, evaluate_original=True, dataset=Datasets.MIMIC_CXR)
    print("#######################################################")
    print("# Evaluating original model head-to-head on MIMIC-CXR #")
    print("#######################################################")
    evaluate(ORIGINAL_MODEL, radgraph_change, models_path, original_radgraph=original_radgraph, evaluate_original=True, model_original=True, dataset=Datasets.MIMIC_CXR)

    print("##############################################################")
    print("# Evlauating RadGraph-Change models head-to-head on CheXpert #")
    print("##############################################################")
    for model in MODELS:
        evaluate(model, radgraph_change, models_path, original_radgraph=original_radgraph, evaluate_original=True, dataset=Datasets.CHEXPERT)
    print("######################################################")
    print("# Evaluating original model head-to-head on CheXpert #")
    print("######################################################")
    evaluate(ORIGINAL_MODEL, radgraph_change, models_path, original_radgraph=original_radgraph, evaluate_original=True, model_original=True, dataset=Datasets.CHEXPERT)
    
    print("##################################################")
    print("# Evaluating RadGraph-Change models on MIMIC-CXR #")
    print("##################################################")
    for model in MODELS:
        evaluate(model, radgraph_change, models_path, original_radgraph=original_radgraph, dataset=Datasets.MIMIC_CXR)
        
    print("#################################################")
    print("# Evaluating RadGraph-Change models on CheXpert #")
    print("#################################################")
    for model in MODELS:
        evaluate(model, radgraph_change, models_path, original_radgraph=original_radgraph, dataset=Datasets.CHEXPERT)
        
    print("Done!")
    