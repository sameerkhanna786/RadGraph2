import json
import os
import random
from argparse import ArgumentParser
from itertools import groupby, permutations
# from utils import write_tsv


def add_entity_tags(text, subj, obj):
    """To report text, add tokens <e1> and </e1> to delineate the beginning and end of subject,
    and add tokens <e2> and </e2> to delineate the beginning and end of object.
    """
    text_arr = text.split(' ')
    if subj["start_ix"] < obj["start_ix"]:
        text_arr.insert(subj["start_ix"], "<e1>")
        text_arr.insert(subj["end_ix"]+2, "</e1>")
        text_arr.insert(obj["start_ix"]+2, "<e2>")
        text_arr.insert(obj["end_ix"]+4, "</e2>")
    else:
        text_arr.insert(obj["start_ix"], "<e2>")
        text_arr.insert(obj["end_ix"]+2, "</e2>")
        text_arr.insert(subj["start_ix"]+2, "<e1>")
        text_arr.insert(subj["end_ix"]+4, "</e1>")
    text_tags = " ".join(text_arr)
    return text_tags


def process_pure(reports_json):
    """Process labels for PURE models according to
    https://github.com/princeton-nlp/PURE#input-data-format-for-the-entity-model
    
    Note, though, that this function models each report as a single sentence
    belonging to a single document.
    
    Args:
        reports_json (str): json filename with reports and labels (see README for details)
    """
    pure_json = []
    
    # loop through each report
    for report_id, report_info in reports_dict.items():
        # get report as a list of tokens (entire report is modeled as a single long sentence)
        sentence_tokens = report_info['text'].strip().split(' ')
        
        sentence_entities = []
        sentence_relations = []
        if "labeler_1" in report_info:
            report_info = report_info["labeler_1"]
        for entity_id, entity_info in report_info['entities'].items():
            # add sentence entities
            sentence_entities.append([entity_info['start_ix'],
                                      entity_info['end_ix'],
                                      entity_info['label']])
            
            # add sentence relations
            for relation in entity_info['relations']:
                relation_type = relation[0]
                obj_id = relation[1]
                try:
                    obj_entity = report_info['entities'][obj_id]
                except:
                    print(f"No entity in report {report_id}!\n")
                else:
                    sentence_relations.append([entity_info['start_ix'],
                                               entity_info['end_ix'],
                                               obj_entity['start_ix'],
                                               obj_entity['end_ix'],
                                               relation_type])
        # save report as a single document dict
        pure_report_dict = {
            'doc_key': report_id,
            'sentences': [sentence_tokens],
            'predicted_ner': [sentence_entities],
            'predicted_relations': [sentence_relations]
        }
        pure_json.append(pure_report_dict)
    
    return pure_json


def process_pure_by_sent(reports_json):
    """Process labels for PURE models where reports are split by sentence,
    as originally intended by the PURE authors:
    https://github.com/princeton-nlp/PURE#input-data-format-for-the-entity-model
    
    Args:
        reports_json (str): json filename with reports and labels (see README for details)
    """
    pure_json = []
    rel_spanning_sents = 0
    
    # loop through each report
    for report_id, report_info in reports_dict.items():
        sents = report_info['text'].split(' . ')
        # loop through each sentence in the report
        sent_start_ix = 0
        sent_end_ix = -1
        doc_sentences = []
        doc_ner = []
        doc_relations = []
        for sent in sents:
            # get sentence as a list of tokens
            sentence_tokens = sent.strip().split(' ')
            if sentence_tokens[-1] != ".":
                sentence_tokens = sentence_tokens + ['.']
            doc_sentences.append(sentence_tokens)
            
            # get start and end indices of sentence
            sent_start_ix = sent_end_ix + 1
            sent_end_ix = sent_start_ix + len(sentence_tokens) - 1

            # loop through all entities to find those that fall within sentence
            sentence_entities = []
            sentence_relations = []
            if "labeler_1" in report_info:
                report_info = report_info["labeler_1"]
            for entity_id, entity_info in report_info['entities'].items():
                if entity_info['start_ix'] >= sent_start_ix and entity_info['end_ix'] <= sent_end_ix:
                    # add entity
                    sentence_entities.append([entity_info['start_ix'],
                                              entity_info['end_ix'],
                                              entity_info['label']])

                    # add relations where this entity is the subject
                    for relation in entity_info['relations']:
                        relation_type = relation[0]
                        obj_id = relation[1]
                        try:
                            obj_entity = report_info['entities'][obj_id]
                        except:
                            print(f"No entity in report {report_id}!\n")
                        else:
                            sentence_relations.append([entity_info['start_ix'],
                                                       entity_info['end_ix'],
                                                       obj_entity['start_ix'],
                                                       obj_entity['end_ix'],
                                                       relation_type])
                            # check if the relation spans multiple sentences
                            if obj_entity['start_ix'] < sent_start_ix or obj_entity['start_ix'] > sent_end_ix:
                                rel_spanning_sents += 1
                elif entity_info['start_ix'] >= sent_start_ix and entity_info['start_ix'] <= sent_end_ix and entity_info['end_ix'] > sent_end_ix:
                    print(f"Entity '{entity_info['tokens']}' spans multiple sentences.")
            
            doc_ner.append(sentence_entities)
            doc_relations.append(sentence_relations)
            
        assert len(doc_sentences) == len(doc_ner) == len(doc_relations)
        
        # save report as a single document dict
        pure_report_dict = {
            'doc_key': report_id,
            'sentences': doc_sentences,
            'ner': doc_ner,
            'relations': doc_relations
        }
        pure_json.append(pure_report_dict)
    print(f"{rel_spanning_sents} relations span multiple sentences.")
    return pure_json

def pure_ner_to_rel(reports_list):
    """Process predictions from PURE NER into format accepted by PURE Relation."""
    pure_json = []
    rel_spanning_sents = 0
    
    # loop through each report
    for report in reports_list:
        sents = [list(group) for k, group in groupby(report['sentences'][0], lambda x: x == ".") if not k]
        # loop through each sentence in the report
        sent_start_ix = 0
        sent_end_ix = -1
        doc_sentences = []
        doc_ner = []
        doc_predicted_ner = []
        doc_relations = []
        for sent in sents:
            sentence_tokens = sent
            if sentence_tokens[-1] != ".":
                sentence_tokens = sentence_tokens + ['.']
            doc_sentences.append(sentence_tokens)
            
            sent_start_ix = sent_end_ix + 1
            sent_end_ix = sent_start_ix + len(sentence_tokens) - 1
            sentence_ner = []
            sentence_predicted_ner = []
            sentence_relations = []

            # loop through gold entities to find those that fall within sentence
            for entity in report['ner'][0]:
                if entity[0] >= sent_start_ix and entity[1] <= sent_end_ix:
                    # add entity
                    sentence_ner.append(entity)

            # loop through predicted entities to find those that fall within sentence
            for entity in report['predicted_ner'][0]:
                if entity[0] >= sent_start_ix and entity[1] <= sent_end_ix:
                    # add entity
                    sentence_predicted_ner.append(entity)

            # loop through relations to find those that fall within sentence
            for relation in report['relations'][0]:
                subj_start_ix = relation[0]
                subj_end_ix = relation[1]
                obj_start_ix = relation[2]
                # if subject is within sentence, add relation
                if subj_start_ix >= sent_start_ix and subj_end_ix <= sent_end_ix:
                    sentence_relations.append(relation)
                    # check if the relation spans multiple sentences
                    if obj_start_ix < sent_start_ix or obj_start_ix > sent_end_ix:
                        rel_spanning_sents += 1

            doc_ner.append(sentence_ner)
            doc_predicted_ner.append(sentence_predicted_ner)
            doc_relations.append(sentence_relations)
            
        assert len(doc_sentences) == len(doc_ner) == len(doc_predicted_ner) == len(doc_relations)
        
        # save report as a single document dict
        pure_report_dict = {
            'doc_key': report['doc_key'],
            'sentences': doc_sentences,
            'ner': doc_ner,
            'predicted_ner': doc_predicted_ner,
            'relations': doc_relations
        }
        pure_json.append(pure_report_dict)
    print(f"{rel_spanning_sents} relations span multiple sentences.")
    return pure_json


def test_by_sent(reports_list):
    """Process test set, which models each report as a single sentence
    belonging to a single document, into a format that splits each report
    by sentence.
    """
    pure_json = []
    rel_spanning_sents = 0
    # loop through each report
    for report in reports_list:
        sents = [list(group) for k, group in groupby(report['sentences'][0], lambda x: x == ".") if not k]
        # loop through each sentence in the report
        sent_start_ix = 0
        sent_end_ix = -1
        doc_sentences = []
        doc_ner = []
        doc_relations = []
        for sent in sents:
            sentence_tokens = sent
            if sentence_tokens[-1] != ".":
                sentence_tokens = sentence_tokens + ['.']
            doc_sentences.append(sentence_tokens)
            
            sent_start_ix = sent_end_ix + 1
            sent_end_ix = sent_start_ix + len(sentence_tokens) - 1
            sentence_ner = []
            sentence_predicted_ner = []
            sentence_relations = []

            # loop through gold entities to find those that fall within sentence
            for entity in report['ner'][0]:
                if entity[0] >= sent_start_ix and entity[1] <= sent_end_ix:
                    # add entity
                    sentence_ner.append(entity)

            # loop through relations to find those that fall within sentence
            for relation in report['relations'][0]:
                subj_start_ix = relation[0]
                subj_end_ix = relation[1]
                obj_start_ix = relation[2]
                # if subject is within sentence, add relation
                if subj_start_ix >= sent_start_ix and subj_end_ix <= sent_end_ix:
                    sentence_relations.append(relation)
                    # check if the relation spans multiple sentences
                    if obj_start_ix < sent_start_ix or obj_start_ix > sent_end_ix:
                        rel_spanning_sents += 1

            doc_ner.append(sentence_ner)
            doc_relations.append(sentence_relations)

        assert len(doc_sentences) == len(doc_ner) == len(doc_relations)
        
        # save report as a single document dict
        pure_report_dict = {
            'doc_key': report['doc_key'],
            'sentences': doc_sentences,
            'ner': doc_ner,
            'relations': doc_relations
        }
        pure_json.append(pure_report_dict)
    print(f"{rel_spanning_sents} relations span multiple sentences.")
    return pure_json
        

def process_rbert(reports_dict):
    """From json file, parse reports for use by R-BERT (Enriching Pre-trained Language Model
    with Entity Information for Relation Classification, https://arxiv.org/pdf/1905.08284.pdf).
    See README for further details.
    
    Args:
        reports_dict (dict): reports dictionary with reports and labels (see README for details)
    
    Returns:
        train_set (list): list of lists where each list sublist (1) represents a single train
                          example, and (2) is comprised of two strings: the first string is
                          label and the second string is the tagged report text.
    """
    train_set = []
    
    # loop through each report
    for report_id, report_info in reports_dict.items():
        report_text = report_info["text"]
        
        # loop through each possible pair of entities for that report
        entity_perms = list(permutations(report_info["entities"], 2))
        for (subj, obj) in entity_perms:
            subj_ent = report_info["entities"][subj]
            obj_ent = report_info["entities"][obj]
            
            # add tags for subj and obj
            report_text_tags = add_entity_tags(report_text, subj_ent, obj_ent)
            
            # check if relation exists between subj and obj
            relation_found = False
            for rel in report_info["entities"][subj]["relations"]:
                if rel[1] == obj:
                    relation_found = True
                    relation_label = rel[0] + "(e1,e2)"
                    train_set.append([relation_label, report_text_tags])
            if relation_found == False:
                relation_label = "no_relation(e1,e2)"
                train_set.append([relation_label, report_text_tags])
    
    return train_set
    

if __name__ == "__main__":
    parser = ArgumentParser(description='Process reports and labels for training')
    parser.add_argument('--reports_json', type=str, required=True,
                        help='path to json file with reports and labels')
    parser.add_argument('--save_path', type=str, required=True,
                        help='path and filename for saving parsed reports for training')
    parser.add_argument('--model_name', type=str, required=True,
                        help='model architecture used for training')
    parser.add_argument("--split_by_sent", action='store_true',
                        help="Whether to split reports by sentence (as opposed to modeling \
                              the entire report as a single sentence).")
    parser.add_argument('--val_size', type=int, nargs='?', required=False,
                        help='If supplied, split reports into train and val sets \
                              with val_size as number of examples in val set.')
    parser.add_argument('--test_size', type=int, nargs='?', required=False,
                        help='If supplied, split reports into train, val, and test sets \
                              with val_size as number of examples in val set and \
                              test_size as number of examples in test set. Assumes that \
                              val_size is also supplied.')
    args = parser.parse_args()
    
    save_file = args.save_path
    # remove save_path file if it already exists
    if os.path.exists(save_file):
        os.remove(save_file)
    
    if args.model_name == 'pure_ner_to_rel':
        reports_list = [json.loads(line) for line in open(args.reports_json)]
    else:
        f = open(args.reports_json)
        reports_dict = json.load(f)
    
    if args.model_name == 'pure':
        if args.split_by_sent:
            data_set = process_pure_by_sent(reports_dict)
        else:
            data_set = process_pure(reports_dict)
        
        if args.val_size and args.test_size: # split reports into train, val, and test sets
            random.shuffle(data_set)
            test_set = data_set[:args.test_size]
            val_set = data_set[args.test_size:args.test_size+args.val_size]
            train_set = data_set[args.test_size+args.val_size:]
            test_path = save_file + "_test.json"
            val_path = save_file + "_val.json"
            train_path = save_file + "_train.json"
            with open(test_path, 'w') as f:
                json.dump(test_set, f)
            with open(val_path, 'w') as f:
                json.dump(val_set, f)
            with open(train_path, 'w') as f:
                json.dump(train_set, f)
        elif args.val_size: # split reports into train and val sets
            random.shuffle(data_set)
            val_set = data_set[:args.val_size]
            train_set = data_set[args.val_size:]
            val_path = save_file + "_val.json"
            train_path = save_file + "_train.json"
            with open(val_path, 'w') as f:
                json.dump(val_set, f)
            with open(train_path, 'w') as f:
                json.dump(train_set, f)
        else:        
            with open(save_file + '.json', 'w') as f:
                json.dump(data_set, f)
    elif args.model_name == 'pure_ner_to_rel':
        data_set = pure_ner_to_rel(reports_list)
        with open(save_file + '.json', 'w') as f:
            json.dump(data_set, f)
    elif args.model_name == 'test_by_sent':
        data_set = test_by_sent(reports_dict)
        with open(save_file + '.json', 'w') as f:
            json.dump(data_set, f)
    elif args.model_name == 'rbert':
        data_set = process_rbert(reports_dict)
        write_tsv(save_file, data_set)
