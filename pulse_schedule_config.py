
import os,imas,sys,yaml, copy, numpy as np



# local database environment
user = os.getenv('USER')
tokamakname = 'iter'
version = os.getenv('IMAS_VERSION')[0]

yamlpath = '/home/ITER/mitterv/codes/pyworkflow/pulse_schedule_config.yaml'

file = open(yamlpath, 'r')
data =  yaml.load(file)
file.close()

shot_nr = data.get('shot number')
run_nr  = data.get('run number')

nbi_power = np.asarray(data.get('nbi power'))
nbi_t     = np.asarray(data.get('nbi time'))
ec_power  = np.asarray(data.get('ec power'))
ec_t      = np.asarray(data.get('ec time'))
ic_power  = np.asarray(data.get('ic power'))
ic_t      = np.asarray(data.get('ic time'))
ic_frequency = data.get('frequency ic')
ec_frequency = data.get('frequency ec')

print('open input and output file')
input = imas.ids(shot_nr, run_nr, 0,0)
input.open_env('mitterv', 'iter','3')
output = imas.ids(shot_nr, 222, 0,0)
output.create_env(user,tokamakname, version)
idx_out = output.distributions.idx


input.pulse_schedule.get()
output.pulse_schedule = copy.deepcopy(input.pulse_schedule)
output.pulse_schedule.setExpIdx(idx_out)



pulse_time = np.asarray(output.pulse_schedule.time)
#zeros  = np.zeros(np.size(timesl))

### FROM YAML
## SET POWER 
# nbi
if len(nbi_power) > 0:
    for i in range(len(nbi_t)): 
        output.pulse_schedule.nbi.unit[2].power.reference.data[pulse_time > nbi_t[i]] = nbi_power[i]
else: 
    print('using nbi power from pulse schedule input')

# ec
if len(ec_power) > 0:
    for i in range(len(ec_t)): 
        output.pulse_schedule.ec.antenna[0].power.reference.data[pulse_time > ec_t[i]] = ec_power[i]
else: 
    print('using ec power from pulse schedule input')
        
# ic
if len(ic_power) > 0:
    for i in range(len(ic_t)):
        output.pulse_schedule.ic.antenna[0].power.reference.data[pulse_time > ic_t[i]] = ic_power[i]
else: 
    print('using ic power from pulse schedule input')



# SET ENERGY (NBI)
print('set nbi energy')
nbi_power_data = output.pulse_schedule.nbi.unit[2].power.reference.data 
output.pulse_schedule.nbi.unit[2].energy.reference.data = 1e6 * (nbi_power_data/(33e6))**(1/2.5)   # E_nbi = 1 MeV * (P_nbi / 33MW)^(1/2.5)


# SET FREQUENCIES (EC and IC)
print('set ec frequency')
if ec_frequency > 0: 
    
    output.pulse_schedule.ec.antenna[0].frequency.reference.data[:] = ec_frequency
   
if ic_frequency > 0:
    output.pulse_schedule.ic.antenna[0].frequency.reference.data[:] = ic_frequency

output.pulse_schedule.put()




