from functools import partial
from models.CNTFET import run_rnn_sim as run_CNTFET_sim 
from models.CNTFET import get_adjusted_simulation_data as CNTFET_DB_postprocess
from models.CNTFET import SimulationConfig as CNTSimConfig 
from models.HFET import get_simulation_data
from models.HFET import run_AE_sim as run_HFET_AE_sim

run_CNTFET_sim = partial(run_CNTFET_sim, config=CNTSimConfig)

MODEL_CONFIG = {
    'CNTFET': {
        'simulation_func': {'rnn': run_CNTFET_sim},
        'device_params': ['tox', 'Lg', 'eps_ox', 'd_cnt', 'V_th', 'sca_flag'],
        'postprocess': CNTFET_DB_postprocess,
    },
    # 'ANOTHERDEVICE': run_ANOTHERDEVICE_sim,
    'HFET': {
        'simulation_func': {'autoencoder': run_HFET_AE_sim},
        'device_params': ['Lsg', 'Lgd', 'Lg', 'hpas', 'hAlGaN', 'hch', 'hg'],
        'postprocess': get_simulation_data,
    },
}