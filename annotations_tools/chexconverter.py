from annotate import *
import csv

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


def label_type_filter_fun(label_type):
    def label_type_filter(entity):
        return entity.radgraph_label is label_type

    return label_type_filter


CHANGE_TYPES = [
    RadGraphLabel.CHAN_WOR,
    RadGraphLabel.CHAN_IMP,
    RadGraphLabel.CHAN_NC,
    RadGraphLabel.CHAN_AP,
    RadGraphLabel.CHAN_DISA,
    RadGraphLabel.CHAN_DISP,
]
# Add CSV header
HEADER = ["text"] + [ct.value for ct in CHANGE_TYPES]
rows = [HEADER]
for _, radgraph_report in radgraph_reports.items():
    # Add report text to each row
    row = [radgraph_report.text]
    for change_type in CHANGE_TYPES:
        # Add 1 if the given type of change occurs in the report and 0 otherwise
        row.append(
            1
            if radgraph_report.get_num_entities_filter(
                label_type_filter_fun(change_type)
            )
            > 0
            else 0
        )
    rows.append(row)
print("Writing rows to CSV file")

with open(f"./{filename_base}_annotations_chexconvert.csv", "w") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerows(rows)

print("Done :)")
