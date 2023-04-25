from annotate import *
import csv

# Determine what to filter according to MIMIC
dataset_portion = get_enum(
    "Please select which dataset portion would you like to filter",
    DatasetPortion,
)
set_dataset(dataset_portion)

# Load the radgraph reports and entities
completed_reports = load_completed_reports()
radgraph_reports = load_radgraph(completed_reports)

# Load previously done annotations
radgraph_reports = load_annotations(radgraph_reports)

# Construct the JSON dictionary
mimic_reports = {}
completed_mimic_reports = {}
chexpert_reports = {}
completed_chexpert_reports = {}
failures = 0
for report_id, radgraph_report in radgraph_reports.items():
    if radgraph_report.patient_id == "":
        chexpert_reports[report_id] = radgraph_report
        completed_chexpert_reports[radgraph_report.study_id] = completed_reports[
            radgraph_report.study_id
        ]
    else:
        mimic_reports[report_id] = radgraph_report
        completed_mimic_reports[radgraph_report.study_id] = completed_reports[
            radgraph_report.study_id
        ]

# Save the records for each partitions
save_annotations(
    mimic_reports,
    filename=f"radgraph_{dataset_portion.value}_mimic_annotations.csv",
)
save_completed_reports(
    completed_mimic_reports,
    filename=f"radgraph_{dataset_portion.value}_mimic_annotated_reports.csv",
)
save_annotations(
    chexpert_reports,
    filename=f"radgraph_{dataset_portion.value}_chexpert_annotations.csv",
)
save_completed_reports(
    completed_chexpert_reports,
    filename=f"radgraph_{dataset_portion.value}_chexpert_annotated_reports.csv",
)

print("Done :)")
