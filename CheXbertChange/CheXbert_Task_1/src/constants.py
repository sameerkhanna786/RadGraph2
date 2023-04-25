NUM_EPOCHS = 25       #Number of epochs to train for
BATCH_SIZE = 13       #Change this depending on GPU memory
NUM_WORKERS = 1       #A value of 0 means the main process loads the data
LEARNING_RATE = 0.000015 #NN learning rate
LOG_EVERY = 200       #iterations after which to log status during training
VALID_NITER = 12    #iterations after which to evaluate model and possibly save (if dev performance is a new max)
PRETRAIN_PATH = None  #path to pretrained model, such as BlueBERT or BioBERT
PAD_IDX = 0           #padding index as required by the tokenizer 

CONDITIONS = ['No Change', 'Change']
CLASS_MAPPING = {1: "Yes"}



