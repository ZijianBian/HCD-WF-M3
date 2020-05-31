# ----------------------------------------------------------------------
# CHECK RULES DEFINED IN THE CODEPARAM XSD FILE, AND TURN THE FIELD RED 
# IN CASE RULES ARE NOT FULFILLED
# ----------------------------------------------------------------------
import colour_definitions as col

def check_xsd_rule(codeparam_dict,elem,root,xmlschema,entry1):
    elem.text = codeparam_dict[elem.tag]
    if xmlschema.validate(root):
        entry1.config(bg=col.c1)
    else:
        entry1.config(bg='salmon1')


