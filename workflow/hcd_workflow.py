import generate_actors, sys
import auto_hcd_actors as actors
from hcd_tools import bundle_copy, create_workflow_param_from_file

# -------------------------------------------------------------------------------------------------

def hcd_workflow(BNDL_in,workflow_xml):

    print('Execute H&CD workflow for current time slice', file=sys.stdout)

    # EXTRACT PARAMETERS FROM INPUT XML FILE
    parameters = create_workflow_param_from_file(workflow_xml,2)

    # STEP 0: PREPARATION OF SUB-BUNDLES FOR EACH TYPE OF H&CD CALCULATION
    # BNDL_OUT WILL HOLD THE FINAL RESULT
    BNDL_nbi  = bundle_copy(BNDL_in)
    BNDL_nuc  = bundle_copy(BNDL_in)
    BNDL_ic   = bundle_copy(BNDL_in)
    BNDL_ec   = bundle_copy(BNDL_in)
    BNDL_core = bundle_copy(BNDL_in)
    BNDL_out  = bundle_copy(BNDL_in)

    # STEP 1: SOURCE CODES, ICCOUP (FOR IC COUPLING) AND WAVE SOLVERS
    print('-- Step 1: Source codes and Wave solvers', file=sys.stdout)
    BNDL_nbi ['distribution_sources'] = actors.nbi_source     ( BNDL_nbi, parameters )
    BNDL_nuc ['distribution_sources'] = actors.nuclear_source ( BNDL_nuc, parameters )
    BNDL_ic  ['waves']                = actors.ic_coup        ( BNDL_ic,  parameters )
    BNDL_ic  ['waves']                = actors.ic_wave_solver ( BNDL_ic,  parameters )
    BNDL_ec  ['waves']                = actors.ec_wave_solver ( BNDL_ec,  parameters )

    # INTERMEDIATE STEP: SYSTEMATICALLY COPY THE NBI DISTRIBUTION_SOURCES TO 
    # THE IC BUNDLE IN CASE SYNERGY IS MODELLED
    BNDL_ic ['distribution_sources'] = BNDL_nbi['distribution_sources']

    # STEP 2: FOKKER PLANK SOLVERS
    print('-- Step 2: Fokker Planck solvers', file=sys.stdout)
    BNDL_ic  ['distributions'] = actors.ic_wave_fp ( BNDL_ic,  parameters)
    BNDL_nuc ['distributions'] = actors.nuclear_fp ( BNDL_nuc, parameters)
    BNDL_nbi ['distributions'] = actors.nbi_fp     ( BNDL_nbi, parameters)

    # STEP 3: MERGING INTO FINAL DISTRIBUTIONS, DISTRIBUTION_SOURCES and WAVES
    print('-- Step 3: Mergers', file=sys.stdout)
    distrib_nbi_ic     = actors.merge_distributions(BNDL_nbi['distributions'], \
                                                    BNDL_ic['distributions'])
    distrib_fus_nbi_ic = actors.merge_distributions(BNDL_nuc['distributions'],distrib_nbi_ic)
    waves_ec_ic        = actors.merge_waves(BNDL_ec['waves'],BNDL_ic['waves'])
    dsources_fus_nbi   = actors.merge_distribution_sources(BNDL_nuc['distribution_sources'], \
                                                    BNDL_nbi['distribution_sources'])

    # INTERMEDIATE STEP: COPY H&CD RESULTS INTO THE BUNDLES FOR CORE_SOURCES AND CORE_PROFILES
    BNDL_core ['distribution_sources'] = dsources_fus_nbi
    BNDL_core ['distributions']        = distrib_fus_nbi_ic
    BNDL_core ['waves']                = waves_ec_ic 

    # STEP 4: MAKE CORE_SOURCES AND CORE_PROFILES IDS:
    print('-- Step 4: Make core_sources and/or core_profiles', file=sys.stdout)
    BNDL_core ['core_sources']  = actors.fill_core_sources  ( BNDL_core, parameters )
    BNDL_core ['core_profiles'] = actors.fill_core_profiles ( BNDL_core, parameters )

    # FILL THE OUTPUT BUNDLE WITH THE RESULTS OF H&CD CALCUATIONS
    BNDL_out['distribution_sources'] = BNDL_core ['distribution_sources']
    BNDL_out['distributions']        = BNDL_core ['distributions']
    BNDL_out['waves']                = BNDL_core ['waves']
    BNDL_out['core_sources']         = BNDL_core ['core_sources']
    BNDL_out['core_profiles']        = BNDL_core ['core_profiles']

    print('End of time slice', file=sys.stdout)

    return BNDL_out
