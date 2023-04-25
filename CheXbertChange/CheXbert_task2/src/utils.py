import copy
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import json
from models.bert_labeler import bert_labeler
from bert_tokenizer import tokenize
from sklearn.metrics import f1_score, confusion_matrix, accuracy_score
from statsmodels.stats.inter_rater import cohens_kappa
from transformers import BertTokenizer
from constants import *

def compute_train_weights(train_path):
    """Compute class weights for rebalancing rare classes
    @param train_path (str): A path to the training csv file

    @returns weight_arr (torch.Tensor): Tensor of shape (train_set_size), containing
                                        the weight assigned to each training example 
    """
    df = pd.read_csv(train_path)
    cond_weights = {}
    for cond in CONDITIONS:
            col = df[cond]
            val_counts = col.value_counts()
            weights = {}
            weights['0.0'] = len(df) / val_counts[0]
            weights['1.0'] = len(df) / val_counts[1]
            cond_weights[cond] = weights
        
    weight_arr = torch.zeros(len(df))
    for i in range(len(df)):     #loop over training set
        for cond in CONDITIONS:  #loop over all conditions
            label = str(df[cond].iloc[i])
            weight_arr[i] += cond_weights[cond][label] #add weight for given class' label
        
    return weight_arr

def generate_attention_masks(batch, source_lengths, device):
    """Generate masks for padded batches to avoid self-attention over pad tokens
    @param batch (Tensor): tensor of token indices of shape (batch_size, max_len)
                           where max_len is length of longest sequence in the batch
    @param source_lengths (List[Int]): List of actual lengths for each of the
                           sequences in the batch
    @param device (torch.device): device on which data should be

    @returns masks (Tensor): Tensor of masks of shape (batch_size, max_len)
    """
    masks = torch.ones(batch.size(0), batch.size(1), dtype=torch.float)
    for idx, src_len in enumerate(source_lengths):
        masks[idx, src_len:] = 0
    return masks.to(device)


def compute_positive_f1(y_true, y_pred):
    """Compute the positive F1 score
    @param y_true (list): List of 6 tensors each of shape (dev_set_size)
    @param y_pred (list): Same as y_true but for model predictions 

    @returns res (list): List of 6 scalars
    """
    for j in range(len(y_true)):
        y_true[j][y_true[j] == 0] = 0
        y_pred[j][y_pred[j] == 0] = 0

    res = []
    for j in range(len(y_true)):
        res.append(f1_score(y_true[j], y_pred[j], pos_label=1))

    return res
        
def compute_positive_acc(y_true, y_pred):
    """Compute the positive acc score
    @param y_true (list): List of 6 tensors each of shape (dev_set_size)
    @param y_pred (list): Same as y_true but for model predictions 

    @returns res (list): List of 6 scalars
    """
    for j in range(len(y_true)):
        y_true[j][y_true[j] == 0] = 0
        y_pred[j][y_pred[j] == 0] = 0

    res = []
    for j in range(len(y_true)):
        res.append(accuracy_score(y_true[j], y_pred[j]))

    return res
    
    
    
    
def evaluate(model, dev_loader, device, return_pred=False):
    """ Function to evaluate the current model weights
    @param model (nn.Module): the labeler module 
    @param dev_loader (torch.utils.data.DataLoader): dataloader for dev set  
    @param device (torch.device): device on which data should be
    @param return_pred (bool): whether to return predictions or not

    @returns res_dict (dictionary): dictionary with key 'positive', with values 
                            being lists of length 6 with each element in the 
                            lists as a scalar. If return_pred is true then a 
                            tuple is returned with the aforementioned dictionary 
                            as the first item, a list of predictions as the 
                            second item, and a list of ground truth as the 
                            third item
    """
    
    was_training = model.training
    model.eval()
    y_pred = [[] for _ in range(len(CONDITIONS))]
    y_true = [[] for _ in range(len(CONDITIONS))]
    loss_values = []
    
    with torch.no_grad():
        for i, data in enumerate(dev_loader, 0):
            batch = data['imp'] #(batch_size, max_len)
            batch = batch.to(device)
            batch_size = batch.shape[0]
            label = data['label'] #(batch_size, 14)
            label = label.permute(1, 0).to(device)
            src_len = data['len']
            batch_size = batch.shape[0]
            attn_mask = generate_attention_masks(batch, src_len, device)

            out = model(batch, attn_mask)
            loss_func = nn.BCEWithLogitsLoss()
            loss_val = 0.0
            for j in range(len(out)):
                outJ = torch.sigmoid(out[j])
                outJ = outJ.to('cpu') #move to cpu for sklearn
                curr_y_pred = (outJ > 0.5).long()
                y_pred[j].append(curr_y_pred)
                y_true[j].append(label[j].to('cpu'))
                loss = loss_func(out[j].squeeze().to(device), label[j].float().to(device))
                loss_val +=loss
            loss_values.append(loss_val.item()/batch_size)
            if (i+1) % 200 == 0:
                print('Evaluation batch no: ', i+1)
                
    for j in range(len(y_true)):
        y_true[j] = torch.cat(y_true[j], dim=0)
        y_pred[j] = torch.cat(y_pred[j], dim=0)

    if was_training:
        model.train()
    positive_f1 = compute_positive_f1(copy.deepcopy(y_true), copy.deepcopy(y_pred))
    accuracy = compute_positive_acc(copy.deepcopy(y_true), copy.deepcopy(y_pred))

    for j in range(len(y_pred)):
        cond = CONDITIONS[j]
        #avg = weighted_avg([negation_f1[j], uncertain_f1[j], positive_f1[j]], f1_weights[cond])
        avg = positive_f1[j]
        weighted.append(avg)
        mat = confusion_matrix(y_true[j], y_pred[j])
        #uncomment if you want to print the confusion matrix duing evaluation
        #print(mat)

    res_dict = {'positive': positive_f1,
                 'accuracy': accuracy,
                 'loss':np.mean(np.array(loss_values))}
    
    if return_pred:
        return res_dict, y_pred, y_true
    else:
        return res_dict

def test(model, checkpoint_path, test_ld):
    """Evaluate model on test set. 
    @param model (nn.Module): labeler module
    @param checkpoint_path (string): location of saved model checkpoint
    @param test_ld (dataloader): dataloader for test set
    """
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if torch.cuda.device_count() > 1:
        print("Using", torch.cuda.device_count(), "GPUs!")
        model = nn.DataParallel(model) #to utilize multiple GPU's
    model = model.to(device)

    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])

    print("Doing evaluation on test set\n")
    metrics = evaluate(model, test_ld, device, f1_weights)
    
    for j in range(len(CONDITIONS)):
        print('%s f1: %.3f' % (CONDITIONS[j], metrics['positive'][j]))
    for j in range(len(CONDITIONS)):
        print('%s  accuracy: %.3f' % (CONDITIONS[j], metrics['accuracy'][j]))

    pos_macro_avg = np.mean(metrics['positive'])
    print(" positive macro avg: %.3f" % (pos_macro_avg))
    

def label_report_list(checkpoint_path, report_list):
    """ Evaluate model on list of reports.
    @param checkpoint_path (string): location of saved model checkpoint
    @param report_list (list): list of report impressions (string)
    """
    imp = pd.Series(report_list)
    imp = imp.str.strip()
    imp = imp.replace('\n',' ', regex=True)
    imp = imp.replace('[0-9]\.', '', regex=True)
    imp = imp.replace('\s+', ' ', regex=True)
    imp = imp.str.strip()
    
    model = bert_labeler()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if torch.cuda.device_count() > 1:
        print("Using", torch.cuda.device_count(), "GPUs!")
        model = nn.DataParallel(model) #to utilize multiple GPU's
    model = model.to(device)
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    y_pred = []
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    new_imps = tokenize(imp, tokenizer)
    with torch.no_grad():
        for imp in new_imps:
            # run forward prop
            imp = torch.LongTensor(imp)
            source = imp.view(1, len(imp))
            
            attention = torch.ones(len(imp))
            attention = attention.view(1, len(imp))
            out = model(source.to(device), attention.to(device))

            # get predictions
            result = {}
            for j in range(len(out)):
                curr_y_pred = out[j].argmax(dim=1) #shape is (1)
                result[CONDITIONS[j]] = CLASS_MAPPING[curr_y_pred.item()]
            y_pred.append(result)
    return y_pred

