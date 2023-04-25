import ast
import csv
import datetime
import getpass
import json
import os
import shutil
import sys
import textwrap
from enum import Enum
from pathlib import Path
from pyparsing import *

BACKUP_FOLDER = "./annotate_backup"
RADGRAPH_FILE = "radgraph_train.json"
ANNOTATIONS_FILE = "radgraph_train_annotations.csv"
ANNOTATIONS_BACKUP_FILE_TEMPLATE = "{}_{}_{}_{}_{}_{}_radgraph_train_annotations.csv"
COMPLETED_REPORTS_FILE = "radgraph_train_annotated_reports.csv"
LOCK_FILE = ".annotate_lock"
DATASET_PORTION = None
MODE = None
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_DOUBLE_INSTANCE = False


class Styles:
    VIOLET = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def terminal_len():
    return os.get_terminal_size().columns


def strip_highlight(s):
    escape_char = Literal("\x1b")
    integers = Word(nums)
    escape_sequence = Combine(
        escape_char + "[" + Optional(delimitedList(integers, ";")) + oneOf(list(alphas))
    )
    return Suppress(escape_sequence).transformString(s)


def highlight(s, color=Styles.CYAN):
    s = str(s)
    split_s = s.split(Styles.END)
    highlighted_split_s = [f"{color}{Styles.BOLD}{s}" for s in split_s]
    highlight_s = Styles.END.join(highlighted_split_s) + Styles.END
    return highlight_s


def highlight_words(s, indexes, color=Styles.CYAN):
    split_s = s.split(" ")
    for index in indexes:
        split_s[index] = highlight(split_s[index], color=color)
    return " ".join(split_s)


def print_error(msg):
    print(highlight(msg, color=Styles.RED))


def print_wrap(s, limit=100, coef=1):
    print(textwrap.fill(s, min(limit, coef * terminal_len() - 5)))


def get_str(prompt):
    prompt += ":"
    new_line = "\n"
    sep_str = f"> {min(len(prompt.split(new_line)[0]), terminal_len() - 2) * '-'}"
    print(sep_str)
    print(f"> {prompt}")
    user_input = input("> ").strip()
    return user_input


def get_enum(prompt, enum_type, default=None):
    prompt += ":"
    new_line = "\n"
    sep_str = f"> {min(len(prompt.split(new_line)[0]), terminal_len() - 2) * '-'}"
    print(sep_str)
    print(f"> {prompt}")
    print(f"> Available options: {', '.join([e.value for e in enum_type])}")
    if default is not None:
        print(f"> Default (press enter to select): {default.value}")
    while True:
        user_input = input("> ").strip()
        try:
            if default is not None and user_input == "":
                print(sep_str)
                return default
            parsed_input = enum_type(user_input)
            print(sep_str)
            return parsed_input
        except:
            print_error(f"> ERROR: Please input valid value (see above for options)")
            pass


class AnnotationModes(str, Enum):
    ANNOTATE = "annotate"
    EDIT = "edit"
    CROSS_ANNOTATE = "cross-annotate"


class DatasetPortion(str, Enum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


class RadGraphLabel(str, Enum):
    OBS_DP = "OBS-DP"
    OBS_U = "OBS-U"
    OBS_DA = "OBS-DA"
    ANAT_DP = "ANAT-DP"
    CHAN_WOR = "CHAN-WOR"
    CHAN_IMP = "CHAN-IMP"
    CHAN_NC = "CHAN-NC"
    CHAN_DEV_AP = "CHAN-DEV-AP"
    CHAN_DEV_DISA = "CHAN-DEV-DISA"
    CHAN_DEV_PLACE = "CHAN-DEV-PLACE"
    CHAN_CON_AP = "CHAN-CON-AP"
    CHAN_CON_RES = "CHAN-CON-RES"


CHANGE_LABELS = [
    RadGraphLabel.CHAN_WOR,
    RadGraphLabel.CHAN_IMP,
    RadGraphLabel.CHAN_NC,
    RadGraphLabel.CHAN_DEV_AP,
    RadGraphLabel.CHAN_DEV_DISA,
    RadGraphLabel.CHAN_DEV_PLACE,
    RadGraphLabel.CHAN_CON_AP,
    RadGraphLabel.CHAN_CON_RES,
]


class RelationType(str, Enum):
    MODIFY = "modify"
    LOCATED_AT = "located_at"
    SUGGESTIVE_OF = "suggestive_of"


class AnnotationStatus(str, Enum):
    UNANNOTATED = "unannotated"
    ANNOTATED = "annotated"
    TENTATIVE = "tentative"


class SourceStatus(str, Enum):
    RADGRAPH = "radgraph"
    ANNOTATION = "annotation"


class EntityHighlightStatus(str, Enum):
    UNCHANGED = "unchanged"
    EDITED = "edited"
    NEW = "new"


entity_highlight_colour_dict = {
    EntityHighlightStatus.UNCHANGED: Styles.CYAN,
    EntityHighlightStatus.EDITED: Styles.VIOLET,
    EntityHighlightStatus.NEW: Styles.GREEN,
}


class AnnotationActionType(str, Enum):
    EXIT = "exit"
    EDIT = "edit"
    REMOVE = "remove"
    NEW = "new"


class Confirmation(str, Enum):
    YES = "yes"
    NO = "no"


class Action:
    def __init__(self, msg, action=lambda: None):
        self.msg = msg
        self.action = action


class AnnotationAction(Action):
    def __init__(self, msg, action_type, action=lambda: None):
        super().__init__(msg, action=action)
        self.action_type = action_type


class RadGraphReport:
    def __init__(self, folder_id, patient_id, study_id, text):
        self.folder_id = folder_id
        self.patient_id = patient_id
        self.study_id = study_id
        self.text = text
        self.entities = {}
        self.tmp_entity_id_counter = 0

    def add_entity(self, entity):
        self.entities[entity.entity_id] = entity

    def map_relations(self, fun):
        def map_entity_relations(e):
            entity.relations = [fun(r) for r in entity.relations if fun(r) is not None]

        for entity in self.entities.values():
            map_entity_relations(entity)

    def commit_entities(self):
        def translate_relation_id_fun(translation_dict):
            """Translates IDs in the entity relations using the supplied dictionary"""

            def translate_relation_id(relation):
                if relation.target_entity_id in translation_dict:
                    relation.target_entity_id = translation_dict[
                        relation.target_entity_id
                    ]
                    return relation
                else:
                    return relation

            return translate_relation_id

        # Generate new unique IDs for all the entities
        translation_dict = {}
        for entity in self.entities.values():
            tmp_entity_id = self.get_next_tmp_entity_id()
            translation_dict[entity.entity_id] = tmp_entity_id
            entity.entity_id = tmp_entity_id

        # Translate IDs in entity relations to match the unique temporary IDs
        self.map_relations(translate_relation_id_fun(translation_dict))

        # Regenerate numerical IDs in the order of entity appearance
        translation_dict = {}
        sorted_entities = sorted(list(self.entities.values()), key=lambda e: e.start_ix)
        next_id = str(1)
        for entity in sorted_entities:
            translation_dict[entity.entity_id] = next_id
            entity.entity_id = next_id
            next_id = str(int(next_id) + 1)

        # Translate IDs in entity relations to match the new numerical IDs
        self.map_relations(translate_relation_id_fun(translation_dict))

    def get_next_tmp_entity_id(self):
        fresh_id = "tmp" + str(self.tmp_entity_id_counter)
        self.tmp_entity_id_counter += 1
        return fresh_id

    def get_spans(self):
        annotated_unchanged_ixs = []
        for entity in self.get_entities_by_highlight_status(
            EntityHighlightStatus.UNCHANGED
        ).values():
            annotated_unchanged_ixs.extend(range(entity.start_ix, entity.end_ix + 1))
        annotated_new_ixs = []
        for entity in self.get_entities_by_highlight_status(
            EntityHighlightStatus.NEW
        ).values():
            annotated_new_ixs.extend(range(entity.start_ix, entity.end_ix + 1))
        annotated_edited_ixs = []
        for entity in self.get_entities_by_highlight_status(
            EntityHighlightStatus.EDITED
        ).values():
            annotated_edited_ixs.extend(range(entity.start_ix, entity.end_ix + 1))
        report_words = self.text.split(" ")
        unannotated_ixs = list(
            set(range(0, len(report_words)))
            - set(annotated_unchanged_ixs)
            - set(annotated_new_ixs)
            - set(annotated_edited_ixs)
        )
        return (
            annotated_unchanged_ixs,
            annotated_new_ixs,
            annotated_edited_ixs,
            unannotated_ixs,
        )

    def get_words(self):
        return self.text.split(" ")

    def get_context(self, start_ix, end_ix, context_fringe=2):
        context_start_ix = max(start_ix - context_fringe, 0)
        context_end_ix = min(end_ix + context_fringe, len(self.text) - 1) + 1
        context = " ".join(self.get_words()[context_start_ix:context_end_ix])
        context_left_len = start_ix - context_start_ix
        core_len = end_ix - start_ix + 1
        return highlight_words(
            context, range(context_left_len, context_left_len + core_len)
        )

    def get_entities_by_highlight_status(self, highlight_status):
        return self.get_entities_filter(
            lambda e: e.highlight_status is highlight_status
        )

    def get_entities_filter(self, filter):
        return {eid: e for eid, e in self.entities.items() if filter(e)}

    def get_num_entities(self):
        return len(self.entities)

    def get_num_entities_filter(self, filter):
        count = 0
        return len(self.get_entities_filter(filter).values())


class RadGraphEntity:
    def __init__(
        self,
        entity_id,
        report,
        tokens,
        start_ix,
        end_ix,
        radgraph_label=None,
        annotation_status=AnnotationStatus.UNANNOTATED,
        source_status=SourceStatus.RADGRAPH,
        annotated_by=None,
        highlight_status=EntityHighlightStatus.UNCHANGED,
    ):
        self.entity_id = entity_id
        self.report = report
        self.tokens = tokens
        self.start_ix = start_ix
        self.end_ix = end_ix
        self.radgraph_label = radgraph_label
        self.annotation_status = annotation_status
        self.source_status = source_status
        self.relations = []
        self.annotated_by = annotated_by or set()
        self.highlight_status = highlight_status

    @staticmethod
    def from_tuple(t, radgraph_reports):
        (
            folder_id,
            patient_id,
            study_id,
            entity_id,
            tokens,
            start_ix,
            end_ix,
            radgraph_label,
            annotation_status,
            source_status,
            relations,
            annotated_by,
        ) = t
        report = radgraph_reports[(folder_id, patient_id, study_id)]
        entity = RadGraphEntity(
            entity_id,
            report,
            tokens,
            int(start_ix),
            int(end_ix),
            radgraph_label=RadGraphLabel(radgraph_label),
            annotation_status=AnnotationStatus(annotation_status),
            source_status=SourceStatus(source_status),
            annotated_by=set(ast.literal_eval(annotated_by)),
        )
        relations = ast.literal_eval(relations)
        for relation in relations:
            entity.add_relation(
                RadGraphRelation(relation[1], RelationType(relation[0]))
            )
        report.entities[entity_id] = entity
        return entity

    def add_relation(self, relation):
        self.relations.append(relation)

    def to_tuple(self):
        report = self.report
        return (
            report.folder_id,
            report.patient_id,
            report.study_id,
            self.entity_id,
            self.tokens,
            self.start_ix,
            self.end_ix,
            self.radgraph_label.value,
            self.annotation_status.value,
            self.source_status.value,
            self.serialize_relations(),
            str(list(self.annotated_by)),
        )

    def serialize_relations(self):
        str_relations = [
            f'["{r.relation_type.value}", "{r.target_entity_id}"]'
            for r in self.relations
        ]
        return f'[{", ".join(str_relations)}]'

    def stringify_relation(self, r):
        target_str = f"{self.report.entities[r.target_entity_id].tokens} (ID {r.target_entity_id})"
        return f"{r.relation_type.value}: {target_str}"

    def stringify_relations(self):
        str_relations = [self.stringify_relation(r) for r in self.relations]
        return " | ".join(str_relations)

    def stringify_annotated_by(self):
        return ", ".join(self.annotated_by) if self.annotated_by else "noone"

    def stringify(self):
        radgraph_label_str = (
            self.radgraph_label.value
            if self.radgraph_label not in CHANGE_LABELS
            else highlight(self.radgraph_label.value, color=Styles.YELLOW)
        )
        return f"{self.tokens} ({self.start_ix}:{self.end_ix}, ID {self.entity_id}): {radgraph_label_str} | Status: {self.annotation_status.value} | Source: {self.source_status.value} | {self.stringify_relations() or 'no relations'} | annotated by: {self.stringify_annotated_by()}"

    def print_annotation_header(self):
        header_str = f"Annotating report {self.report.folder_id}/{self.report.patient_id}/{self.report.study_id}"
        entity_str = self.stringify()
        sep_str = "#" * min(
            max(len(strip_highlight(header_str)), len(strip_highlight(entity_str))),
            terminal_len() - 2,
        )
        print(sep_str)
        print(header_str)
        print(highlight(entity_str))
        print(sep_str)
        highlighted_report = highlight_words(
            self.report.text, list(range(self.start_ix, self.end_ix + 1))
        )
        print_wrap(highlighted_report)

    def annotate_label(self, show_header=False):
        if show_header:
            self.print_annotation_header()
        while True:
            radgraph_label = get_enum(
                f"Please specify label for {highlight(self.tokens)}",
                RadGraphLabel,
                self.radgraph_label or RadGraphLabel.CHAN_NC,
            )
            print(
                f"Ok, selected label {highlight(radgraph_label.value)} for {highlight(self.tokens)}"
            )
            annotation_status = get_enum(
                f"Please confirm annotation status (annotated: done, tentative: further review needed,\n  unannotated: annotate again)",
                AnnotationStatus,
                AnnotationStatus.ANNOTATED,
            )
            if (
                annotation_status is AnnotationStatus.ANNOTATED
                or annotation_status is AnnotationStatus.TENTATIVE
            ):
                self.radgraph_label = radgraph_label
                self.annotation_status = annotation_status
                print(
                    f"Ok, annotation status set to {highlight(annotation_status.value)}"
                )
                self.annotated_by.add(getpass.getuser())
                return

    def modify_tokens(self):
        tokens, tokens_ixs = get_entity_tokens(self.report, edited_entity=self)
        if tokens is None:
            return
        available_actions = []
        for start_ix, end_ix in tokens_ixs:
            available_actions.append(
                Action(
                    f"Set entity tokens to span '{self.report.get_context(start_ix, end_ix)}'",
                    action=complete_tokens_assignment_fun(
                        self.report, tokens, start_ix, end_ix, edited_entity=self
                    ),
                )
            )
        get_action(available_actions).action()

    def complete_new_relation_fun(self, target_entity_id, relation_type):
        def complete_new_relation():
            self.add_relation(
                RadGraphRelation(target_entity_id, RelationType(relation_type))
            )

        return complete_new_relation

    def add_new_relation_fun(self):
        def add_new_relation():
            relation_type = get_enum(
                "Please choose the type for the new relation",
                RelationType,
                default=RelationType.MODIFY,
            )

            available_actions = []
            for entity_id, entity in self.report.entities.items():
                available_actions.append(
                    Action(
                        f"{self.report.get_context(entity.start_ix, entity.end_ix)}",
                        action=self.complete_new_relation_fun(entity_id, relation_type),
                    )
                )

            available_actions.append(Action(f"Cancel adding relation"))

            get_action(
                available_actions,
                prompt="Please select the target entity for the relation",
            ).action()

        return add_new_relation

    def remove_relation_fun(self, relation_index):
        def remove_new_relation():
            del self.relations[relation_index]

        return remove_new_relation

    def annotate_relations(self, show_header=False):
        while True:
            available_actions = []
            available_actions.append(
                AnnotationAction(
                    "Add new relation",
                    AnnotationActionType.NEW,
                    action=self.add_new_relation_fun(),
                )
            )
            for i, relation in enumerate(self.relations):
                available_actions.append(
                    AnnotationAction(
                        f"Remove relation {highlight(self.stringify_relation(relation))}",
                        AnnotationActionType.REMOVE,
                        action=self.remove_relation_fun(i),
                    )
                )
            available_actions.append(
                AnnotationAction(
                    f"Exit relation editor and continue (you can still change the relations later)",
                    AnnotationActionType.EXIT,
                )
            )

            selected_action = get_action(
                available_actions,
                prompt=f"You can now edit relations for the entity {highlight(self.tokens)}. Please select an action:",
            )
            if selected_action.action_type is AnnotationActionType.EXIT:
                return
            else:
                selected_action.action()

    def delete(self):
        prompt = highlight(
            f"Are you sure you want to delete the entity {self.stringify()}? This action cannot be undone",
            Styles.YELLOW,
        )
        confirm_delete = get_enum(prompt, Confirmation, default=Confirmation.NO)
        if confirm_delete is Confirmation.NO:
            return

        # Remove all relations targetting this entity
        def delete_fun(relation):
            if relation.target_entity_id == self.entity_id:
                return None
            return relation

        self.report.map_relations(delete_fun)

        del self.report.entities[self.entity_id]


class RadGraphRelation:
    def __init__(self, target_entity_id, relation_type):
        self.target_entity_id = target_entity_id
        self.relation_type = relation_type


def print_welcome():
    print(
        """
                             _        _       
     /\                     | |      | |      
    /  \   _ __  _ __   ___ | |_ __ _| |_ ___ 
   / /\ \ | '_ \| '_ \ / _ \| __/ _` | __/ _ \\
  / ____ \| | | | | | | (_) | || (_| | ||  __/
 /_/    \_\_| |_|_| |_|\___/ \__\__,_|\__\___|
                                              
                                              
"""
    )


def get_lock():
    global EXIT_DOUBLE_INSTANCE
    try:
        os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        print_error(
            "ERROR: It seems that another instance of Annotate is currently in use."
        )
        print_error("       Annotate cannot handle concurrency and can only be used by")
        print_error("       a single user at a time. Please coordinate on Slack.")
        EXIT_DOUBLE_INSTANCE = True
        sys.exit(EXIT_FAILURE)


def set_mode(mode):
    # TODO: Using global variables in this way isn't particularly nice, may want to refactor eventually
    global MODE

    MODE = mode


def set_dataset(dataset_portion):
    # TODO: Using global variables in this way isn't particularly nice, may want to refactor eventually
    global RADGRAPH_FILE
    global ANNOTATIONS_FILE
    global ANNOTATIONS_BACKUP_FILE_TEMPLATE
    global COMPLETED_REPORTS_FILE
    global DATASET_PORTION

    annotator_suffix = (
        "" if MODE is not AnnotationModes.CROSS_ANNOTATE else f"_{getpass.getuser()}"
    )

    RADGRAPH_FILE = f"radgraph_{dataset_portion}.json"
    ANNOTATIONS_FILE = f"radgraph_{dataset_portion}_annotations{annotator_suffix}.csv"
    ANNOTATIONS_BACKUP_FILE_TEMPLATE = (
        "{}_{}_{}_{}_{}_{}_radgraph_"
        + dataset_portion
        + "_annotations"
        + annotator_suffix
        + ".csv"
    )
    COMPLETED_REPORTS_FILE = (
        f"radgraph_{dataset_portion}_annotated_reports{annotator_suffix}.csv"
    )
    DATASET_PORTION = dataset_portion


def load_csv(filename, description="items"):
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            items = [row for row in reader]
        print(
            f"Loaded {highlight(len(items), color=Styles.GREEN)} {description} from most recent save file."
        )
    else:
        print(f"No previous {description} found.")
        items = []
    return items


def load_annotations(radgraph_reports, filename=None):
    def get_num_entities_reports_filter(radgraph_reports, filter):
        return sum(
            [r.get_num_entities_filter(filter) for r in radgraph_reports.values()]
        )

    total_vanilla_radgraph = sum(
        [r.get_num_entities() for r in radgraph_reports.values()]
    )
    if filename is None:
        filename = ANNOTATIONS_FILE
    annotations_raw = load_csv(filename, description="annotations")
    if annotations_raw:
        Path(BACKUP_FOLDER).mkdir(exist_ok=True)
        now = datetime.datetime.now()
        backup_file = ANNOTATIONS_BACKUP_FILE_TEMPLATE.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )
        backup_path = os.path.join(BACKUP_FOLDER, backup_file)
        shutil.copyfile(filename, backup_path)
        for raw_annotation in annotations_raw:
            # This mutates radgraph_reports so that it has the latest annotations
            RadGraphEntity.from_tuple(raw_annotation, radgraph_reports)
    total_annotated_radgraph = get_num_entities_reports_filter(
        radgraph_reports,
        lambda e: e.annotation_status == AnnotationStatus.ANNOTATED
        and e.source_status == SourceStatus.RADGRAPH,
    )
    total_added_radgraph = get_num_entities_reports_filter(
        radgraph_reports,
        lambda e: e.annotation_status == AnnotationStatus.ANNOTATED
        and e.source_status == SourceStatus.ANNOTATION,
    )
    total_tentative_radgraph = get_num_entities_reports_filter(
        radgraph_reports, lambda e: e.annotation_status == AnnotationStatus.TENTATIVE
    )

    # TODO: Somewhat ugly hotfix, but probably not worth refactoring in the short term
    total_vanilla_radgraph = (
        total_vanilla_radgraph + total_annotated_radgraph + total_tentative_radgraph
    )
    fraction_vanilla_annotated_str = highlight(
        "{}/{} ({}%)".format(
            total_annotated_radgraph,
            total_vanilla_radgraph,
            round(100 * total_annotated_radgraph / total_vanilla_radgraph, 2),
        ),
        color=Styles.GREEN,
    )
    print(
        f"{fraction_vanilla_annotated_str} entities from the original RadGraph have been annotated."
    )
    print(
        f"{highlight(total_added_radgraph, color=Styles.GREEN)} additional entities have been added."
    )
    print(
        f"{highlight(total_tentative_radgraph, color=Styles.GREEN)} entities are marked tentative and should be checked."
    )

    return radgraph_reports


def load_completed_reports(filename=None):
    if filename is None:
        filename = COMPLETED_REPORTS_FILE
    completed_reports_raw = load_csv(filename, description="completed reports")
    completed_reports = {}
    if completed_reports_raw:
        for study_id, annotation_status in completed_reports_raw:
            annotation_status = AnnotationStatus(annotation_status)
            completed_reports[study_id] = annotation_status

    num_tentative = len(
        [r for r in completed_reports.values() if r == AnnotationStatus.TENTATIVE]
    )
    print(
        f"{highlight(num_tentative, color=Styles.GREEN)} reports are marked tentative and should be checked."
    )

    return completed_reports


def load_radgraph(completed_reports, complete_only=False):
    completed_study_ids = completed_reports.keys()
    f = open(RADGRAPH_FILE)
    radgraph = json.load(f)
    radgraph_reports = {}
    for sample_id, sample_data in radgraph.items():
        sample_id = sample_id.replace(".txt", "")
        try:
            folder_id, patient_id, study_id = sample_id.split("/")
        except ValueError as e:
            folder_id, patient_id, study_id = "", "", sample_id
        note_text = sample_data["text"]

        report = RadGraphReport(folder_id, patient_id, study_id, note_text)

        if study_id not in completed_study_ids:
            if "labeler_1" in sample_data:
                sample_data = sample_data["labeler_1"]
            entities = sample_data["entities"]
            for entity_id, entity_data in entities.items():
                tokens = entity_data["tokens"]
                radgraph_label = entity_data["label"]
                start_ix = entity_data["start_ix"]
                end_ix = entity_data["end_ix"]

                entity = RadGraphEntity(
                    entity_id,
                    report,
                    tokens,
                    start_ix,
                    end_ix,
                    radgraph_label=RadGraphLabel(radgraph_label),
                )

                for relation_type, target_entity_id in entity_data["relations"]:
                    relation = RadGraphRelation(
                        target_entity_id, RelationType(relation_type)
                    )
                    entity.add_relation(relation)

                report.add_entity(entity)

        if not complete_only or study_id in completed_reports:
            radgraph_reports[(folder_id, patient_id, study_id)] = report

    return radgraph_reports


def get_subsequence_ixs(needle, haystack, filter=lambda ix: True):
    ixs = []
    if len(needle) > len(haystack):
        return False
    for i in range(len(haystack) - len(needle) + 1):
        if needle == haystack[i : i + len(needle)] and all(
            [filter(ix) for ix in range(i, i + len(needle))]
        ):
            ixs.append((i, i + len(needle) - 1))
    return ixs


def get_entity_tokens(report, edited_entity=None):
    _, _, _, unannotated_ixs = report.get_spans()
    report_words = report.get_words()
    new_line = "\n"
    if edited_entity is None:
        prompt = (
            "Please enter tokens for the newly annotated entity or done\n  to cancel."
        )
        available_ixs = unannotated_ixs
    else:
        prompt = (
            "Please enter the new tokens for the edited entity or done\n to cancel."
        )
        available_ixs = list(range(edited_entity.start_ix, edited_entity.end_ix + 1))
        searched_ix = edited_entity.start_ix - 1
        while True:
            if searched_ix in unannotated_ixs:
                available_ixs.insert(0, searched_ix)
            else:
                break
            searched_ix -= 1
        searched_ix = edited_entity.end_ix + 1
        while True:
            if searched_ix in unannotated_ixs:
                available_ixs.append(searched_ix)
            else:
                break
            searched_ix += 1
    available_words = [report.get_words()[ix] for ix in available_ixs]
    sep_str = f"> {min(len(prompt.split(new_line)[0]), terminal_len() - 2) * '-'}"
    print(sep_str)
    print(f"> {prompt}")
    while True:
        user_input = input("> ").strip()
        if user_input == "done":
            print(sep_str)
            return None, None
        split_input = user_input.split(" ")
        if not get_subsequence_ixs(split_input, available_words):
            if edited_entity is None:
                print_error(
                    "> ERROR: Selected tokens are not a subsequence of unannotated tokens, try again"
                )
            else:
                print_error(
                    "> ERROR: Selected tokens are invalid, please try again.\n"
                    "         Note that the new tokens can only be chosen from\n"
                    "         the immediate neighbourhood of the original entity\n"
                    "         and cannot include tokens from another existing entity.\n"
                )
            continue
        tokens_ixs = get_subsequence_ixs(
            split_input, report_words, filter=lambda ix: ix in available_ixs
        )
        if not tokens_ixs:
            print_error(
                "> ERROR: Selected tokens are not a subsequence of the report text, try again"
            )
            continue
        print(sep_str)
        return user_input, tokens_ixs


def get_action(
    available_actions, prompt="Please select an action which you would like to perform:"
):
    max_str_len = len(strip_highlight(prompt))
    for available_action in available_actions:
        max_str_len = max(max_str_len, len(strip_highlight(available_action.msg)) + 3)
    sep_str = f"> {min(max_str_len, terminal_len() - 2) * '-'}"
    print(sep_str)
    print(f"> {prompt}")
    for i, available_action in enumerate(available_actions):
        print(f"> {i + 1}) {available_action.msg}")
    while True:
        if len(available_actions) == 1:
            print("> INFO: Automatically selecting only available action")
            print(sep_str)
            return available_actions[0]
        user_input = input("> ").strip()
        try:
            parsed_input = int(user_input)
            if parsed_input <= 0:
                raise ValueError
            selected_action = available_actions[parsed_input - 1]
            print(sep_str)
            return selected_action
        except:
            print_error(f"> ERROR: Please input valid value")
            pass


def complete_tokens_assignment_fun(
    report, tokens, start_ix, end_ix, edited_entity=None
):
    def complete_tokens_assignment():
        print(f"Ok, selected span '{report.get_context(start_ix, end_ix)}'")

        if edited_entity is None:
            # Create new entity
            new_entity = RadGraphEntity(
                report.get_next_tmp_entity_id(),
                report,
                tokens,
                start_ix,
                end_ix,
                source_status=SourceStatus.ANNOTATION,
                highlight_status=EntityHighlightStatus.NEW,
            )
            report.add_entity(new_entity)

            new_entity.annotate_label()
            new_entity.annotate_relations()
        else:
            # Modify the existing entity
            edited_entity.tokens = tokens
            edited_entity.start_ix = start_ix
            edited_entity.end_ix = end_ix

    return complete_tokens_assignment


def annotate_new_entity_fun(report):
    def annotate_new_entity():
        tokens, tokens_ixs = get_entity_tokens(report)
        if tokens is None:
            return
        available_actions = []
        for start_ix, end_ix in tokens_ixs:
            available_actions.append(
                Action(
                    f"Create entity using tokens in span '{report.get_context(start_ix, end_ix)}'",
                    action=complete_tokens_assignment_fun(
                        report, tokens, start_ix, end_ix
                    ),
                )
            )
        get_action(available_actions).action()

    return annotate_new_entity


def edit_entity_fun(entity):
    def edit_entity():
        while True:
            available_actions = [
                AnnotationAction(
                    "Modify entity tokens",
                    AnnotationActionType.EDIT,
                    action=lambda: entity.modify_tokens(),
                ),
                AnnotationAction(
                    "Modify entity annotation",
                    AnnotationActionType.EDIT,
                    action=lambda: entity.annotate_label(),
                ),
                AnnotationAction(
                    "Modify entity relations",
                    AnnotationActionType.EDIT,
                    action=lambda: entity.annotate_relations(),
                ),
                AnnotationAction(
                    "Delete this entity",
                    AnnotationActionType.REMOVE,
                    action=lambda: entity.delete(),
                ),
                AnnotationAction(
                    "Finish editing entity and exit", AnnotationActionType.EXIT
                ),
            ]

            selected_action = get_action(
                available_actions,
                prompt=f"You can now edit the entity {highlight(entity.stringify())}. Please select an action:",
            )
            if selected_action.action_type is AnnotationActionType.EXIT:
                if entity.highlight_status is not EntityHighlightStatus.NEW:
                    entity.highlight_status = EntityHighlightStatus.EDITED
                    entity.annotated_by.add(getpass.getuser())
                return
            elif selected_action.action_type is AnnotationActionType.REMOVE:
                selected_action.action()
                return
            else:
                selected_action.action()

    return edit_entity


def annotate_additional_entities(report):
    while True:
        (
            annotated_unchanged_ixs,
            annotated_new_ixs,
            annotated_edited_ixs,
            unannotated_ixs,
        ) = report.get_spans()

        header_str = f"Annotating report {report.folder_id}/{report.patient_id}/{report.study_id}"
        max_str_len = len(header_str)
        if len(unannotated_ixs) > 0:
            unannotated_str = f"There are {len(unannotated_ixs)} unannotated tokens (marked {highlight('red', color=Styles.RED)}) in this report. Please annotate them if appropriate"
            max_str_len = max(max_str_len, len(strip_highlight(unannotated_str)))
        if len(annotated_unchanged_ixs) > 0:
            num_unchanged_entities = len(
                report.get_entities_by_highlight_status(EntityHighlightStatus.UNCHANGED)
            )
            unchanged_str = f"There are {num_unchanged_entities} previously existing entities (marked {highlight('cyan', color=Styles.CYAN)}) in this report."
            max_str_len = max(max_str_len, len(strip_highlight(unchanged_str)))
        if len(annotated_new_ixs) > 0:
            num_new_entities = len(
                report.get_entities_by_highlight_status(EntityHighlightStatus.NEW)
            )
            new_str = f"There are {num_new_entities} newly added entities (marked {highlight('green', color=Styles.GREEN)}) in this report."
            max_str_len = max(max_str_len, len(strip_highlight(new_str)))
        if len(annotated_edited_ixs) > 0:
            num_edited_entities = len(
                report.get_entities_by_highlight_status(EntityHighlightStatus.EDITED)
            )
            edited_str = f"There are {num_edited_entities} edited entities (marked {highlight('violet', color=Styles.VIOLET)}) in this report."
            max_str_len = max(max_str_len, len(strip_highlight(edited_str)))

        sep_str = "#" * min(max_str_len, terminal_len() - 2)
        print(sep_str)
        print(header_str)
        if len(unannotated_ixs):
            print(unannotated_str)
        if len(annotated_unchanged_ixs):
            print(unchanged_str)
        if len(annotated_new_ixs):
            print(new_str)
        if len(annotated_edited_ixs):
            print(edited_str)
        print(sep_str)
        highlighted_report = highlight_words(
            report.text, unannotated_ixs, color=Styles.RED
        )
        highlighted_report = highlight_words(
            highlighted_report, annotated_unchanged_ixs, color=Styles.CYAN
        )
        highlighted_report = highlight_words(
            highlighted_report, annotated_new_ixs, color=Styles.GREEN
        )
        highlighted_report = highlight_words(
            highlighted_report, annotated_edited_ixs, color=Styles.VIOLET
        )
        print_wrap(highlighted_report, limit=200, coef=1.5)

        available_actions = []
        if len(unannotated_ixs):
            available_actions.append(
                AnnotationAction(
                    "Add new entity",
                    AnnotationActionType.NEW,
                    action=annotate_new_entity_fun(report),
                )
            )
        for _, entity in report.entities.items():
            available_actions.append(
                AnnotationAction(
                    f"Edit/delete entity {highlight(entity.stringify(), color=entity_highlight_colour_dict[entity.highlight_status])}",
                    AnnotationActionType.EDIT,
                    action=edit_entity_fun(entity),
                )
            )
        available_actions.append(
            AnnotationAction(
                f"Mark this report as complete/done and continue",
                AnnotationActionType.EXIT,
            )
        )

        selected_action = get_action(available_actions)
        if selected_action.action_type is AnnotationActionType.EXIT:
            report.commit_entities()
            desired_annotation_status = get_enum(
                f"Please confirm annotation status (annotated: done, tentative: further review needed,\n  unannotated: continue annotating)",
                AnnotationStatus,
                AnnotationStatus.ANNOTATED,
            )
            if desired_annotation_status is AnnotationStatus.UNANNOTATED:
                continue
            return desired_annotation_status
        else:
            selected_action.action()
            print()
            print()


def exit_program():
    print()
    print("Preparing to exit program, cleaning up and terminating...")
    if not EXIT_DOUBLE_INSTANCE:
        print("Removing lock file")
        os.remove(LOCK_FILE)
    print("Cleanup done, goodbye!")


def save_annotations(reports, filename=None):
    entities = []
    for _, report in reports.items():
        for _, entity in report.entities.items():
            if entity.annotation_status is not AnnotationStatus.UNANNOTATED:
                entity_tuple = entity.to_tuple()
                entities.append(entity_tuple)
    if filename is None:
        filename = ANNOTATIONS_FILE
    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerows(entities)


def save_completed_reports(completed_reports, filename=None):
    reports = []
    for study_id, annotation_status in completed_reports.items():
        reports.append((study_id, annotation_status.value))
    if filename is None:
        filename = COMPLETED_REPORTS_FILE
    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerows(reports)


if __name__ == "__main__":
    print_welcome()
    try:
        # Make sure that only one user is using Annotate at a time
        get_lock()

        # Determine how to annotate
        mode = get_enum(
            "Please select the mode in which you would like to annotate",
            AnnotationModes,
            default=AnnotationModes.ANNOTATE,
        )
        set_mode(mode)

        # Determine what to annotate
        dataset_portion = get_enum(
            "Please select which dataset portion would you like to annotate",
            DatasetPortion,
        )
        set_dataset(dataset_portion)

        # Load the radgraph reports and entities
        completed_reports = load_completed_reports()
        radgraph_reports = load_radgraph(completed_reports)

        # Load previously done annotations
        radgraph_reports = load_annotations(radgraph_reports)
        print()

        # Allow labelling of only unannotated or tentative records
        if mode is not AnnotationModes.EDIT:
            desired_annotation_status = get_enum(
                "Please select which entities would you like to annotate",
                AnnotationStatus,
                AnnotationStatus.UNANNOTATED,
            )
            print()
        print()

        while True:
            if mode is AnnotationModes.EDIT:
                desired_study_id = get_str(
                    "Please enter the study ID of the report which you want to edit"
                )
                study_id_found = False

            for _, current_report in radgraph_reports.items():
                if mode is AnnotationModes.EDIT:
                    if current_report.study_id == desired_study_id:
                        study_id_found = True
                    else:
                        continue

                current_annotations = current_report.entities

                changed_at_least_one = False

                for entity_id, entity in current_annotations.items():
                    if (
                        mode is AnnotationModes.EDIT
                        or entity.annotation_status is not desired_annotation_status
                    ):
                        # Found existing annotation which should not be re-annotated
                        continue

                    changed_at_least_one = True

                    entity.annotate_label(show_header=True)

                    save_annotations(radgraph_reports)
                    print(
                        highlight("Successfully saved annotation", color=Styles.GREEN)
                    )
                    print()
                    print()

                if mode is not AnnotationModes.EDIT and (
                    (
                        current_report.study_id not in completed_reports
                        and desired_annotation_status
                        is not AnnotationStatus.UNANNOTATED
                    )
                    or (
                        current_report.study_id in completed_reports
                        and not changed_at_least_one
                        and completed_reports[current_report.study_id]
                        is not desired_annotation_status
                    )
                ):
                    continue

                selected_report_annotation_status = annotate_additional_entities(
                    current_report
                )
                completed_reports[
                    current_report.study_id
                ] = selected_report_annotation_status
                save_annotations(radgraph_reports)
                save_completed_reports(completed_reports)
                print(highlight("Successfully saved annotation", color=Styles.GREEN))
                print()
                print()

            if mode is not AnnotationModes.EDIT:
                break
            elif not study_id_found:
                print(
                    highlight(
                        "ERROR: Requested study ID not found. Please try a different one.",
                        color=Styles.RED,
                    )
                )

    finally:
        exit_program()
