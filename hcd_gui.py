import sys, os
sys.path.append('interface')
sys.path.append('workflow')
sys.path.append(os.getcwd())
from tkinter import *
from tkinter import filedialog, messagebox, ttk
from shutil import copy2, rmtree
from lxml import *
from lxml import etree
from hcd_wrapper import hcd_wrapper 
from hover_class import *
from datetime import datetime
from make_flowchart import make_flowchart




run_config_folder = os.path.join(os.getcwd(), 'run_configurations/run_'+datetime.now().strftime('%m%d_%H%M%S'))
workflow_param = run_config_folder+ '/input_workflow.xml'

os.makedirs(run_config_folder)
copy2('input_workflow_default.xml', run_config_folder+'/input_workflow.xml', follow_symlinks=True)
        


#---------------------------------------------------------------------------------------------
##  create a python directory (maindict) that contains the name of all codes (nemo, bbnbi, ...) , their in & output IDSs, their category (ec_wavesolver, nbi_source, ..) the heating system they belong to (EC, IC, NBI, alpha)

actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')

ids_list = ['core_profiles','core_sourcres','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_antennas','wall', 'distribution_sources', 'distributions', 'waves']

def read_inputoutput(name):

    in_l = []
    out_l = []
    try:
        sys.path[:0] = [os.path.join(actor_path,name)]
        globals()[name] = getattr(__import__(name), name)
        
        parstr = globals()[name].__doc__
        
        for iids in ids_list:
            if parstr.find(':param '+iids) is not -1:
                in_l.append(iids)
            if parstr.find(':param result: '+iids) is not -1:
                out_l.append(iids)
    except:
        print(name, 'not compiled')


    return(in_l, out_l)

tree = etree.parse('input_workflow_default.xml')
root = tree.getroot()

maindict = {}

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
                dict2[icat.tag] = [dict1, icat.text]
        dict3[isys.tag] = dict2
    maindict[step.tag] = dict3

## ------------------------------------------------------------------------------------------
## set a few standard colors to call later
c1 = 'white'
c2 = 'white smoke'
c3 = 'navajo white'
c4 = 'ghost white'
c5 = 'azure4'

cb = 'LavenderBlush3'
c_arr=['red', 'blue','yellow','green']

##---------------------------------------------------------------------------------------------
## CREATE BASIC GUI to be filled later: 

window = Tk()
window.title('HCD WORKFLOW')
window.configure(bg = c1)
#window.geometry("1300x800")
#window.resizable(0,1)

fr_wfp = Frame(window, width = 300, height = 10000, background = c3)
fr_wfp.grid(row = 0, column = 0, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

fr_as = Frame(window, width = 10000, height = 10000, background = c1)
fr_as.grid(row = 0, column = 1, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

fr_fc = Frame(window, width = 100, height = 100, background = c1)
fr_fc.grid(row = 0, column = 2, sticky = 'news', padx = 3, pady = 3)
fr_fc.grid_remove()

old_fr = fr_fc

wfpdict = {}
codedict = {}

## putting this in a function makes sense, because this way the other functions can be defined after wards. the load_parameters() function is called at the very end of the script. 
def load_parameters(workflow_param):
    load_wf_param(workflow_param)      
    load_actor_select(workflow_param)


#_________________________________________________________________________________________________________________________________________


def load_wf_param(workflow_param):

    # DEFINE THE FUNCTIONS WHICH WILL BE USED IN THE REST OF LOAD_WF_PARAM:
    def savechanges(pval, ptag):   #saves a new value of one of the workflow parameters to the workflow-parameter dictionary
        wfpdict[ptag] = pval.get()



    def save_wfp_to_file(tree, root, workflow_param):
 
        i = 0
        for iroot in range(2):
            for elem in root[iroot].iter():
                if((elem.tag is not etree.Comment) and (len(elem) == 0)):
                    elem.text = wfpdict[elem.tag]
                    i = i+1  

        for elem in root[2][0].iter():
            if((elem.tag is not etree.Comment) and (len(elem) == 0)):
                elem.text = str(codedict[elem.tag])

        tree.write(workflow_param)
 
        
        ## ---------------------- create_directories()



        #COPY ALL XML FILES THAT WILL BE USED TO THE LOCAL FOLDER TO CALL THEM FROM THERE DURING THE RUN
        for sys in maindict['systems']:
            for cat in maindict['systems'][sys]:
                if int(maindict['systems'][sys][cat][1]) is not 0:
                    curval = list(maindict['systems'][sys][cat][0])[int(maindict['systems'][sys][cat][1])-1]

                    for file in os.listdir(actor_path+'/'+curval ):
                        if file.endswith(".xml") and (not 'default' in file):
                            src_file = os.path.join(actor_path+'/'+curval, file)
                            dest_file = os.path.join(run_config_folder+'/input_'+curval+'.xml')
                            if not os.path.exists(dest_file):
                                copy2(src_file, dest_file, follow_symlinks=True)

        copy2(run_config_folder+'/input_workflow.xml','input_workflow_default.xml', follow_symlinks=True)
                            
    def save_wfp_and_run(tree, root, workflow_param, save_yn):
        save_wfp_to_file(tree, root, workflow_param)
        window.destroy()
        hcd_wrapper(run_config_folder)
        if save_yn == 0:
            rmtree(run_config_folder)
        

    # BEGINNING OF THE ACTUAL LOAD_WF_PARAM FUNCTION
    tree = etree.parse(workflow_param)
    root = tree.getroot()
    rrow = 0

    for root_nr in range(2):
        lf = Label(fr_wfp, text = root[root_nr].attrib['display'], bg = c3 , font = '15')
        lf.grid(row = rrow, column = 0, columnspan = 3, pady = 10, padx = 5, sticky = 'we')
        rrow += 1
            
        for param in root[root_nr].iter():
            if param.tag is not etree.Comment and len(param) == 0:

                wfpdict[param.tag.strip()] = param.text.strip()
               
                Label(fr_wfp,text = param.tag.strip(), bg = c3).grid(row = rrow, column = 0, padx = 10, sticky = 'w')
                pval = StringVar()
                pval.set(param.text.strip())

                if param.tag.find('input_path') is not -1:
                    pval.set(run_config_folder)


                e=Entry(fr_wfp,textvariable = pval, bg = c1)
                e.grid(row = rrow, column = 1, padx = 10, sticky = 'e')
                pval.trace('w', lambda name, index, mode, ptag = param.tag.strip(), pval = pval: savechanges(pval, ptag))
                rrow += 1

                
                
    Button(fr_wfp, text = 'Save Changes', bg = c2, command = lambda root = root: save_wfp_to_file(tree, root,workflow_param)).grid(row = rrow+10, column = 0, pady =(20,3), padx = 5, sticky = 'ew')
    Button(fr_wfp, text = 'Load Parameters',bg = c2, command = lambda: load_parameters(filedialog.askdirectory()+'/input_workflow.xml')).grid(row = rrow+10, column = 1, pady = (20,3), padx = 5, sticky = 'ew')
    Button(fr_wfp, text = 'Save and Run',bg = c2, command = lambda root = root, save_yn = 1: save_wfp_and_run(tree, root, workflow_param, save_yn)).grid(row = rrow+ 11, column = 0, pady = (3,10), padx = 5, sticky = 'ew')
    Button(fr_wfp, text = 'Run (without saving configuration)', bg = c2 , command = lambda root = root, save_yn = 0: save_wfp_and_run(tree, root, workflow_param, save_yn)).grid(row = rrow+ 11, column = 1, pady = (3,10), padx = 5, sticky = 'ew')



def updatevalue(choice, sys, cat, cb):  #saves the actor selection in e maindict
    maindict[choice][sys][cat][1] = cb.current()
    codedict[cat] = cb.current()

def load_actor_select(workflow_param): 
    def call_edit_codeparam():
        cp_top = Toplevel()
        cp_top.title('Edit Code Parameters')
        cp_top.geometry('500x700')
    
        fr_ab = Frame(cp_top, width = 200, height = 500, bg = c4)
        fr_ab.grid(row = 0, column = 0, rowspan = 2, sticky = 'ns')
        fr_main = Frame(cp_top, width = 500, height = 1500, bg = c1)
        fr_main.grid(row = 1, column = 1, sticky = 'nwes')
        prev_frame = fr_main
        fr_top = Frame(cp_top, width = 500, height = 50, bg = c2) 
        fr_top.grid(row = 0, column =1, sticky = 'ew')
        cparm_dict = {}



        for sys in maindict['systems']:
            for cat in maindict['systems'][sys]:
                if int(maindict['systems'][sys][cat][1]) is not 0:
                    curval = list(maindict['systems'][sys][cat][0])[int(maindict['systems'][sys][cat][1])-1]
                    Button(fr_ab, text = curval, bg = c2, command = lambda sys = sys, cat = cat: make_frame(sys,cat, prev_frame) ).grid(padx = 5, pady = 5, sticky = 'ew')

        def make_frame(sys,cat, prev_frame):
            prev_frame.grid_remove()
            prev_frame.grid_forget()
            fr = Frame(cp_top, width = 500, height = 1500, bg = c1)
            prev_frame = fr
            fr.grid(row = 1, column =1, sticky = 'nswe')
            fr.grid_propagate(0)

            instr = StringVar()
            curval = list(maindict['systems'][sys][cat][0])[int(maindict['systems'][sys][cat][1])-1]
            instr_xsd = StringVar()


            instr.trace('w', lambda name, index, mode, fr = fr: changed_val(fr, instr.get(), instr_xsd.get(), curval))
        #    instr_xsd.trace('w', lambda name, index, mode, fr=fr: changed_val(fr, instr.get(), instr_xsd.get(), curval))


            for file in os.listdir(actor_path+'/'+curval ):
                if file.endswith(".xml") and (not 'default' in file):
                    instr.set(os.path.join(actor_path+'/'+curval, file))
                if file.endswith('.xsd'):
                    instr_xsd.set(os.path.join(actor_path+'/'+curval, file))


        def changed_val(fra, cpar, xsdpath, curval):
            try:
                xmlschema_doc = etree.parse(xsdpath)
                root_xsd = xmlschema_doc.getroot()
                xmlschema = etree.XMLSchema(xmlschema_doc)
                docum_dict = {}
                for elem in root_xsd.iter():
                    if elem.tag ==  '{http://www.w3.org/2001/XMLSchema}element':
                        for i in elem.iter():
                            if i.tag ==  '{http://www.w3.org/2001/XMLSchema}documentation':
                                docum_dict[elem.attrib.values()[0]] = i.text
            except:
                docum_dict = {}

            fra.grid_remove()
            fra.grid_forget()
            fra = Frame(cp_top, width = 500, height = 1500, bg = c1)
            fra.grid(row = 1, column = 1, sticky = 'nswe')
            fra.grid_propagate(0)

            tree = etree.parse(cpar)        
            root = tree.getroot()
            rrow = 1
            ccolumn = 0

            for elem in root.iter():
                if ((elem.tag is not etree.Comment) and (len(elem) == 0)):
                    l = Label(fra, text = elem.tag.strip(), bg = c1)
                    l.grid(row = rrow, column = ccolumn)
                    evar = StringVar()
                    evar.set(elem.text.strip())
                    e = Entry(fra, textvar = evar, bg = c1)
                    e.grid(row = rrow, column = ccolumn+1, padx = 3, pady = 3)

                    cparm_dict[elem.tag] = evar.get()

                    evar.trace('w', lambda name, index, mode, elem = elem.tag, evar = evar: change_in_par(cparm_dict, elem, evar))

                    try:
                        CreateToolTip(l, docum_dict[l.cget('text')])
                    except:
                        pass 

                    rrow +=1 
                    if rrow > 30:
                        ccolumn += 2
                        rrow = 1
                        fra.grid_propagate(1)

            Button(fr_top, text = 'save', command = lambda: save_codeparam(cparm_dict, tree, root, curval)).grid(row = 1, column = 1, padx = 5, pady = 5, columnspan = 5)


        def change_in_par(cparm_dict, elem, evar):
            cparm_dict[elem] = evar.get()

    def save_codeparam(cparm_dict, tree, root, curval):

        
        for elem in root.iter():
            if((elem.tag is not etree.Comment) and (len(elem) == 0)):
                elem.text = cparm_dict[elem.tag]

        tree.write(run_config_folder+'/input_'+curval+'.xml')


    # BEGINNING OF THE ACTUAL ACTOR SELECT FUNCTION:
    tree = etree.parse(workflow_param)
    root = tree.getroot()
    rrow = 0

    for sys in maindict['systems']:
        Label(fr_as, text = sys, bg = c1, font = '15').grid(row = rrow, column = 0, columnspan =2, sticky = 'ew')
        rrow += 1
        for cat in maindict['systems'][sys]:
            Label(fr_as, text = cat, bg = c1,anchor=W, justify=LEFT).grid(row = rrow, column = 0, sticky = W)
            cb = ttk.Combobox(fr_as, value = ['']+list(maindict['systems'][sys][cat][0]))
            cb.current(int(maindict['systems'][sys][cat][1]))
            codedict[cat] = cb.current()
            cb.grid(row = rrow, column = 1, padx = 20, pady = 5, sticky = 'we')
            cb.bind('<<ComboboxSelected>>', lambda event, sys = sys, cat = cat, cb = cb: updatevalue('systems', sys, cat, cb))
            rrow += 1

    for sys in maindict['post_process']:
        Label(fr_as, text = sys, bg = c1, font = '15').grid(row = rrow, column = 0, columnspan =2, sticky = 'ew')
        rrow += 1
        for cat in maindict['post_process'][sys]:
            Label(fr_as, text = cat, bg = c1,anchor=W, justify=LEFT).grid(row = rrow, column = 0, sticky = W)
            cb = ttk.Combobox(fr_as, value = ['']+list(maindict['post_process'][sys][cat][0]))
            cb.current(int(maindict['post_process'][sys][cat][1]))
            codedict[cat] = cb.current()
            cb.grid(row = rrow, column = 1, padx = 20, pady = 5, sticky = 'we')
            cb.bind('<<ComboboxSelected>>', lambda event, sys = sys, cat = cat, cb = cb: updatevalue('post_process', sys, cat, cb))
            rrow += 1
    

  #  for sys in maindict['make']

    Button(fr_as, text = 'edit codeparameters',bg = c2, command = lambda: call_edit_codeparam()).grid(row = rrow, columnspan = 2, pady = 5) 
  #  Button(fr_as, text = 'create flowchart', bg = c2).grid(row = rrow +1, columnspan = 2, pady = 5)
    Button(fr_as, text = 'create flowchart', bg = c2, command = lambda: make_flowchart(old_fr, window, maindict, c1, c2, c3, c4,c5)).grid(row = rrow +1, columnspan = 2, pady = 5)



#--------------------------------------------------------------------------------------------------------------------------

load_parameters(workflow_param)


window.mainloop()
