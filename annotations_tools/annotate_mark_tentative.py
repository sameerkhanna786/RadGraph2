from annotate import *
import json

# Determine which annotations to update
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

tentative_keywords_entities = [
    " ",
    "residual",
    "enlargement",
    "enlarged",
    "elevation",
    "elevated",
    "decrease",
    "postoperative",
    "chronic",
    "clear",
    "conspicuous",
    "prominent",
]
tentative_keywords_reports = tentative_keywords_entities[1:]

print("Press enter to continue")
input()

# Automatically convert annotations according to the key, marking them as tentative
json_dict = {}
for _, radgraph_report in radgraph_reports.items():

    marked_tentative = False
    for entity_id, entity in radgraph_report.entities.items():
        if any([keyword in entity.tokens for keyword in tentative_keywords_entities]):
            marked_tentative = True
            entity.annotation_status = AnnotationStatus.TENTATIVE

save_annotations(
    radgraph_reports,
    filename=f"radgraph_{dataset_portion.value}_annotations_marked.csv",
)

print("Done :)")
