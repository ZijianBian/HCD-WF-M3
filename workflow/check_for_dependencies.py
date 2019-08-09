def check_for_dependencies(root, dependencies):
    from lxml import etree
    
    
    codedict_names = {}

    for elem in root.iter():
        if elem is not etree.Comment and 'list' in elem.attrib:
            if elem.text is not '0':

                codename = elem.attrib['list'].split(' ')[int(elem.text)-1]
                codedict_names[elem.tag] = codename
            else:
                codedict_names[elem.tag] = None

         



    def check_if_code_fulfills_configuration(cat, code):
            if dependencies[cat] is not None and code in dependencies[cat]: 
                
                    fulfills_all_dependencies = [1] * (len(dependencies[cat][code]))
                    j = 0

                    for dep in dependencies[cat][code]:

                        
                        for i in dep.keys():


                            if 'any'in str(dep[i]) and codedict_names[i] is not None:
                                pass
                            elif str(dep[i]).find(str(codedict_names[i]))is not -1:
                                pass
                            else:
                                print('this is not a valid configuration for '+ code.upper() + ' please change the selection of your actors and try again')
                                sys.exit()
                                

    for entry in codedict_names:
        if codedict_names is not None:
            check_if_code_fulfills_configuration(entry, codedict_names[entry])


    print('selection fulfills all actor selection rules')
