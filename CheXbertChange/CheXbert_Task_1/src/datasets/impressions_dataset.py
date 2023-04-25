import torch
import pandas as pd
import numpy as np
from bert_tokenizer import load_list
from torch.utils.data import Dataset, DataLoader

class ImpressionsDataset(Dataset):
        """The dataset to contain report impressions and their labels."""
        
        def __init__(self, csv_path, list_path):
                """ Initialize the dataset object
                @param csv_path (string): path to the csv file containing labels
                @param list_path (string): path to the list of encoded impressions
                """
                self.df = pd.read_csv(csv_path)
                # Conditions are No Change and Change
                self.df =  self.df[['No Change','Change']]
                self.encoded_imp = load_list(path=list_path)

        def __len__(self):
                """Compute the length of the dataset

                @return (int): size of the dataframe
                """
                return self.df.shape[0]

        def __getitem__(self, idx):
                """ Functionality to index into the dataset
                @param idx (int): Integer index into the dataset

                @return (dictionary): Has keys 'imp', 'label' and 'len'. The value of 'imp' is
                                      a LongTensor of an encoded impression. The value of 'label'
                                      is a LongTensor containing the labels and 'the value of
                                      'len' is an integer representing the length of imp's value
                """
                if torch.is_tensor(idx):
                        idx = idx.tolist()
                label = self.df.iloc[idx].to_numpy()
                label = torch.LongTensor(label)
                imp = self.encoded_imp[idx]
                imp = torch.LongTensor(imp)
                return {"imp": imp, "label": label, "len": imp.shape[0]}