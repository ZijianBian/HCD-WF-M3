# ------------------------------------------------------------
# PURPOSE: COPY A BUNDLE OF IDSS
# NOTE: A BUNDLE IS HERE DEFINED AS A SET OF IDSS ASSEMBLED 
#       INTO A DICTIONARY
# ------------------------------------------------------------
# INPUT ARGUMENTS:
# - INPUT_BUNDLE: INITIAL BUNDLE TO COPY
# - IDSLIST (OPTIONAL): RESTRICTED LIST OF IDSS TO COPY FROM
#   THE INITIAL BUNDLE
# ------------------------------------------------------------
# OUTPUT ARGUMENT:
# - OUTPUT_BUNDLE: OUTPUT COPIED BUNDLE
# ------------------------------------------------------------
import imas,sys

def bundle_copy(input_bundle,idslist=None):

    # OPTIONALLY RESTRICT THE LIST OF IDSS TO BE COPIED
    # IF NO LIST IS SPECIFIED: USE THE FULL LIST OF THE INITIAL BUNDLE
    if idslist == None:
        idslist = input_bundle.keys()

    # EMPTY IMAS STRUCTURE
    output_imas = imas.ids(0,0)
    
    # EMPTY OUTPUT BUNDLE (DICTIONARY)
    output_bundle = dict()

    # LOOP OVER IDSS OF THE BUNDLE TO COPY
    for key in input_bundle.keys():

        # ONLY COPY THE IDSS WE ARE INTERESTED IN
        if key in idslist:

            # IDS TO COPY
            ids = input_bundle[key]

            # COPY THE IDS INTO THE EMPTY IMAS STRUCTURE
            eval('output_imas.'+key+'.copyValues(ids)')

            # USE THIS STRUCTURE TO FILL THE DICTIONARY OF THE OUTPUT BUNDLE
            output_bundle[key] = eval('output_imas.'+key)

    return output_bundle


