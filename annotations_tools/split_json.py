import json
import math

print("Please enter the name of the file to split")
filename = input()

with open(filename, "r") as f:
    json_data = json.load(f)

print("Please enter the number of partitions")
num_partitions = int(input())


def partition_list(l, num_partitions):
    num_items = math.ceil(len(l) / num_partitions)
    print(
        f"Splitting {len(l)} reports into {num_partitions} partitions of {num_items} each"
    )
    for i in range(0, len(l), num_items):
        yield l[i : i + num_items]


partitions = partition_list(list(json_data.items()), num_partitions)

for i, partition in enumerate(partitions):
    d = dict(partition)
    with open(
        "splits/" + filename.replace(".json", "") + "_" + str(i) + ".json", "w"
    ) as f:
        json.dump(d, f)
