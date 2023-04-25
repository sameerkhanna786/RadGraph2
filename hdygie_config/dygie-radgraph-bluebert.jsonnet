local template = import "template.libsonnet";

template.DyGIE {
  bert_model: "bionlp/bluebert_pubmed_mimic_uncased_L-12_H-768_A-12",
  heirarchy: "",
  cuda_device: 0,
  data_paths: {
    train: "./data/dygie_train.json",
    validation: "./data/dygie_dev.json",
    test: "./data/dygie_test.json",
  },
  loss_weights: {
    ner: 0.2,
    relation: 1.0,
    coref: 0.0,
    events: 0.0
  },
  target_task: "relation",
  model:{
    "type": "from_archive",
    "archive_file": "./models/dygie-radgraph-bluebert-pretrain"
  },
  trainer +: {
    num_epochs: 30,
    optimizer: {
      type: 'adamw',
      lr: 2e-4,
      weight_decay: 0.0,
      parameter_groups: [
        [
          ['_embedder'],
          {
            lr: 8e-6,
            weight_decay: 0.01,
            finetune: true,
          },
        ],
      ],
    },
    learning_rate_scheduler: {
      type: 'slanted_triangular'
    }
  }
}