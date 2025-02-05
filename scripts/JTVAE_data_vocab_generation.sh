export DIR="$(dirname "$(pwd)")"
# conda env update --file ${DIR}'/uncertainty_guided_env.yml'
# source activate uncertainty_guided_env
export PYTHONPATH=${PYTHONPATH}:${DIR}

export data_folder=${DIR}'/JTVAE/data/opd_small_large/train.txt'
export vocab_location=${DIR}'/JTVAE/data/opd_small_large/new_vocab.txt'
    
python ../JTVAE/fast_jtnn/mol_tree.py --data_folder ${data_folder} --vocab_location ${vocab_location}
