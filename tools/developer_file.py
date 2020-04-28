## DEPENDENCY LIST: DICTIONARY OF CODES WHICH CAN ONLY BE CALLED IN COMBINATION WITH OTHER CODES
def load_code_dependencies():

    # e.g. 'ic_wave_fp': {'StixReDist': [ {'ic_coup': 'iccoup'}, {'ic_wave_solver': 'any'} ]}:
    # StixReDist has to be run with iccoup AND any of the ic_wave_solvers, 

    dependencies = {'ec_wave_solver'    : None,
                    'ic_coup'           : None,
                    'ic_wave_solver'    : None,
                    'ic_wave_fp'        : {'StixReDist': [ {'ic_wave_solver': 'any'} ]},
                    'nbi_source'        : None,
                    'nbi_fp'            : None, 
                    #'nbi_fp'            : {'risk': [{'nbi_source': 'nemo bbnbi'}]},
                    'nuclear_source'    : None,
                    'nuclear_fp'        : None,
                    'fill_core_sources' : None,
                    'fill_core_profiles': None}
    return dependencies

## ADDITIONAL INPUT ARGUMENTS: CODES WHICH NEED ADDITIONAL INPUT ARGUMENTS (E.G. DOUBLE OR INTEGER)
def load_add_arg():
    add_arg = {'risk'  : ['dt_required'], 
               'spot'  : ['dt_required'],  
               'pion'  : ['tbegin','tend','dt_required'],  
               'iccoup': ['ic_wave_nr_toroidal_modes'],
               'bbnbi'  :['fokker_flag']}
    return add_arg
