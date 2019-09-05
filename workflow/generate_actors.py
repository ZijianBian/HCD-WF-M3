import os, imas,sys,copy
import lxml
from lxml import etree
import check_for_mpi as cfmpi
import pdb
from developer_file import load_add_arg 

tree = etree.parse('input_workflow_default.xml')
root = tree.getroot()
maindict = {}

actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')

ids_list = ['core_profiles','core_sources','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_antennas','wall', 'distribution_sources', 'distributions', 'waves']

add_arg = load_add_arg()

list_of_actors = []
list_of_uncompiled_actors = []

def read_inputoutput(name):
    in_l = []
    out_l = []
    try:
        sys.path[:0] = [os.path.join(actor_path,name)]
        globals()[name] = getattr(__import__(name), name)
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
                elif elem.find(':param result: '+iids) is not -1:
                    out_l.append(iids)
                    break

        list_of_actors.append(name)

        
    except:
        if name not in list_of_uncompiled_actors:
            print('warning: ', name, ' is not compiled')
        list_of_uncompiled_actors.append(name)

    return(in_l, out_l)


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

#print(maindict)



with open('workflow/auto_hcd_actors.py', 'w') as file:

    file.write('import os, imas, sys, copy\n\n')
    file.write('actor_path = os.path.join(os.getenv("KEPLER"), "imas/src/org/iter/imas/python")\n')
    file.write('list_of_actors = ["'+'","'.join(list_of_actors)+'", "empty_distribution_sources", "empty_waves", "empty_distributions"]\n\n\n')
    file.write('for name in list_of_actors:\n')
    file.write('   sys.path[:0] = [os.path.join(actor_path,name)]\n')
    file.write('   globals()[name] = getattr(__import__(name), name)\n\n\n\n\n')
        


    for proc in maindict:
        for sys in maindict[proc]:
            for cat in maindict[proc][sys]:

                file.write('def '+ cat + '(bundle, parameters): \n')
                i = 0
                
#                    if code not in list_of_uncompiled_actors: 

                for code in maindict[proc][sys][cat]:
                    add_arg_nr = 0
                    i +=1 
                    if i == 1:
                        file.write('   if parameters["'+cat +'"] == '+str(i)+':\n')
                    else: 
                        file.write('   elif parameters["'+cat +'"] == '+str(i)+':\n')
                    file.write('       print("--'+code.upper()+'--")\n')
                    if len(maindict[proc][sys][cat][code][1]) > 0:
                        output_ids_list = maindict[proc][sys][cat][code][1][0]
                        file.write('       '+output_ids_list+'_temp = '+code+'(')
                        
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

                        

                        libmpi_path = os.path.join(os.getenv('KEPLER'), 'imas/lib64/lib'+code+'.so')
                            
                        if cfmpi.is_compiled_for_mpi(libmpi_path, 'libmpi'):
                            file.write(',  "mpi_local"')
                            


                        file.write(')\n\n')
                    else:
                        file.write('       print("code not installed")\n\n')
                
                #pdb.set_trace()
                file.write('\n')
                file.write('   else: \n')
                file.write('       '+output_ids_list+'_temp = empty_'+output_ids_list+ '(bundle["core_profiles"])')
                file.write('\n\n')

                file.write('   return('+ output_ids_list+'_temp)')
                file.write('\n\n')    


#import auto_hcd_actors


