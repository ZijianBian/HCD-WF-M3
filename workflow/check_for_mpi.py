from subprocess import Popen, PIPE

def get_result(p):
    stdout = p.communicate()
    for s in stdout:
        if len(s) is not 0:
            res = True
        elif len(s) is 0:
            res = False
        break
    return(res)
        
def run_cmd(cmd):
    p = Popen(cmd, shell = True, stdout = PIPE)
    p.wait()
    return get_result(p)

def is_compiled_for_mpi(file_path, grep_str):
    cmd = 'ldd '+file_path + '| grep '+grep_str
    return(run_cmd(cmd))

