export DIR="$(dirname "$(pwd)")"
#conda env update --file ${DIR}'/uncertainty_guided_env.yml'
#source activate uncertainty_guided_env
export PYTHONPATH=${PYTHONPATH}:${DIR}

python ../JTVAE/fast_molvae/data_preprocess.py \
                --train ${DIR}'/JTVAE/data/opd_small_large/train.txt' \
                --split 100 --jobs 40 \
                --output ${DIR}'/JTVAE/data/opd_small_large_processed'
