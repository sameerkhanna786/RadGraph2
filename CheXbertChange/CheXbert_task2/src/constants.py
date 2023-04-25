NUM_EPOCHS = 5      #Number of epochs to train for
BATCH_SIZE = 10       #Change this depending on GPU memory
NUM_WORKERS = 1       #A value of 0 means the main process loads the data
LEARNING_RATE = 0.000001
LOG_EVERY = 200       #iterations after which to log status during training
VALID_NITER = 20   #iterations after which to evaluate model and possibly save (if dev performance is a new max)
PRETRAIN_PATH = None #path to pretrained model, such as BlueBERT or BioBERT
PAD_IDX = 0           #padding index as required by the tokenizer 

CONDITIONS = ['No Change', 'Appearance', 'Disappearance', "Displacement", "Worsening", "Improvement"]
CLASS_MAPPING = {1: "Yes"}
#CLASS_MAPPING = {0: "No", 1: "Yes"}
