local template = import "template.libsonnet";

template.DyGIE {
  bert_model: "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
  heirarchy: "./data/org.txt",
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
  trainer +: {
    num_epochs: 30,
    optimizer: {
      type: 'adamw',
      lr: 1e-3,
      weight_decay: 0.0,
      parameter_groups: [
        [
          ['_embedder'],
          {
            lr: 5e-5,
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
