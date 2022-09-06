from wf_tools import find_nearest

#####################################################################################

# ------------------------------------------------------
# IS THE NBI SYSTEM ON?
# --> CHECK THE POWER ON ALL UNITS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_nbi_on(nbi, time_slice):
    if nbi.ids_properties.homogeneous_time==1:
        if len(nbi.time) > 0:
            time_array = nbi.time
        else:
            return False
        [tc, it] = find_nearest(time_array, time_slice)
        nunit = len(nbi.unit)
        power = 0.0
        if nunit > 0:
            for iunit in range(nunit):
                if nbi.unit[iunit].power_launched.data[it] > 0:
                    power = power + nbi.unit[iunit].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False
    else:
        nunit = len(nbi.unit)
        power = 0.0
        if nunit > 0:
            for iunit in range(nunit):
                if len(nbi.unit[iunit].power_launched.time) > 0:
                    time_array = nbi.unit[iunit].power_launched.time
                    [tc, it] = find_nearest(time_array, time_slice)
                    if nbi.unit[iunit].power_launched.data[it] > 0:
                        power = power + nbi.unit[iunit].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False


#####################################################################################

# ------------------------------------------------------
# IS THE EC SYSTEM ON?
# --> CHECK THE POWER ON ALL LAUNCHERS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_ec_on(ec_launchers, time_slice):
    if ec_launchers.ids_properties.homogeneous_time==1:
        if len(ec_launchers.time) > 0:
            time_array = ec_launchers.time
        else:
            return False
        [tc, it] = find_nearest(time_array, time_slice)
        nlauncher = len(ec_launchers.beam)
        power = 0.0
        if nlauncher > 0:
            for ilauncher in range(nlauncher):
                if ec_launchers.beam[ilauncher].power_launched.data[it] > 0:
                    power = power + ec_launchers.beam[ilauncher].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False
    else:
        nlauncher = len(ec_launchers.beam)
        power = 0.0
        if nlauncher > 0:
            for ilauncher in range(nlauncher):
                if len(ec_launchers.beam[ilauncher].power_launched.time) > 0:
                    time_array = ec_launchers.beam[ilauncher].power_launched.time
                    [tc, it] = find_nearest(time_array, time_slice)
                    if ec_launchers.beam[ilauncher].power_launched.data[it] > 0:
                        power = power + ec_launchers.beam[ilauncher].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False
        
#####################################################################################

# ------------------------------------------------------
# IS THE IC SYSTEM ON?
# --> CHECK THE POWER ON ALL ANTENNAS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_ic_on(ic_antennas, time_slice):
    if ic_antennas.ids_properties.homogeneous_time==1:
        if len(ic_antennas.time) > 0:
            time_array = ic_antennas.time
        else:
            return False
        [tc, it] = find_nearest(time_array, time_slice)
        nantenna = len(ic_antennas.antenna)
        power = 0.0
        if nantenna > 0:
            for iantenna in range(nantenna):
                if ic_antennas.antenna[iantenna].power_launched.data[it] > 0:
                    power = power + ic_antennas.antenna[iantenna].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False
    else:
        nantenna = len(ic_antennas.antenna)
        power = 0.0
        if nantenna > 0:
            for iantenna in range(nantenna):
                if len(ic_antennas.antenna[iantenna].power_launched.time) > 0:
                    time_array = ic_antennas.antenna[iantenna].power_launched.time
                    [tc, it] = find_nearest(time_array, time_slice)
                    if ic_antennas.antenna[iantenna].power_launched.data[it] > 0:
                        power = power + ic_antennas.antenna[iantenna].power_launched.data[it]
            if power == 0:
                return False
            else:
                return True
        else:
            return False
    
#####################################################################################

