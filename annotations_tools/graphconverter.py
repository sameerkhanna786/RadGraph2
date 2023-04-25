from annotate import *
import json

# Determine what to convert
dataset_portion = get_enum(
    "Please select which dataset portion would you like to convert",
    DatasetPortion,
)
set_dataset(dataset_portion)

filename_base = input()
filename_annotations = filename_base + "_annotations.csv"
filename_completed = filename_base + "_annotated_reports.csv"

# Load the radgraph reports and entities
completed_reports = load_completed_reports(filename=filename_completed)
radgraph_reports = load_radgraph(completed_reports, complete_only=True)

# Load previously done annotations
radgraph_reports = load_annotations(radgraph_reports, filename=filename_annotations)

# Construct the JSON dictionary
json_dict = {}
for _, radgraph_report in radgraph_reports.items():
    report_id = f"{radgraph_report.folder_id}/{radgraph_report.patient_id}/{radgraph_report.study_id}.txt"

    # Create dictionary for the report with the top-level fields
    # populated
    report_json = {
        "text": radgraph_report.text,
        "data_split": dataset_portion.value,
        "entities": {},
    }
    json_dict[report_id] = report_json

    # Add entities and relations
    for entity_id, entity in radgraph_report.entities.items():
        relations_list = []
        entity_json = {
            "tokens": entity.tokens,
            "label": entity.radgraph_label.value,
            "start_ix": entity.start_ix,
            "end_ix": entity.end_ix,
            "relations": relations_list,
        }
        report_json["entities"][entity_id] = entity_json
        for relation in entity.relations:
            relations_list.append(
                [relation.relation_type.value, relation.target_entity_id]
            )


print("Writing result to a JSON file")

with open(f"./{filename_base}_annotations_graphconvert.json", "w") as f:
    json.dump(json_dict, f)

print("Done :)")
