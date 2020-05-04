# -------------------------------------------------------
# PURPOSE: GENERATE THE AUTO_HCD_ACTORS PYTHON FILE
#          ACCORDING TO THE ACTOR SELECTION FROM THE GUI
# -------------------------------------------------------
from developer_file import load_add_arg
from hcd_tools import import_actor, loadlist, read_actor_ids, create_maindict, is_compiled_for_mpi

# CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
# (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
(maindict, compiled_actors, uncompiled_actors) = create_maindict('input_workflow_default.xml',2,0)

# GENERATE THE WORKFLOW/AUTO_HCD_ACTORS.PY FILE 
empty_actor_list = loadlist('empty_actor_list')
add_arg          = load_add_arg()
with open('workflow/auto_hcd_actors.py', 'w') as file:

    file.write('from hcd_tools import import_actor\n\n')
    file.write('list_of_actors = ["'+'","'.join(compiled_actors+empty_actor_list)+'"]\n\n')
    file.write('for name in list_of_actors:\n')
    file.write('   err = import_actor(name,0)\n\n')
        
    for proc in maindict:
        for sys in maindict[proc]:
            for cat in maindict[proc][sys]:

                file.write('def '+ cat + '(bundle, parameters): \n')
                i = 0
                
                for code in maindict[proc][sys][cat]:
                    err = import_actor(code,0)
                    add_arg_nr = 0
                    i +=1 
                    if i == 1:
                        file.write('   if parameters["'+cat +'"] == '+str(i)+':\n')
                    else: 
                        file.write('   elif parameters["'+cat +'"] == '+str(i)+':\n')
                    file.write('       print("-- '+code.upper()+' --")\n')
                    if len(maindict[proc][sys][cat][code][1]) > 0:
                        output_ids_list = maindict[proc][sys][cat][code][1]
                        file.write('       '+",".join(str(x)+'_temp' \
                                   for x in output_ids_list)+' = '+code+'(')
                        first_in = True
                        for ids_in in maindict[proc][sys][cat][code][0]:
                            if first_in == False:
                                file.write(', ')
                            
                            if ids_in.find('add_arg') is not -1\
                               and add_arg.get(code) is not None:
                                file.write('parameters["'+add_arg[code][add_arg_nr]+'"]')
                                add_arg_nr += 1
                            elif ids_in.find('codeparam') is not -1:
                                file.write('(parameters["input_path"]+"/'\
                                           +sys+'/input_'+code+'.xml")')
                            else:
                                file.write('bundle["'+ids_in+'"]')
                            first_in = False

                        libmpi_path = eval(code+'.location')+'/native_wrapper/lib/lib'+code+'.so'
                        if is_compiled_for_mpi(libmpi_path, 'libmpi'):
                            if cat == 'nbi_fp':
                                file.write(',"mpi_local",mpi_processes=parameters["nproc_ion_fp"]')
                            else:
                                file.write(',"mpi_local"') # FOR NON-FP CODES, DEFAULT IS NPROC=4

                        file.write(')\n')
                    else:
                        file.write('       print("code not installed")\n\n')
                        output_ids_list = ['core_profiles'] # DEFAULT WHEN NO CODE AVAILABLE FOR THIS SOURCE/PROCESS (TO REFINE LATER)
                
                file.write('   else: \n')
                file.write('       '+output_ids_list[0]+'_temp = empty_'\
                           +output_ids_list[0]+ '(bundle["core_profiles"])')
                file.write('\n')

                file.write('   return('+ output_ids_list[0]+'_temp)')
                file.write('\n\n')    
