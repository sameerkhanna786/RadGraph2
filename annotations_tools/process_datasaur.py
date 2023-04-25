import csv
import json
import os
from argparse import ArgumentParser
from collections import OrderedDict


def read_tsv(filename):
    tsv_file = open(filename)
    tsv_reader = csv.reader(tsv_file, delimiter="\t")
    report_rows = []
    for row in tsv_reader:
        report_rows.append(row)
    return report_rows


def create_report_dict(filename, current_id_num=-1):
    # initiate a dictionary to contain entire single report
    """From filename of tsv exported from Datasaur.ai, returns a dictionary
    that contans report information as described in the repo README.

    Args:
        filename (str): tsv filename

    Returns:
        report (dict): text, entity, and relation information for a single report
    """
    # TODO: Attach the correct metadata to the reports in the dictionary
    reports = {}
    first_iter = True

    reports_rows = read_tsv(filename)
    for row in reports_rows:
        if row and row[0].startswith("#Text="):
            if not first_iter:
                # save relation information
                for rel_label in rel_labels:
                    [relation_type, entity_ids] = rel_label.split("[")

                    # ensure that each relation has two associated entities
                    # and that relation is a valid relation type
                    possible_rels = ["located_at", "modify", "suggestive_of"]
                    if (
                        len(entity_ids.split("_")) > 1
                        and relation_type in possible_rels
                    ):
                        [subj, obj] = entity_ids.split("_")
                        subj = subj
                        obj = obj.rstrip("]")
                        relation_tuple = (relation_type, obj)
                        try:
                            reports[current_id]["entities"][subj]["relations"].append(
                                relation_tuple
                            )
                        except:
                            print(reports[current_id]["entities"])
                            print(subj)
                            print(filename)
                            continue
                #             report["entities"][subj]["relations"].append(relation_tuple)

            # Start of a new report
            first_iter = False
            current_id_num += 1
            current_id = f"{current_id_num}/{current_id_num}/{current_id_num}"
            # TODO: Attach the correct metadata to the reports in the dictionary
            reports[current_id] = {"text": "", "entities": {}, "data_split": "test"}
            prev_ent_id = None
            word_count = 0
            rel_labels = []

        # If row[2] != None, then it's a word.
        if len(row) > 1:
            token = row[2].replace(" ", "")
            word_count += 1

            # Update "text" field in report dictionary
            if len(reports[current_id]["text"]) > 0:
                reports[current_id]["text"] = reports[current_id]["text"] + " " + token
            else:
                reports[current_id]["text"] = token

            # If row[3] != None and != "_", then it's an entity.
            if len(row) > 2 and row[3] != "_":
                # get entity and relation info
                labels = row[3].split("|")
                for label in labels:
                    ent_labels = []
                    if (
                        label.startswith("ANAT-")
                        or label.startswith("OBS-")
                        or label.startswith("CHAN-")
                    ):
                        ent_labels.append(label)

                    # save entity information
                    for ent_label in ent_labels:
                        # entity_id is the id given by Datasaur
                        [entity_type, entity_id] = ent_label.split("[")
                        entity_id = entity_id.rstrip("]")

                        if entity_id != prev_ent_id:  # token represents a new entity
                            reports[current_id]["entities"][entity_id] = {
                                "tokens": token,
                                "label": entity_type,
                                "start_ix": word_count - 1,
                                "end_ix": word_count - 1,
                                "relations": [],
                            }
                            prev_ent_id = entity_id
                        else:  # token is part of an existing multi-token entity
                            existing_entity = reports[current_id]["entities"][entity_id]
                            existing_entity["tokens"] = (
                                existing_entity["tokens"] + " " + token
                            )
                            existing_entity["end_ix"] = word_count - 1
                if row[4] != "_":
                    # Get relation info
                    current_rel_labels = row[4].split("|")
                    rel_labels.extend(current_rel_labels)

    return reports, current_id_num + 1


if __name__ == "__main__":
    parser = ArgumentParser(description="Preprocess Datasaur.ai report labels")
    parser.add_argument(
        "--reports_dir",
        type=str,
        required=True,
        help="path to directory with Datasaur report files with labels",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        required=True,
        help="path and filename for saving parsed reports as json",
    )
    parser.add_argument(
        "--reference_file",
        type=str,
        required=True,
        help="path to a JSON file with reference IDs",
    )
    args = parser.parse_args()

    all_reports = {}
    current_id_num = -1
    for filename in os.listdir(args.reports_dir):
        filepath = os.path.join(args.reports_dir, filename)
        current_reports, current_id_num = create_report_dict(
            filepath, current_id_num=current_id_num
        )
        # study_id = filename.split(".")[0]
        # reports[study_id] = report_dict
        all_reports = {**all_reports, **current_reports}

    with open(args.reference_file, "r") as f:
        reference_reports = json.load(f, object_pairs_hook=OrderedDict)

    for report in all_reports.values():
        search_text = report["text"]
        found = False
        for reference_id, reference_report in reference_reports.items():
            if search_text == reference_report["text"]:
                report["reference_id"] = reference_id
                found = True
                break
        if not found:
            raise ValueError("Report text not found in reference reports")
    all_reports = {v["reference_id"]: v for v in all_reports.values()}
    export_reports = OrderedDict(
        sorted(
            all_reports.items(),
            key=lambda x: list(reference_reports.keys()).index(x[0]),
        )
    )

    save_file = args.save_path + ".json"
    with open(save_file, "w") as fp:
        json.dump(export_reports, fp, indent=4)
