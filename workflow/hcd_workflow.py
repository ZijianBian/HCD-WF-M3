=import os, imas, sys
import generate_actors
import auto_hcd_actors as actors
from bundle_copy import bundle_copy
from import_actor import import_actor

# MERGERS EXECUTED LOCALLY IN HCD_WORKFLOW (ALL OTHER ACTORS ARE DEFINED IN AUTO_HCD_ACTORS)
list_of_actors = ['merge_waves','merge_distributions','merge_distribution_sources','merge_core_sources']

# IMPORT ALL ACTORS FROM THE MINIMUM LIST
for name in list_of_actors:

    err = import_actor(name)

# --------------------------------------------------------------------------------------------------------------------

def hcd_workflow(IDS_BUNDLE_in, parameters):

    # STEP 0: PREPARATION OF SUB-BUNDLES FOR EACH TYPE OF H&CD CALCULATION - IDS_BUNDLE_OUT WILL HOLD THE FINAL RESULT
    IDS_BUNDLE_nbi     = bundle_copy(IDS_BUNDLE_in)
    IDS_BUNDLE_nuclear = bundle_copy(IDS_BUNDLE_in)
    IDS_BUNDLE_ic      = bundle_copy(IDS_BUNDLE_in)
    IDS_BUNDLE_ec      = bundle_copy(IDS_BUNDLE_in)
    IDS_BUNDLE_core    = bundle_copy(IDS_BUNDLE_in)
    IDS_BUNDLE_out     = bundle_copy(IDS_BUNDLE_in)

    # STEP 1: SOURCE CODES, ICCOUP (FOR IC COUPLING) AND WAVE SOLVERS
    print('-- Step 1: Source codes and Wave solvers')
    IDS_BUNDLE_nbi     ['distribution_sources'] = actors.nbi_source     ( IDS_BUNDLE_nbi,     parameters )
    IDS_BUNDLE_nuclear ['distribution_sources'] = actors.nuclear_source ( IDS_BUNDLE_nuclear, parameters )
    IDS_BUNDLE_ic      ['waves']                = actors.ic_coup        ( IDS_BUNDLE_ic,      parameters )
    IDS_BUNDLE_ic      ['waves']                = actors.ic_wave_solver ( IDS_BUNDLE_ic,      parameters )
    IDS_BUNDLE_ec      ['waves']                = actors.ec_wave_solver ( IDS_BUNDLE_ec,      parameters )

    # INTERMEDIATE STEP: SYSTEMATICALLY COPY THE NBI DISTRIBUTION_SOURCES TO THE IC BUNDLE IN CASE SYNERGY IS MODELLED
    IDS_BUNDLE_ic ['distribution_sources'] = IDS_BUNDLE_nbi['distribution_sources']

    # STEP 2: FOKKER PLANK SOLVERS
    print('-- Step 2: Fokker Planck solvers')
    IDS_BUNDLE_ic      ['distributions'] = actors.ic_wave_fp ( IDS_BUNDLE_ic,      parameters)
    IDS_BUNDLE_nuclear ['distributions'] = actors.nuclear_fp ( IDS_BUNDLE_nuclear, parameters)
    IDS_BUNDLE_nbi     ['distributions'] = actors.nbi_fp     ( IDS_BUNDLE_nbi,     parameters)

    # STEP 3: MERGING INTO FINAL DISTRIBUTIONS, DISTRIBUTION_SOURCES and WAVES
    print('-- Step 3: Mergers')
    distributions_nbi_ic         = merge_distributions        ( IDS_BUNDLE_nbi['distributions'],            IDS_BUNDLE_ic['distributions'])
    distributions_fus_nbi_ic     = merge_distributions        ( IDS_BUNDLE_nuclear['distributions'],        distributions_nbi_ic)
    waves_ec_ic                  = merge_waves                ( IDS_BUNDLE_ec['waves'],                     IDS_BUNDLE_ic['waves'])
    distribution_sources_fus_nbi = merge_distribution_sources ( IDS_BUNDLE_nuclear['distribution_sources'], IDS_BUNDLE_nbi['distribution_sources'])

    # INTERMEDIATE STEP: COPY H&CD RESULTS INTO THE BUNDLES FOR CORE_SOURCES AND CORE_PROFILES
    IDS_BUNDLE_core ['distribution_sources'] = distribution_sources_fus_nbi
    IDS_BUNDLE_core ['distributions']        = distributions_fus_nbi_ic
    IDS_BUNDLE_core ['waves']                = waves_ec_ic 

    # STEP 4: MAKE CORE_SOURCES AND CORE_PROFILES IDS:
    print('-- Step 4: Make core_sources and/or core_profiles')
    IDS_BUNDLE_core ['core_sources']  = actors.fill_core_sources  ( IDS_BUNDLE_core, parameters )
    IDS_BUNDLE_core ['core_profiles'] = actors.fill_core_profiles ( IDS_BUNDLE_core, parameters )

    # FILL THE OUTPUT BUNDLE WITH THE RESULTS OF H&CD CALCUATIONS
    IDS_BUNDLE_out['distribution_sources'] = IDS_BUNDLE_core ['distribution_sources']
    IDS_BUNDLE_out['distributions']        = IDS_BUNDLE_core ['distributions']
    IDS_BUNDLE_out['waves']                = IDS_BUNDLE_core ['waves']
    IDS_BUNDLE_out['core_sources']         = IDS_BUNDLE_core ['core_sources']
    IDS_BUNDLE_out['core_profiles']        = IDS_BUNDLE_core ['core_profiles']

    print('End of time slice')

    return IDS_BUNDLE_out
