import os, sys
import argparse
parser = argparse.ArgumentParser(description='choose actors in argument with default actor input parameters')
parser.add_argument("-s","--show",help="show actor list",action="store_true")
parser.add_argument("-e","--ec_wave_solver",help="ec_wave_solver=0,1,2...", type=int, default=0)
parser.add_argument("-i","--ic_coup",help="ic_coup=0,1", type=int, default=0)
parser.add_argument("-is","--ic_wave_solver",help="ic_wave_solver=0,1,2,...", type=int, default=0)
parser.add_argument("-if","--ic_wave_fp",help="ic_wave_fp=0,1", type=int, default=0)

parser.add_argument("-n","--nbi_source",help="nbi_source=0,1,2...", type=int, default=0)
parser.add_argument("-nf","--nbi_fp",help="nbi_source=0,1,2,...", type=int, default=0)

parser.add_argument("-nu","--nuclear_source",help="nuclear_source=0,1...", type=int, default=0)
parser.add_argument("-nuf","--nuclear_fp",help="nuclear_fp=0,1,2,...", type=int, default=0)

parser.add_argument("-fs","--fill_core_sources",help="fill_core_sources=0,1", type=int, default=0)
parser.add_argument("-fp","--fill_core_profiles",help="fill_core_profiles=0,1", type=int, default=0)
parser.add_argument("-p","--parallel",help="parallel workflow flag",type=int,default=0)
parser.add_argument("-nproc","--nproc_ion_fp",help="nproc of ion FP ",type=int, default=16)

args = vars(parser.parse_args())
ec_wave_solver = args["ec_wave_solver"]
ic_coup = args["ic_coup"]
ic_wave_solver = args["ic_wave_solver"]
ic_wave_fp = args["ic_wave_fp"]

nbi_source = args["nbi_source"]
nbi_fp = args["nbi_fp"]

nuclear_source = args["nuclear_source"]
nuclear_fp = args["nuclear_fp"]

fill_core_sources = args["fill_core_sources"]
fill_core_profiles = args["fill_core_profiles"]
parallel_f = args["parallel"]
show_f = args["show"]
nproc = args["nproc_ion_fp"]
if(nproc<1):
  nproc=1

print('parallel flag:',parallel_f)

try:
    from lxml import etree
except:
    print('ERROR: lxml module not found', file=sys.stderr)
    print('---> TIP: load the HCD module or source the configuration file', file=sys.stderr)
    sys.exit()

try:
    import colour_definitions as col
    from hcd_tools import import_actor, create_maindict, loadlist, \
        create_workflow_param_from_file, dict_merge
    from codeparam_edit import edit_codeparam
    from utility_functions import save, run, destr_and_make, \
        update_workflow_param,load
except:
    raise
    print('ERROR while loading internal HCD modules', file=sys.stderr)
    print('---> TIP: load the HCD module or source the configuration file', file=sys.stderr)
    sys.exit()

#---------------------------------------------------------------------------------------------
# Folder from which to find the compiled HCD actors

if os.getenv('ACTOR_FOLDER') is None:
    print('ERROR: the environment variable ACTOR_FOLDER has not been set up', file=sys.stderr)
    sys.exit()
else:
    ACTOR_FOLDER = os.getenv('ACTOR_FOLDER')

# --------------------------------------------------------------------------------------------
# Path to the default parameter file

hcd_path = '/'.join(os.path.realpath(__file__).split('/')[:-1])
default_wf_param_file = hcd_path+'/global_configuration/input_workflow_default.xml'

# --------------------------------------------------------------------------------------------
def open_gui(wf_param_file):

    # CHECK THAT MANDATORY ACTORS ARE THERE
    merge_actor_list = loadlist('merge_actor_list')
    err_global = 0
    for actor in merge_actor_list:
        err = import_actor(actor,1)
        err_global = err_global + err
    if err_global!=0:
        print('---------------------------------------------', file=sys.stderr)
        print('One or more mandatory actor(s) not accessible', file=sys.stderr)
        print('--> Program stopped.'                         , file=sys.stderr)
        print('---------------------------------------------', file=sys.stderr)
        return


    # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
    # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
    (maindict, compiled_actors, uncompiled_actors, code_selection, catlist) = \
        create_maindict(wf_param_file,1,1)
    workflow_param = create_workflow_param_from_file(wf_param_file,1)


    ## abbreviations for the keys - makes it easier to change them in the xml file
    wfp_ref = list(workflow_param.keys())[0]
    cod_ref = list(workflow_param.keys())[1]

    hcd_actors_ref = list(maindict.keys())[1]
    make_core_ref  = list(maindict.keys())[2]
    all_actors_ref = [hcd_actors_ref,make_core_ref]

    global_dict = dict_merge(maindict[hcd_actors_ref],maindict[make_core_ref])

    cats_actors = {}
    for icat in global_dict.keys():
      for icat_sub in global_dict[icat].items():
         cats_actors[icat_sub[0]] = list(icat_sub[1].keys())

    ## LEFT - CONFIGURING THE WORKFLOW PARAMETERS
    irow = 0

    # Class to not re-generate a new folder name between two 'save' statements
    class saved_folder_name(object):
        def __init__(self):
            self.value = None
        def NoAction(self):
            self.value = self.value
        def Save(self,chosen_folder,init_folder):
            previous_folder = init_folder
            if chosen_folder == init_folder: # Very first SAVE, or SAVE after a SAVE_AS
                self.value=save(self.value,default_wf_param_file,previous_folder,\
                    global_dict,uncompiled_actors,workflow_param,wfp_ref,cod_ref)
            else:
                if chosen_folder is None:
                    if self.value is None: # 1st SAVE after a LOAD
                        self.value=save(init_folder,default_wf_param_file,previous_folder,\
                            global_dict,uncompiled_actors,workflow_param, \
                            wfp_ref,cod_ref)
                    else: # Next SAVEs after a LOAD; SAVE after a SAVE AS which is after a LOAD; 
                        self.value=save(self.value,default_wf_param_file,previous_folder, \
                            global_dict,uncompiled_actors,workflow_param, \
                            wfp_ref,cod_ref)
                else: # SAVE AS
                    if_cancelled = self.value
                    self.value=save(chosen_folder,default_wf_param_file,previous_folder,\
                        global_dict,uncompiled_actors,workflow_param,\
                        wfp_ref,cod_ref)
                    if self.value is None:
                        self.value = if_cancelled
            return self.value

    saved_folder = saved_folder_name()

    # -------------------------------------------------------------------------------------

    # To use the folder loaded through the 'load' function for the next 'save' statements
    if wf_param_file == default_wf_param_file:
        init_folder = None
    else:
        init_folder = ('/').join(wf_param_file.split('/')[:-1])

    # -------------------------------------------------------------------------------------
    workflow_param['ACTOR SELECTION']['ec_wave_solver'] = str(ec_wave_solver)
    workflow_param['ACTOR SELECTION']['ic_coup'] = str(ic_coup)
    workflow_param['ACTOR SELECTION']['ic_wave_solver'] = str(ic_wave_solver)
    workflow_param['ACTOR SELECTION']['ic_wave_fp'] = str(ic_wave_fp)
    workflow_param['ACTOR SELECTION']['nbi_source'] = str(nbi_source)
    workflow_param['ACTOR SELECTION']['nbi_fp'] = str(nbi_fp)
    workflow_param['ACTOR SELECTION']['nuclear_source'] = str(nuclear_source)
    workflow_param['ACTOR SELECTION']['nuclear_fp'] = str(nuclear_fp)
    workflow_param['ACTOR SELECTION']['fill_core_sources'] = str(fill_core_sources)
    workflow_param['ACTOR SELECTION']['fill_core_profiles'] = str(fill_core_profiles)
    #workflow_param['FURTHER SETTINGS']['nproc_ion_fp'] = str(nproc)
    workflow_param['WORKFLOW PARAMETERS (STANDALONE)']['parallel_workflow'] = str(parallel_f)
    if(show_f==1):   
      for icat in cats_actors.keys():
        print('cat ',icat, cats_actors[icat])
    
    test_folder = 'data/test_actors'+str(ec_wave_solver)+str(ic_coup)+str(ic_wave_solver)+str(ic_wave_fp)+str(nbi_source)+str(nbi_fp)+str(nuclear_source)+str(nuclear_fp)+str(fill_core_sources)+str(fill_core_profiles) \
+'_nproc'+str(nproc)
#    if(os.path.isdir(test_folder)):
#      os.removedirs(test_folder)    
    saved_folder.Save(test_folder, init_folder)
    run(test_folder)

#---------------------------------------------------------------------------------------------
if __name__ == "__main__":

    open_gui(default_wf_param_file)

