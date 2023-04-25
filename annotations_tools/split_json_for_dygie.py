import json

filename = input()

with open(filename, 'r') as f:
    reports = json.load(f)

report_strs = []
for report in reports:
    report['ner'] = report['predicted_ner']
    del report['predicted_ner']
    report['relations'] = report['predicted_relations']
    del report['predicted_relations']
    report_strs.append(json.dumps(report))

with open(f'{filename[:-5]}_split.json', 'w') as f:
    f.write("\n".join(report_strs))