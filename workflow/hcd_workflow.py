import os, imas, sys, copy
from set_md_from_pulse_schedule import set_md_from_pulse_schedule
import generate_actors
import auto_hcd_actors as act

actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')
list_of_actors = ['merge_waves', 'merge_distributions', 'merge_distribution_sources', 'hcd2core_sources', 'empty_core_sources']

for name in list_of_actors:
    try:
        sys.path[:0] = [os.path.join(actor_path,name)]
        globals()[name] = getattr(__import__(name), name)
    except:
        pass
        print(name, 'not found')
#--------------------------------------------------------------------------------------------------------------------

def hcd_workflow(IDS_BUNDLE_in, parameters):

    ## STEP 0: preparation - modified IDSs will be stored in their respective bundles, IDS_BUNDLE_out will hold the final information:
    print('-- step 0')
    IDS_BUNDLE_nbi   = copy.deepcopy(IDS_BUNDLE_in)
    IDS_BUNDLE_nuclear = copy.deepcopy(IDS_BUNDLE_in)
    IDS_BUNDLE_ic    = copy.deepcopy(IDS_BUNDLE_in)
    IDS_BUNDLE_ec    = copy.deepcopy(IDS_BUNDLE_in)
    IDS_BUNDLE_out   = copy.deepcopy(IDS_BUNDLE_in)
  

    ## STEP 1:  SOURCE CODES and WAVE SOLVER (and ICCOUP) :
    print('-- step 1: source codes and wave solvers')
    IDS_BUNDLE_nbi['distribution_sources']      = copy.deepcopy(act.nbi_source(IDS_BUNDLE_nbi, parameters))
    IDS_BUNDLE_nuclear['distribution_sources']  = copy.deepcopy(act.nuclear_source(IDS_BUNDLE_nuclear, parameters))
    IDS_BUNDLE_ic['waves']                      = copy.deepcopy(act.ic_coup(IDS_BUNDLE_ic, parameters))
    IDS_BUNDLE_ic['waves']                      = copy.deepcopy(act.ic_wave_solver(IDS_BUNDLE_ic, parameters))
    IDS_BUNDLE_ec['waves']                      = copy.deepcopy(act.ec_wave_solver(IDS_BUNDLE_ec, parameters))
  

    ## STEP 2: FOKKER PLANK SOLVERS and creating a common nbi_ic distributions IDS
    print('-- step 2: fokker plank solvers')
    IDS_BUNDLE_nuclear['distributions']        = copy.deepcopy(act.nuclear_fp(IDS_BUNDLE_nuclear, parameters))

    if(parameters['nbi_fp'] == 9 and parameters['ic_fp'] == 9):
        distributions_nbi_ic    =   copy.deepcopy(act.synergy_fp(IDS_BUNDLE_nbi, IDS_BUNDLE_ic, parameters))
    else:
        IDS_BUNDLE_nbi['distributions']    =   copy.deepcopy(act.nbi_fp(IDS_BUNDLE_nbi, parameters))
        IDS_BUNDLE_ic['distributions']     =   copy.deepcopy(act.ic_wave_fp(IDS_BUNDLE_ic, parameters))

        distributions_nbi_ic =   merge_distributions(IDS_BUNDLE_nbi['distributions'], IDS_BUNDLE_ic['distributions'])


    ## STEP 4: MERGING INTO FINAL DISTRIBUTIONS, DISTRIBUTION SOURCES and WAVES
    print('-- step 3: mergers')
    distributions_final        = merge_distributions(IDS_BUNDLE_nuclear['distributions'], distributions_nbi_ic)
    waves_final                = merge_waves(IDS_BUNDLE_ec['waves'], IDS_BUNDLE_ic['waves'])
    distribution_sources_final = merge_distribution_sources(IDS_BUNDLE_nbi['distribution_sources'], IDS_BUNDLE_nuclear['distribution_sources'])
   

    ## STEP 5: MAKE CORE IDS:
    print('-- step 4: make core ids')
    if parameters['hcd2core_sources'] == 1:
        core_sources_final  = hcd2core_sources(distributions_final, distribution_sources_final, waves_final, IDS_BUNDLE_in['core_profiles'])
    else:
        pass
        core_sources_final = empty_core_sources(IDS_BUNDLE_in['core_profiles'])

    if parameters['hcd2core_profiles'] == 1:
        core_profiles_final = hcd2core_profiles(distributions_final, distribution_sources_final, waves_final, IDS_BUNDLE_in['core_profiles'])
    else:
        pass
        core_profiles_final = copy.deepcopy(IDS_BUNDLE_in['core_profiles'])
   



    IDS_BUNDLE_out['distributions']        = distributions_final
    IDS_BUNDLE_out['waves']                = waves_final
    IDS_BUNDLE_out['distribution_sources'] = distribution_sources_final 
    IDS_BUNDLE_out['core_sources']         = core_sources_final

    print('end of timeloop')

    return IDS_BUNDLE_out

    
