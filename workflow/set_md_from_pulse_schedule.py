
import os,imas,sys,yaml, copy

def set_md_from_pulse_schedule(bundle):

    pulse_schedule0 = copy.deepcopy(bundle['pulse_schedule'])
    nbi0 = copy.deepcopy(bundle['nbi'])
    ec_antennas0 = copy.deepcopy(bundle['ec_antennas'])
    ic_antennas0 = copy.deepcopy(bundle['ic_antennas'])
       

    for uj in range(len(nbi0.unit)):
        nbi0.unit[uj].power_launched.data = pulse_schedule0.nbi.unit[2].power.reference.data
        nbi0.unit[uj].energy.data         = pulse_schedule0.nbi.unit[2].energy.reference.data
    for aj in range(len(ec_antennas0.antenna)):
        ec_antennas0.antenna[aj].frequency =           pulse_schedule0.ec.antenna[0].frequency.reference.data
        ec_antennas0.antenna[aj].power_launched.data = pulse_schedule0.ec.antenna[0].power.reference.data/3
    for aj in range(len(ic_antennas0.antenna)):    
        ic_antennas0.antenna[aj].frequency.data =      pulse_schedule0.ic.antenna[0].frequency.reference.data
        ic_antennas0.antenna[aj].power_launched.data = pulse_schedule0.ic.antenna[0].power.reference.data
        

    print('Set Machine Description IDSs with Pulse Schedule Data')

    IDS_BUNDLE = copy.deepcopy(bundle)
    IDS_BUNDLE['nbi'] = nbi0
    IDS_BUNDLE['ec_antennas'] = ec_antennas0
    IDS_BUNDLE['ic_antennas'] = ic_antennas0

    return IDS_BUNDLE

