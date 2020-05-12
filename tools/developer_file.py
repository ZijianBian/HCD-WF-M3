## ADDITIONAL INPUT ARGUMENTS: CODES WHICH NEED ADDITIONAL INPUT ARGUMENTS (E.G. DOUBLE OR INTEGER)
def load_add_arg():
    add_arg = {'risk'  : ['dt_required'], 
               'spot'  : ['dt_required'],  
               'pion'  : ['tbegin','tend','dt_required'],  
               'iccoup': ['ic_wave_nr_toroidal_modes'],
               'bbnbi'  :['fokker_flag']}
    return add_arg
