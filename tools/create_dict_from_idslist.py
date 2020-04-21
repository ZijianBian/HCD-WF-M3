# ------------------------------------------------
# Create dictionary from IDS list and IMAS object
# ------------------------------------------------

def create_dict_from_idslist(idslist,imas_object):

    imas_dict = {}
    for ids in idslist:
        imas_dict[ids] = eval('imas_object.'+ids)

    return imas_dict

