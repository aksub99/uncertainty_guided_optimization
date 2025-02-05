import os,sys, statistics
import numpy as np
import pandas as pd
import json
import pickle as pkl
import argparse
import time
from rdkit import RDLogger
import torch

from JTVAE.fast_jtnn import *
from utils import optimization_utils as ou

lg = RDLogger.logger() 
lg.setLevel(RDLogger.CRITICAL)
path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Agument parser')
    parser.add_argument('--experiment_name', default="20210101", type=str, help='Name of experiment log file')
    parser.add_argument('--target_property', default='final_logP', type=str, help='Black box objective to optimize (eg., final_logP)')
    parser.add_argument('--model_type', default='JTVAE', type=str, help='CharVAE|JTVAE')
    parser.add_argument('--optimization_method', default=None, type=str, help='Method to optimize objects: [gradient_ascent|bayesian_optimization]')
    parser.add_argument('--batch_size', default=128, type=int, help='Batch size')

    parser.add_argument('--mode_generation_starting_points', default="random", type=str, help='Method to generate starting points [random|low_property_objects]')
    parser.add_argument('--starting_property_upper_bound', default=None, type=float, help='Property upper bound when selecting starting positions [low_property_objects]')
    parser.add_argument('--num_starting_points', default=1000, type=int, help='Number of starting points for search')

    parser.add_argument('--GA_number_optimization_steps', default=None, type=int, help='Number of gradient steps during optimization')
    parser.add_argument('--GA_alpha', default=None, type=float, help='Coefficient scaling gradient step during gradient ascent')
    parser.add_argument('--GA_uncertainty_threshold', default=None, type=str, help='Uncertainty upper bound (passed as percentile of train values) [No_constraint|max|P99|P95|P90]')
    parser.add_argument('--GA_keep_all_generated', default=False, action='store_true', help='Whether to do stats on all generated objects Vs just last set obtained (GA)')

    parser.add_argument('--BO_number_objects_generated', default=None, type=int, help='Number of objects generated by Bayesian optimization')
    parser.add_argument('--BO_uncertainty_mode', default=None, type=str, help='Mode to include uncertainty in BO [Uncertainty_censoring|Penalized_objective]')
    parser.add_argument('--BO_uncertainty_threshold', default=None, type=str, help='Uncertainty upper bound (passed as percentile of train values) [No_constraint|max|P99|P95|P90]')
    parser.add_argument('--BO_uncertainty_coeff', default=None, type=float, help='Uncertainty penalty coeff in surrogate model')
    parser.add_argument('--BO_abs_bound', default=None, type=float, help='Bounds of space to search for new points')
    parser.add_argument('--BO_acquisition_function', default=None, type=str, help='Type of acquisition function')
    parser.add_argument('--BO_default_value_invalid', default=None, type=float, help='Imputation in BO when generating an invalid molecule')

    parser.add_argument('--decoder_uncertainty_method', default="MI_Importance_Sampling", type=str, help='Method to estimate uncertainty [MI_Importance_sampling, NLL_prior]')
    parser.add_argument('--decoder_num_sampled_models', default=10, type=int, help='Number of samples from model parameters')
    parser.add_argument('--decoder_num_sampled_outcomes', default=40, type=int, help='Number of sequences sampled to estimate decooder uncertainty')
    
    parser.add_argument('--model_checkpoint', default=None, type=str, help='Checkpoint of PVAE to be used')
    parser.add_argument('--vocab_path', default=None, type=str, help='Path to vocab to be used')
    parser.add_argument('--model_decoding_mode', default=None, type=str, help='Method to decode from latent [topk|max|sample]')
    parser.add_argument('--model_decoding_topk_value', default=None, type=int, help='Number of elements considered in topk decoding approach')
    parser.add_argument('--seed', default=0, type=int, help='Random seed for reproducibility')
    args = parser.parse_args()
    
    torch.manual_seed(args.seed)
    model_path = os.path.dirname(args.model_checkpoint)

    if args.model_type=='JTVAE':    
        vocab = [x.strip("\r\n ") for x in open(args.vocab_path)] 
        vocab = Vocab(vocab)
        params = json.load(open(model_path+os.sep+"parameters.json","r"))
        if 'prop' not in params.keys():
            model = JTNNVAE(vocab=vocab, **params)
        else:
            model = JTNNVAE_prop(vocab=vocab, **params)
        dict_buffer = torch.load(args.model_checkpoint)
        model.load_state_dict(dict_buffer)
        model = model.to(device)
        with open(dir_path+os.sep+'JTVAE/data/opd/train.txt') as f:
            train_dataset = [line.strip("\r\n ").split()[0] for line in f]
        print("train dataset length: ", len(train_dataset))
        # with open(dir_path+os.sep+'JTVAE/data/opd/test.txt') as f:
        #     test_dataset = [line.strip("\r\n ").split()[0] for line in f]
        hidden_dim = model.latent_size*2
    
    elif args.model_type=='CharVAE':
        pass 

    print("Sample starting positions")
    uncertainty_list_full = []
    # uncertainty_array_full = np.empty(shape=(len(train_dataset),))
    for index in range(0, len(train_dataset), args.num_starting_points):
        starting_objects_latent_embeddings, starting_objects_properties, starting_objects_smiles = ou.starting_objects_latent_embeddings(
                                                                                                        model=model, 
                                                                                                        data=train_dataset, 
                                                                                                        mode=args.mode_generation_starting_points,
                                                                                                        num_objects_to_select=args.num_starting_points, 
                                                                                                        batch_size=args.batch_size, 
                                                                                                        property_upper_bound=args.starting_property_upper_bound,
                                                                                                        model_type=args.model_type,
                                                                                                        index=index)

        print("Perform optimization in latent space")
        start_time=time.time()
        
        uncertainty_array = ou.get_stats_train_data(
                                model=model,
                                starting_objects_latent_embeddings=starting_objects_latent_embeddings,
                                num_sampled_models=args.decoder_num_sampled_models,
                                uncertainty_decoder_method=args.decoder_uncertainty_method,
                                num_sampled_outcomes=args.decoder_num_sampled_outcomes,
                                model_decoding_mode=args.model_decoding_mode,
                                model_decoding_topk_value=args.model_decoding_topk_value,
                                batch_size=args.batch_size,
                                model_type=args.model_type
                                )
    
        uncertainty_list_full.extend(list(uncertainty_array))
        # uncertainty_array_full = np.append(uncertainty_array_full, uncertainty_array)
        # print(uncertainty_array_full, uncertainty_array_full.shape)
        del starting_objects_latent_embeddings
        del starting_objects_properties
        del starting_objects_smiles
        
        end_time=time.time()
        duration=end_time-start_time
    train_stats = ou.compute_stats(np.array(uncertainty_list_full))
    print("train stats: ", train_stats)
