# IMPORT 
import os,imas,sys,copy

actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')
list_of_actors = ['nemo', 'bbnbi','afsi',  'empty_distribution_sources', 
                  'iccoup', 'Cyrano','lion', 'tomcat', 'genray', 'gray', 'empty_waves', 
                  'StixReDist', 'risk', 'spot', 'ascot4serial', 'ascot4parallel', 'empty_distributions', 
                  'hcd2core_sources_mireille', 'hcd2core_profiles']

for name in list_of_actors:
    try:
        sys.path[:0] = [os.path.join(actor_path,name)]
        globals()[name] = getattr(__import__(name), name)
    except:
        print('warning: ', name, ' is not compiled')


# NBI SOURCE CODE--------------------------------------------------------------------------------------
def source_code_nbi(bundle, parameters):
    if parameters['nbi_source'] == 1:
        print('-- NEMO --')
        distribution_sources_nbi_s = nemo(bundle['equilibrium'], bundle['core_profiles'], bundle['nbi'], bundle['distribution_sources'], parameters['fokker_flag'], parameters['nmarker'], (parameters['input_path']+'/input_nemo.xml'))
    elif parameters['nbi_source'] == 2:
        print('--BBNBI--')
        distribution_sources_nbi_s = bbnbi(parameters['fokker_flag'], bundle['nbi'], bundle['wall'], bundle['core_profiles'], bundle['equilibrium'],(parameters['input_path']+'/input_bbnbi.xml') )
        
    else:
 #       distribution_sources_nbi_s = copy.deepcopy(bundle['distribution_sources'])
       distribution_sources_nbi_s = empty_distribution_sources(bundle['core_profiles'])
    return(distribution_sources_nbi_s)



# ALPHA SOURCE CODE--------------------------------------------------------------------------------------
def source_code_alpha(bundle, parameters):
    if parameters['alpha_source'] == 1:
        print('-- AFSI --')
        distribution_sources_a_s = afsi(bundle['equilibrium'], bundle['core_profiles'], bundle['wall'], bundle['distributions'], (parameters['input_path']+'input_afsi.xml'))
    else:
        distribution_sources_a_s = empty_distribution_sources(bundle['core_profiles'])
       # distribution_sources_a_s = copy.deepcopy(bundle['distribution_sources'])
    return(distribution_sources_a_s)


# IC COUPLING AND WAVE SOLVER --------------------------------------------------------------------------------
def iccoup(bundle, parameters):
    if parameters['ic_coup'] == 1:
        print('--- ICCOUP ---')
        waves_coupling = iccoup(bundle['equilibrium'], bundle['ic_antennas'], parameters['ic_wave_nr_toroidal_modes'], (parameters['input_path']+ '/input_iccoup.xml'))

    else: 
        waves_coupling = empty_waves(bundle['core_profiles'])
    return(waves_coupling)


def wave_solver_ic(bundle, parameters):
    if parameters['ic_wave_solver'] == 1:
        print('--- CYRANO ---')
        waves_ic_ws = Cyrano(bundle['equilibrium'], bundle['core_profiles'], bundle['ic_antennas'],bundle['waves'], bundle['distributions'], (parameters['input_path']+ '/input_Cyrano.xml'))

    elif parameters['ic_wave_solver'] == 2:
        print('--- TOMCAT ---')
        waves_ic_ws = tomcat(bundle['equilibrium'], bundle['core_profiles'], bundle['ic_antennas'], bundle['distributions'], (parameters['input_path']+'/input_tomcat.xml'))

    elif parameters['ic_wave_solver'] == 3:
        print('--- LION ---')
        waves_ic_ws = lion(bundle['equilibrium'], bundle['core_profiles'], bundle['ic_antennas'], bundle['waves'],(parameters['input_path']+'/input_lion.xml'))

    else: 
         waves_ic_ws = empty_waves(bundle['core_profiles'])
     #    waves_ic_ws = copy.deepcopy(bundle['waves'])

    return(waves_ic_ws)





# EC WAVE SOLVER ---------------------------------------------------------------------------

def wave_solver_ec(bundle, parameters):

    if parameters['ec_wave_solver'] == 1:
        print('--- GENRAY ---')
        waves_ec_ws = genray(bundle['equilibrium'], bundle['core_profiles'], bundle['ec_antennas'], (parameters['input_path']+'/input_genray.xml'))


    elif parameters['ec_wave_solver'] == 2:
        print('--- GRAY ---')
        waves_ec_ws = gray(bundle['equilibrium'], bundle['core_profiles'], bundle['ec_antennas'], (parameters['input_path']+'/input_gray.xml'))


    else:
        waves_ec_ws = empty_waves(bundle['core_profiles'])
     #   waves_ec_ws = copy.deepcopy(bundle['waves'])

    return(waves_ec_ws)


# FOKKER PLANKS --------------------------------------------------------------------------------


def fokker_plank_ic(bundle, parameters):

    if parameters['ic_wave_fp'] == 1:
        print('--- STIXREDIST ---')
        distributions_fp_w = StixReDist(bundle['equilibrium'], bundle['core_profiles'], bundle['ic_antennas'], bundle['waves'], (parameters['input_path'] + 'input_StixReDist.xml'))

    else:
        distributions_fp_w = empty_distributions(bundle['core_profiles'])
       # distributions_fp_w = copy.deepcopy(bundle['distributions'])
    
    return(distributions_fp_w)
    

def fokker_plank_alpha(bundle, parameters):
        
    if parameters['alpha_fp'] == 2:
        print('--- SPOT ---')
        distributions_fp_s = spot(bundle['equilibrium'], bundle['core_profiles'], bundle['wall'], bundle['nbi'], bundle['distribution_sources'], bundle['distributions'], parameters['dt_required'] , (parameters['input_path'], + '/input_spot.xml'), parameters['mpi_local']) 

    elif parameters['alpha_fp'] == 3:
        print('--- ASCOT 4 SERIAL ---')
        distributions_fp_s = ascot4serial(bundle['core_profiles'], bundle['equilibrium'], bundle['wall'], bundle['distribution_sources'], bundle['distributions'], (parameters['input_path'] + '/input_ascot4serial.xml') )
    
    elif parameters['alpha_fp'] == 4:
        print('--- ASCOT 4 PARALLEL ---')
        distributions_fp_s = ascot4parallel(bundle['core_profiles'], bundle['equilibrium'], bundle['wall'], bundle['distribution_sources'], bundle['distributions'], (parameters['input_path'] + '/input_ascot4parallel.xml'))

    elif parameters['alpha_fp'] == 5:
        print('--- SPOT WITHOUT SOURCE !XML IS NOT CHANGED YET!  ---')
        distributions_fp_s = spot(bundle['equilibrium'], bundle['core_profiles'], bundle['wall'], bundle['nbi'], bundle['distribution_sources'], bundle['distributions'], parameters['dt_required'] , (parameters['input_path'] + '/input_spot.xml'), parameters['mpi_local']) 

    else:
         distributions_fp_s = empty_distributions(bundle['core_profiles'])
     #    distributions_fp_s = copy.deepcopy(bundle['distributions'])
        
    return(distributions_fp_s)


## NBI FP (maybe define function that calls general source-fp function? but xmls? ----------------------------------------------------
def fokker_plank_nbi(bundle, parameters):
    if parameters['nbi_fp']  == 1: 
        print('--- RISK ---')
        print(bundle['distribution_sources'].time)
        distributions_fp_s = risk(bundle['equilibrium'], bundle['core_profiles'], bundle['nbi'], bundle['distribution_sources'], bundle['distributions'], parameters['dt_required'], (parameters['input_path'] + '/input_risk.xml'), 'mpi_local')
        
    elif parameters['nbi_fp'] == 2:
        print('--- SPOT ---')
        distributions_fp_s = spot(bundle['equilibrium'], bundle['core_profiles'], bundle['wall'], bundle['nbi'], bundle['distribution_sources'], bundle['distributions'], parameters['dt_required'] , (parameters['input_path'] + '/input_spot.xml'), parameters['mpi_local']) 

    elif parameters['nbi_fp'] == 3:
        print('--- ASCOT 4 SERIAL ---')
        distributions_fp_s = ascot4serial(bundle['core_profiles'], bundle['equilibrium'], bundle['wall'], bundle['distribution_sources'] , bundle['distributions'], (parameters['input_path'] + '/input_ascot4serial.xml') )
    
    elif parameters['nbi_fp'] == 4:
        print('--- ASCOT 4 PARALLEL ---')
        distributions_fp_s = ascot4parallel(bundle['core_profiles'], bundle['equilibrium'], bundle['wall'], bundle['distribution_sources'], bundle['distributions'], (parameters['input_path'] + '/input_ascot4parallel.xml'))

    else:
        distributions_fp_s = empty_distributions(bundle['core_profiles'])
      #  distributions_fp_s = copy.deepcopy(bundle['distributions'])
        
    return(distributions_fp_s)


## SYNERGY
def fokker_plank_nbi_ic_synergy(IDS_BUNDLE_nbi, IDS_BUNDLE_ic, parameters):
    
    distributions = spot( )
