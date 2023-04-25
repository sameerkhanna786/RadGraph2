This folder contains our models for the adaptation of CheXbert to change prediction for Tasks 1 and 2.

This code is adapted from the original CheXbert code, that can be found on their GitHub https://github.com/stanfordmlgroup/CheXbert. We modified the original code in order to fit it to out specific tasks (i.e. we changed the 14 conditions to the different kinds of change, the possible classes for each linear head, and the loss function -- from categorical to binary cross entropy), and to compute the metrics we wanted (F-1 and accuracy).

Both subfolders CheXbert_task1 and CheXbert_task2 contain modified code and the two notebooks contain code to go trough a full training of the best model we have found for both tasks. For the model in Task 1 no reweighting is present in the notebook (and, based on our results, we suggest to run the model without the pre-trained CheXbert weights we obtianed from the CheXbert GitHub), while the notebook for Task 2 includes how to perform reweighting (and, based on performance, we suggest to used the pre-trained CheXbert weights). 
For both models, to train the hyperparameters, it will be necessary to modify the constants.py file in the src sub-folder for both Task 1 and Task 2.

The full citation for the original CheXbert code from their GitHub repository is: @misc{smit2020chexbert,
	title={CheXbert: Combining Automatic Labelers and Expert Annotations for Accurate Radiology Report Labeling Using BERT},
	author={Akshay Smit and Saahil Jain and Pranav Rajpurkar and Anuj Pareek and Andrew Y. Ng and Matthew P. Lungren},
	year={2020},
	eprint={2004.09167},
	archivePrefix={arXiv},
	primaryClass={cs.CL}
}
