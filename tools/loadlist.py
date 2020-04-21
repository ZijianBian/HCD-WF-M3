# -----------------------------------------------------
# Function to read the yaml file containing the global
# lists used in many places of the H&CD workflow
# -----------------------------------------------------

# Load necessary modules
import yaml, inspect, os

# Private function to inspect the full path of the function
def __foo():
  pass

# Create lists from the global configuration yaml file
def loadlist(listname):

    path_file = os.path.abspath(inspect.getfile(__foo))
    path = '/'.join(path_file.split('/')[:-1])

    file = open(path+'/../global_configuration/'+'global_lists.yaml', 'r')
    data = yaml.load(file, Loader=yaml.CLoader)

    if listname=='ids_list':
        output_list = data['ids_list'].split(' ')
    elif listname=='actor_list':
        output_list = data['actor_list'].split(' ')
    elif listname=='merge_actor_list':
        output_list = data['merge_actor_list'].split(' ')
    elif listname=='empty_actor_list':
        output_list = data['empty_actor_list'].split(' ')
    else:
        print('Error: bad listname in loadlist()')
        output_list=[]

    return output_list
