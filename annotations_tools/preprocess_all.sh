# Copy over files
# Script expects to locate all data fies in the ../data folder
cp ../data/radgraph_train_annotations.csv ./radgraph_train_annotations.csv
cp ../data/radgraph_train_annotated_reports.csv ./radgraph_train_annotated_reports.csv
cp ../data/radgraph_dev_annotations.csv ./radgraph_dev_annotations.csv
cp ../data/radgraph_dev_annotated_reports.csv ./radgraph_dev_annotated_reports.csv
cp ../data/radgraph_test_annotations.csv ./radgraph_test_annotations.csv
cp ../data/radgraph_test_annotated_reports.csv ./radgraph_test_annotated_reports.csv
cp ../data/radgraph_train.json ./radgraph_train.json
cp ../data/radgraph_dev.json ./radgraph_dev.json
cp ../data/radgraph_test.json ./radgraph_test.json

# Run mimic_chexpert_split.py
echo test | python3 mimic_chexpert_split.py

# Run graphconverter.py
printf "train\nradgraph_train" | python3 graphconverter.py
printf "dev\nradgraph_dev" | python3 graphconverter.py
printf "test\nradgraph_test" | python3 graphconverter.py
printf "test\nradgraph_test_mimic" | python3 graphconverter.py
printf "test\nradgraph_test_chexpert" | python3 graphconverter.py

# Run chexconverter.py
printf "train\nradgraph_train" | python3 chexconverter.py
printf "dev\nradgraph_dev" | python3 chexconverter.py
printf "test\nradgraph_test" | python3 chexconverter.py
printf "test\nradgraph_test_mimic" | python3 chexconverter.py
printf "test\nradgraph_test_chexpert" | python3 chexconverter.py

# Run process_dygie.py
python process_dygie.py --reports_json ./radgraph_train_annotations_graphconvert.json --save_path radgraph_train_annotations_graphconvert_processed --model_name pure
python process_dygie.py --reports_json ./radgraph_dev_annotations_graphconvert.json --save_path radgraph_dev_annotations_graphconvert_processed --model_name pure
python process_dygie.py --reports_json ./radgraph_test_annotations_graphconvert.json --save_path radgraph_test_annotations_graphconvert_processed --model_name pure
python process_dygie.py --reports_json ./radgraph_test_mimic_annotations_graphconvert.json --save_path radgraph_test_mimic_annotations_graphconvert_processed --model_name pure
python process_dygie.py --reports_json ./radgraph_test_chexpert_annotations_graphconvert.json --save_path radgraph_test_chexpert_annotations_graphconvert_processed --model_name pure

# Run split_json_for_dygie.py
echo radgraph_train_annotations_graphconvert_processed.json | python3 split_json_for_dygie.py
echo radgraph_dev_annotations_graphconvert_processed.json | python3 split_json_for_dygie.py
echo radgraph_test_annotations_graphconvert_processed.json | python3 split_json_for_dygie.py
echo radgraph_test_mimic_annotations_graphconvert_processed.json | python3 split_json_for_dygie.py
echo radgraph_test_chexpert_annotations_graphconvert_processed.json | python3 split_json_for_dygie.py

# Copy files for Dygie and PL-Marker
cp radgraph_train_annotations_graphconvert_processed_split.json ../data/dygie_train.json
cp radgraph_dev_annotations_graphconvert_processed_split.json ../data/dygie_dev.json
cp radgraph_test_annotations_graphconvert_processed_split.json ../data/dygie_test.json

# Copy files for Dygie MIMIC/CheXpert evauluation
cp radgraph_test_mimic_annotations_graphconvert_processed_split.json ../data/dygie_test_mimic.json
cp radgraph_test_chexpert_annotations_graphconvert_processed_split.json ../data/dygie_test_chexpert.json
cp radgraph_test_mimic_annotations_chexconvert.csv ../data/chexbert_test_mimic.csv
cp radgraph_test_chexpert_annotations_chexconvert.csv ../data/chexbert_test_chexpert.csv

# Copy files for CheXBERT
cp radgraph_train_annotations_chexconvert.csv ../data/chexbert_train.csv
cp radgraph_dev_annotations_chexconvert.csv ../data/chexbert_dev.csv
cp radgraph_test_annotations_chexconvert.csv ../data/chexbert_test.csv