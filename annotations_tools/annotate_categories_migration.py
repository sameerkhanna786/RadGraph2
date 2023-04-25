from annotate import *
import json

# Override the labels
class RadGraphLabel(str, Enum):
    OBS_DP = "OBS-DP"
    OBS_U = "OBS-U"
    OBS_DA = "OBS-DA"
    ANAT_DP = "ANAT-DP"
    CHAN_WOR = "CHAN-WOR"
    CHAN_IMP = "CHAN-IMP"
    CHAN_NC = "CHAN-NC"

    # Deprecated labels
    CHAN_AP = "CHAN-AP"
    CHAN_DISA = "CHAN-DISA"
    CHAN_DISP = "CHAN-DISP"

    # New labels
    CHAN_DEV_AP = "CHAN-DEV-AP"
    CHAN_DEV_DISA = "CHAN-DEV-DISA"
    CHAN_DEV_PLACE = "CHAN-DEV-PLACE"
    CHAN_CON_AP = "CHAN-CON-AP"
    CHAN_CON_RES = "CHAN-CON-RES"


DEPRECATED_LABELS = {
    RadGraphLabel.CHAN_AP: RadGraphLabel.CHAN_CON_AP,
    RadGraphLabel.CHAN_DISA: RadGraphLabel.CHAN_CON_RES,
    RadGraphLabel.CHAN_DISP: RadGraphLabel.CHAN_DEV_PLACE,
}

# Determine what to migrate
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

# Automatically convert annotations according to the key, marking them as tentative
json_dict = {}
for _, radgraph_report in radgraph_reports.items():
    for entity_id, entity in radgraph_report.entities.items():
        if entity.radgraph_label in DEPRECATED_LABELS:
            entity.radgraph_label = DEPRECATED_LABELS[entity.radgraph_label]
            entity.annotation_status = AnnotationStatus.TENTATIVE

save_annotations(
    radgraph_reports,
    filename=f"radgraph_{dataset_portion.value}_annotations_migrated.csv",
)

print("Done :)")
