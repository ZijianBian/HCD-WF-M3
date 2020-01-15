## DEPENDENCY LIST: dictionary of codes which can only be called in combination with other codes
def load_code_dependencies():

    # e.g. 'ic_wave_fp':        {'StixReDist': [ {'ic_coup': 'iccoup'},  {'ic_wave_solver': 'any'} ]},  StixReDist has to be run with iccoup AND any of the ic_wave_solvers, 
    

    dependencies = {'ec_wave_solver':     None,
                    'ic_coup':           None,
                    'ic_wave_solver':    None,
                    'ic_wave_fp':        {'StixReDist': [ {'ic_wave_solver': 'any'} ]},
                    'nbi_source':        None,
                    'nbi_fp':  None, 
                 #   'nbi_fp':            {'risk': [{'nbi_source': 'nemo bbnbi'}]},
                    'nuclear_source':    None,
                    'nuclear_fp':        None,
                    'hcd2core_sources':  None,
                    'hcd2core_profiles': None}
    return dependencies


## ADDITIONAL INPUT ARGUMENTS: list of codes which need additional input arguments (e.g. double or integer)
def load_add_arg():
    add_arg = {'risk': ['dt_required'], 
               'spot': ['dt_required'],  
               'pion': ['tbegin','tend','dt_required'],  
               'iccoup': ['ic_wave_nr_toroidal_modes'],
               'bbnbi':['fokker_flag']}
    return add_arg
