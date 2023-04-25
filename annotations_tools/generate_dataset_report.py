from annotate import *
from datetime import datetime

RADGRAPH_LABEL_DICT = {
    RadGraphLabel.CHAN_WOR: "CHANGE-WORSENING",
    RadGraphLabel.CHAN_IMP: "CHANGE-IMPROVEMENT",
    RadGraphLabel.CHAN_NC: "CHANGE-NO-CHANGE",
    RadGraphLabel.CHAN_DEV_AP: "CHANGE-DEVICE-APPEARANCE",
    RadGraphLabel.CHAN_DEV_DISA: "CHANGE-DEVICE-DISAPPEARANCE",
    RadGraphLabel.CHAN_DEV_PLACE: "CHANGE-DEVICE-PLACEMENT",
    RadGraphLabel.CHAN_CON_AP: "CHANGE-CONDITION-APPEARANCE",
    RadGraphLabel.CHAN_CON_RES: "CHANGE-CONDITION-RESOLUTION",
}

COLORS = [
    "blue",
    "magenta",
    "orange",
    "teal",
    "violet",
    "cyan",
    "olive",
    "purple",
    "brown",
]
COLOR_INDEX = 0


def get_next_color():
    global COLORS
    global COLOR_INDEX
    if COLOR_INDEX == len(COLORS):
        COLOR_INDEX = 0
    color = COLORS[COLOR_INDEX]
    COLOR_INDEX += 1
    return color


def construct_report_latex(report_id, report_tokens, change_entities):
    report_latex = f"""\\section*{{{report_id}}}
    """
    report_latex += " ".join(report_tokens)
    report_latex += """
    \\subsection*{Annotated change entities}
    """
    if change_entities:
        report_latex += """\\begin{itemize}
        """

        for entity_text, entity_relations in change_entities:
            report_latex += f"""\\item {entity_text}
            """
            if entity_relations:
                report_latex += """\\begin{itemize}
                """
                for relation_text in entity_relations:
                    report_latex += f"""\\item {relation_text}
                    """
                report_latex += """\\end{itemize}
                """
        report_latex += """\\end{itemize}
        """
    else:
        report_latex += "None"

    report_latex += """
    \\subsection*{Remarks}
    \\textbf{Annotations correct \& complete}: Yes / No

    \\medskip
    \\noindent\\textbf{Notes}:
    \\bigskip
    \\bigskip

    \\noindent\\rule{\\textwidth}{1pt}
    """

    return report_latex


# Determine which portion to generate the report for
dataset_portion = get_enum(
    "Please select the dataset portion for which you would like to generate the report",
    DatasetPortion,
)
set_dataset(dataset_portion)

LATEX_HEAD = (
    """
\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\usepackage{xcolor}

\\title{Annotations Report ("""
    + dataset_portion.value.capitalize()
    + """ Set)}
\\author{Auto-generated on """
    + datetime.now().isoformat().split("T")[0]
    + """}
\date{}

\\begin{document}

\maketitle

\\noindent\\rule{\\textwidth}{1pt}
"""
)

LATEX_TAIL = """
\end{document}
"""

filename_base = f"radgraph_{dataset_portion.value}"
filename_annotations = filename_base + "_annotations.csv"
filename_completed = filename_base + "_annotated_reports.csv"

# Load the radgraph reports and entities
completed_reports = load_completed_reports(filename=filename_completed)
radgraph_reports = load_radgraph(completed_reports, complete_only=True)

# Load previously done annotations
radgraph_reports = load_annotations(radgraph_reports, filename=filename_annotations)

# Auto-generate the report
reports_latex = []
for _, radgraph_report in radgraph_reports.items():
    COLOR_INDEX = 0
    report_id = f"{radgraph_report.folder_id}/{radgraph_report.patient_id}/{radgraph_report.study_id}"
    sanitized_text = radgraph_report.text.replace("_", "\\_").replace("#", "\\#")
    report_tokens = sanitized_text.split()
    change_entities = []
    for entity_id, entity in radgraph_report.entities.items():
        if entity.radgraph_label in CHANGE_LABELS:
            # Highlight the entity in the report text
            entity_color = get_next_color()

            report_tokens[entity.start_ix] = (
                "\\textbf{\\color{"
                + entity_color
                + "}{"
                + report_tokens[entity.start_ix]
                + "}"
            )
            report_tokens[entity.end_ix] = report_tokens[entity.end_ix] + "}"

            # Construct entity text, entity type and relations report
            entity_text = (
                "\\textbf{\\color{"
                + entity_color
                + "}{"
                + entity.tokens
                + "}}: "
                + RADGRAPH_LABEL_DICT[entity.radgraph_label]
            )
            entity_relations = []
            for relation in entity.relations:
                relation_text = (
                    "\\textbf{"
                    + relation.relation_type.value.replace("_", "\\_")
                    + "}: "
                    + radgraph_report.entities[relation.target_entity_id].tokens
                )
                entity_relations.append(relation_text)

            change_entities.append((entity_text, entity_relations))

    # Construct the latex code for the report
    reports_latex.append(
        construct_report_latex(report_id, report_tokens, change_entities)
    )

latex = LATEX_HEAD + "\n".join(reports_latex) + LATEX_TAIL
latex = "\n".join([l.strip() for l in latex.split("\n")])
with open(filename_base + "_report.tex", "w") as f:
    f.write(latex)

print("Done :)")
