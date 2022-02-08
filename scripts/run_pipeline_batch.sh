#!/bin/bash
#SBATCH -p normal
#SBATCH -J uncertainty
#SBATCH -o uncertainty-%j.out
#SBATCH -t 24-00:00:00
#SBATCH -n 1
#SBATCH -N 1
#SBATCH --gres=gpu:volta:1
#SBATCH --mem=300gb

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"
echo ""
cat $0
echo ""

export DIR="$(dirname "$(pwd)")"

source /etc/profile
module load anaconda/2021a
source activate uncertainty_guided_env

# bash JTVAE_data_vocab_generation.sh
# bash JTVAE_data_preprocess.sh
# bash JTVAE_train_jtnnvae-prop_step2_train.sh
# bash JTVAE_test_jtnnvae-prop.sh
# bash JTVAE_uncertainty_guided_optimization_gradient_ascent.sh
bash JTVAE_uncertainty_guided_optimization_train_stats.sh
