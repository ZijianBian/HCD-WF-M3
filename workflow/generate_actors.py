# -------------------------------------------------------
# PURPOSE: GENERATE THE AUTO_HCD_ACTORS PYTHON FILE
#          ACCORDING TO THE ACTOR SELECTION FROM THE GUI
# -------------------------------------------------------
import os,imas,sys,copy
import lxml
from lxml import etree
import check_for_mpi
from developer_file import load_add_arg
from hcd_tools import import_actor, loadlist

tree                      = etree.parse('input_workflow_default.xml')
root                      = tree.getroot()
maindict                  = {}
ids_list                  = loadlist('ids_list')
merge_actor_list          = loadlist('merge_actor_list')
empty_actor_list          = loadlist('empty_actor_list')
add_arg                   = load_add_arg()
list_of_actors            = []
list_of_uncompiled_actors = []

# ----------------------------------------------------------------------
def read_inputoutput(name):
    in_l  = []
    out_l = []

    err = import_actor(name)

    if err==0:
        parstr = globals()[name].__doc__
        
        for elem in parstr.split('\n'):
            
            for iids in ids_list:
                if elem.find(':param '+iids) is not -1:
                    in_l.append(iids)
                    break
                elif elem.find('integ') is not -1:
                    in_l.append('add_arg')
                    break
                elif elem.find('doub') is not -1:
                    in_l.append('add_arg')
                    break
                elif elem.find('codeparam') is not -1:
                    in_l.append('codeparam')
                    break
                elif elem.find(':param result: ') is not -1 \
                and elem.find(iids) is not -1:
                    out_l.append(iids)

        list_of_actors.append(name)
        
    else:
        list_of_uncompiled_actors.append(name)

    return(in_l, out_l)
# ----------------------------------------------------------------------

for step in root[2]:
    dict3 = {}
    for isys in step:
        dict2 = {}
        for icat in isys:
            dict1 = {}
            if icat.tag is not etree.Comment:
                for icode in icat.attrib['list'].split():
                    (in_l, out_l) = read_inputoutput(icode)
                    dict1[icode] = [in_l, out_l]
                dict2[icat.tag] = dict1
        dict3[isys.tag] = dict2
    maindict[step.tag] = dict3

# GENERATE THE WORKFLOW/AUTO_HCD_ACTORS.PY FILE 
with open('workflow/auto_hcd_actors.py', 'w') as file:

    file.write('import os, imas, sys, copy\n')
    file.write('from hcd_tools import import_actor\n\n')
    file.write('list_of_actors = ["'+'","'.join(list_of_actors+empty_actor_list)+'"]\n\n\n')
    file.write('for name in list_of_actors:\n')
    file.write('   err = import_actor(name)\n')
        
    for proc in maindict:
        for sys in maindict[proc]:
            for cat in maindict[proc][sys]:

                file.write('def '+ cat + '(bundle, parameters): \n')
                i = 0
                
                for code in maindict[proc][sys][cat]:
                    add_arg_nr = 0
                    i +=1 
                    if i == 1:
                        file.write('   if parameters["'+cat +'"] == '+str(i)+':\n')
                    else: 
                        file.write('   elif parameters["'+cat +'"] == '+str(i)+':\n')
                    file.write('       print("--'+code.upper()+'--")\n')
                    if len(maindict[proc][sys][cat][code][1]) > 0:
                        output_ids_list = maindict[proc][sys][cat][code][1]
                        file.write('       '+",".join(str(x)+'_temp' for x in output_ids_list)+' = '+code+'(')
                        
                        first_in = True
                        for ids_in in maindict[proc][sys][cat][code][0]:
                            if first_in == False:
                                file.write(', ')
                            
                            if ids_in.find('add_arg') is not -1:
                                file.write('parameters["'+add_arg[code][add_arg_nr]+'"]')
                                add_arg_nr += 1
                            elif ids_in.find('codeparam') is not -1:
                                file.write('(parameters["input_path"]+"/'+sys+'/input_'+code+'.xml")')
                            else:
                                file.write('bundle["'+ids_in+'"]')
                            first_in = False

                        libmpi_path = eval(code+'.location')+'/native_wrapper/lib/lib'+code+'.so'
                        if check_for_mpi.is_compiled_for_mpi(libmpi_path, 'libmpi'):
                            if cat == 'nbi_fp':
                                file.write(',  "mpi_local", mpi_processes=parameters["nproc_ion_fp"]')
                            else:
                                file.write(',  "mpi_local"') # FOR OTHER MPI CODES, KEEP THE DEFAULT FOR NOW (NPROC=4)

                        file.write(')\n\n')
                    else:
                        file.write('       print("code not installed")\n\n')
                
                file.write('\n')
                file.write('   else: \n')
                file.write('       '+output_ids_list[0]+'_temp = empty_'+output_ids_list[0]+ '(bundle["core_profiles"])')
                file.write('\n\n')

                file.write('   return('+ output_ids_list[0]+'_temp)')
                file.write('\n\n')    
