def write_to_ids(sys_dict, param,source ): #, ntime_slices, t_begin, t_end):
    import os, sys, imas, copy
    import numpy as np
    import matplotlib.pyplot as plt
    import pdb
    from pyal import ALEnv
    from random import randint
    from get_MDdb2ids import get_MDdb2ids # Machine Description data from SQL DB
    from idsdisp import idsprint,idsrprint

    #### OPEN IDS: 
    # remote and local database environment
    shot       = param['shot_nr']
    run_in     = param['run_in']
    run_out    = param["run_out"]
    machine    = param['machine'] # assumed to be the same for remote/local DB
    user_in    = param['user']
    local_user = os.getenv('USER')
    version    = os.getenv('IMAS_VERSION')[0]
    
    # IF THE REQUIRED LOCAL DATABASE DOES NOT EXIST --> CREATE IT
    if not os.path.exists(os.getenv('HOME')+'/public/imasdb/'+machine):
        print('--> Create local database '+os.getenv('HOME')+'/public/imasdb/'+machine)
        os.popen("imasdb "+machine).read()

    # OPEN INPUT DATAFILE
    #print('Open input datafile %s/%s for user = %s, machine = %s'%(str(shot),str(run_in),str(user_in),str(machine)))
    #input = imas.ids(shot,run_in,0,0)
    #input.open_env(user_in,machine,version)
    #idx_in = input.core_profiles.idx

    # OPEN OR CREATE OUTPUT DATAFILE
    output = imas.ids(shot,run_out,0,0)
    print('----------------------------------------------------------------------------')
    try:
        output.open_env(local_user,machine,version)    
        print('Open existing output datafile %s/%s for user = %s, machine = %s'%(str(shot),str(run_out),str(local_user),str(machine)))
    except Exception:
        print('Output datafile does not exist --> Create it...')
        print('--> Create output datafile %s/%s for user = %s, machine = %s'%(str(shot),str(run_out),str(local_user),str(machine)))
        output.create_env(local_user,machine,version)
    idx_out = output.core_profiles.idx

    # DEFINE THE SHOT/RUN NUMBERS AND LOCATION OF THE TEMPORARY FILE
    exist = 'yes'
    shot_tmp = 9988
    while exist == 'yes':
        run_tmp  = randint(0,9999)
        tmp = imas.ids(shot_tmp,run_tmp,0,0)
        try:
            tmp.open_env(user,tokamakname,version)
        except Exception:
            exist = 'no'
    tmp_db = ALEnv(shot=shot_tmp, run_temp=run_tmp, machine_temp=tokamakname).ids_tmp

    ## PREPARE PUTTING TO IDS STRUCTURE -> adjust the number of timesteps
    sys_dict_temp =  {}
    is_config = True
    i = 0
    for iant in sys_dict:
        if is_config == True:
             is_config = False
        else:
            sys_dict_temp[iant] = copy.deepcopy(sys_dict[iant])
            for elem in sys_dict[iant]:
                try: 
                    sys_dict_temp[iant][elem]  = [float(i) for i in sys_dict[iant][elem].split()]
                except:
                    try:
                        for id in range(len(sys_dict_temp[iant][elem])):
                            sys_dict_temp[iant][elem][id] = [float(i) for i in sys_dict[iant][elem][id].split()]
                       
                    except:
                        sys_dict_temp[iant][elem]  =  sys_dict[iant][elem]
                
                               
    for iant in sys_dict_temp: 
        for elem in sys_dict_temp[iant]:
       
            if '_time' not in elem:
                i = 0
                if isinstance(sys_dict_temp[iant][elem], str): 
                # if it is still a string it means that it was not possible to convert it into a list -> aka things that should stay strings like the name
                    pass 

                elif len(sys_dict_temp[iant][elem]) <=1:
                # if it is not a string, but now a list with only one or zero entries, then there is  no need to spread it to the number of timeslices (interpolate) (?) if this is a wrong assumption, just delete the elif condition:  the reason to use the timevsystor to check if it contains only one entry is because it might be a two dimensional entry, in which case the length of the entry itself would be the nr of dimensions
                    pass

                elif isinstance(sys_dict_temp[iant][elem][0], list):
                ## if it is a list, this means we are dealing with a timedependent two or more dimensional entry, which means we have to iterate through the dimensions for interpolation
                    for id in range(len(sys_dict_temp[iant][elem])):
                        val_list = sys_dict_temp[iant][elem][id]
                        t_list = sys_dict_temp[iant][elem+'_time']
                        
                        timearray = np.linspace(float(sys_dict['configure']['t_begin']), float(sys_dict['configure']['t_end']), int(sys_dict['configure']['n_time_slices']))
                        interpolated_values = np.interp(timearray, t_list, val_list)
                     
                        sys_dict_temp[iant][elem][id] = interpolated_values

                    sys_dict_temp[iant][elem+'_time'] = timearray


                else: 
                ## the only option left, is that we are dealing with a timedependent one dimensional entry: so we treat it the same as before, but we dont have to iterate through the dimensions

                    val_list = sys_dict_temp[iant][elem]
                    t_list = sys_dict_temp[iant][elem+'_time']
                    
                    timearray = np.linspace(float(sys_dict['configure']['t_begin']), float(sys_dict['configure']['t_end']), int(sys_dict['configure']['n_time_slices']))
                    interpolated_values = np.interp(timearray, t_list, val_list)
                
                    sys_dict_temp[iant][elem] = interpolated_values
                    sys_dict_temp[iant][elem+'_time'] = timearray

  
    # -------------------------- set to ids 

    def set_ec(ec_dict_temp):

        #input.ec_launchers.get()
        #output.ec_launchers = copy.deepcopy(input.ec_launchers)
        #output.ec_launchers.setExpIdx(idx_out)

        is_config = True

        # Allocate all necessary variables
        output.ec_launchers.launcher.resize(len(ec_dict_temp))
        i = 0
        for iant in ec_dict_temp:
            output.ec_launchers.launcher[i].power_launched.data.resize(len(ec_dict_temp[iant]['power_launched']))
            output.ec_launchers.launcher[i].power_launched.time.resize(len(ec_dict_temp[iant]['power_launched_time']))
            output.ec_launchers.launcher[i].frequency.data.resize(len(ec_dict_temp[iant]['frequency']))
            output.ec_launchers.launcher[i].frequency.time.resize(len(ec_dict_temp[iant]['frequency_time']))
            output.ec_launchers.launcher[i].mode.data.resize(len(ec_dict_temp[iant]['mode']))
            output.ec_launchers.launcher[i].mode.time.resize(len(ec_dict_temp[iant]['mode_time']))
            output.ec_launchers.launcher[i].launching_position.time.resize(len(ec_dict_temp[iant]['launching_position_time']))
            output.ec_launchers.launcher[i].launching_position.r.resize(len(ec_dict_temp[iant]['launching_position_r']))
            output.ec_launchers.launcher[i].launching_position.z.resize(len(ec_dict_temp[iant]['launching_position_z']))
            output.ec_launchers.launcher[i].launching_position.phi.resize(len(ec_dict_temp[iant]['launching_position_phi']))
            output.ec_launchers.launcher[i].steering_angle_pol.data.resize(len(ec_dict_temp[iant]['steering_angle_pol']))
            output.ec_launchers.launcher[i].steering_angle_pol.time.resize(len(ec_dict_temp[iant]['steering_angle_pol_time']))
            output.ec_launchers.launcher[i].steering_angle_tor.data.resize(len(ec_dict_temp[iant]['steering_angle_tor']))
            output.ec_launchers.launcher[i].steering_angle_tor.time.resize(len(ec_dict_temp[iant]['steering_angle_tor_time']))    
            output.ec_launchers.launcher[i].beam.spot.size.data.resize(len(ec_dict_temp[iant]['beam_spot_size']))
            output.ec_launchers.launcher[i].beam.spot.size.time.resize(len(ec_dict_temp[iant]['beam_spot_size_time']))
            output.ec_launchers.launcher[i].beam.spot.angle.data.resize(len(ec_dict_temp[iant]['beam_spot_angle']))
            output.ec_launchers.launcher[i].beam.spot.angle.time.resize(len(ec_dict_temp[iant]['beam_spot_angle_time']))
            output.ec_launchers.launcher[i].beam.phase.curvature.data.resize(len(ec_dict_temp[iant]['beam_phase_curvature']))
            output.ec_launchers.launcher[i].beam.phase.curvature.time.resize(len(ec_dict_temp[iant]['beam_phase_curvature_time']))
            output.ec_launchers.launcher[i].beam.phase.angle.data.resize(len(ec_dict_temp[iant]['beam_phase_angle']))
            output.ec_launchers.launcher[i].beam.phase.angle.time.resize(len(ec_dict_temp[iant]['beam_phase_angle_time']))
            i += 1

        # Fill all variables with information from the xml file / interface edition
        i = 0
        for iant in ec_dict_temp:
            output.ec_launchers.launcher[i].name = ec_dict_temp[iant]['name']
            output.ec_launchers.launcher[i].power_launched.data = ec_dict_temp[iant]['power_launched']
            output.ec_launchers.launcher[i].power_launched.time = ec_dict_temp[iant]['power_launched_time']
            output.ec_launchers.launcher[i].frequency.data = ec_dict_temp[iant]['frequency'][0]
            output.ec_launchers.launcher[i].frequency.time = ec_dict_temp[iant]['frequency_time'][0]
            output.ec_launchers.launcher[i].mode.data = ec_dict_temp[iant]['mode']
            output.ec_launchers.launcher[i].mode.time = ec_dict_temp[iant]['mode_time']
            output.ec_launchers.launcher[i].launching_position.time  = ec_dict_temp[iant]['launching_position_time']
            output.ec_launchers.launcher[i].launching_position.r  = ec_dict_temp[iant]['launching_position_r']
            output.ec_launchers.launcher[i].launching_position.z = ec_dict_temp[iant]['launching_position_z']
            output.ec_launchers.launcher[i].launching_position.phi = ec_dict_temp[iant]['launching_position_phi']
            output.ec_launchers.launcher[i].steering_angle_pol.data = ec_dict_temp[iant]['steering_angle_pol']
            output.ec_launchers.launcher[i].steering_angle_pol.time= ec_dict_temp[iant]['steering_angle_pol_time']
            output.ec_launchers.launcher[i].steering_angle_tor.data = ec_dict_temp[iant]['steering_angle_tor']
            output.ec_launchers.launcher[i].steering_angle_tor.time = ec_dict_temp[iant]['steering_angle_tor_time']
            output.ec_launchers.launcher[i].beam.spot.size.data = ec_dict_temp[iant]['beam_spot_size']
            output.ec_launchers.launcher[i].beam.spot.size.time = ec_dict_temp[iant]['beam_spot_size_time']
            output.ec_launchers.launcher[i].beam.spot.angle.data = ec_dict_temp[iant]['beam_spot_angle']
            output.ec_launchers.launcher[i].beam.spot.angle.time = ec_dict_temp[iant]['beam_spot_angle_time']
            output.ec_launchers.launcher[i].beam.phase.curvature.data = ec_dict_temp[iant]['beam_phase_curvature']
            output.ec_launchers.launcher[i].beam.phase.curvature.time = ec_dict_temp[iant]['beam_phase_curvature_time']
            output.ec_launchers.launcher[i].beam.phase.angle.data = ec_dict_temp[iant]['beam_phase_angle']
            output.ec_launchers.launcher[i].beam.phase.angle.time = ec_dict_temp[iant]['beam_phase_angle_time']
            i += 1

        # Save IDS to local database
        output.ec_launchers.ids_properties.homogeneous_time = 0
        output.ec_launchers.time.resize(len(output.ec_launchers.launcher[0].power_launched.time))
        output.ec_launchers.time = output.ec_launchers.launcher[0].power_launched.time
        output.ec_launchers.put()
        print('--> Saved ec_launchers IDS.')
       
    def set_ic(ic_dict_temp):

        is_config = True
    
        #input.ic_antennas.get()
        #output.ic_antennas = copy.deepcopy(input.ic_antennas)
        #output.ic_antennas.setExpIdx(idx_out)
           
        # Allocate all necessary variables
        output.ic_antennas.antenna.resize(len(ic_dict_temp))
        i = 0
        for iant in ic_dict_temp:
            output.ic_antennas.antenna[i].frequency.data.resize(len(ic_dict_temp[iant]['frequency']))
            output.ic_antennas.antenna[i].frequency.time.resize(len(ic_dict_temp[iant]['frequency_time']))
            output.ic_antennas.antenna[i].power_launched.data.resize(len(ic_dict_temp[iant]['power_launched']))
            output.ic_antennas.antenna[i].power_launched.time.resize(len(ic_dict_temp[iant]['power_launched_time']))
            i += 1

        # Fill all variables with information from the xml file / interface edition
        i = 0
        for iant in ic_dict_temp:
            output.ic_antennas.antenna[i].name = ic_dict_temp[iant]['name']
            output.ic_antennas.antenna[i].identifier = ic_dict_temp[iant]['identifier']
            output.ic_antennas.antenna[i].frequency.data = ic_dict_temp[iant]['frequency']
            output.ic_antennas.antenna[i].frequency.time = ic_dict_temp[iant]['frequency_time']
            output.ic_antennas.antenna[i].power_launched.data = ic_dict_temp[iant]['power_launched']
            output.ic_antennas.antenna[i].power_launched.time = ic_dict_temp[iant]['power_launched_time']                
            i += 1

        # Save IDS to local database
        output.ic_antennas.ids_properties.homogeneous_time = 0
        output.ic_antennas.time.resize(len(output.ic_antennas.antenna[0].power_launched.time))
        output.ic_antennas.time = output.ic_antennas.antenna[0].power_launched.time
        output.ic_antennas.put()
        print('--> Saved ic_antennas IDS.')

    def set_nbi(nbi_dict_temp):
     
        #input.nbi.get()
        #output.nbi = copy.deepcopy(input.nbi)
        #output.nbi.setExpIdx(idx_out)

        # Get machine description data from SQL database
        nbi = get_MDdb2ids('nbi','ITER_NBI_geometry_off_on')

        # Allocate all necessary variables
        output.nbi.unit.resize(len(nbi_dict_temp))
        i = 0
        for iunit in nbi_dict_temp:
            output.nbi.unit[i].power_launched.data.resize(len(nbi_dict_temp[iunit]['power_launched']))
            output.nbi.unit[i].power_launched.time.resize(len(nbi_dict_temp[iunit]['power_launched_time']))
            output.nbi.unit[i].energy.data.resize(len(nbi_dict_temp[iunit]['energy']))
            output.nbi.unit[i].energy.time.resize(len(nbi_dict_temp[iunit]['energy_time']))
            output.nbi.unit[i].beam_current_fraction.data.resize(len(nbi_dict_temp[iunit]['beam_current_fraction']))
            output.nbi.unit[i].beam_current_fraction.time.resize(len(nbi_dict_temp[iunit]['beam_current_fraction_time']))
            output.nbi.unit[i].beam_power_fraction.data.resize(len(nbi_dict_temp[iunit]['beam_power_fraction']))
            output.nbi.unit[i].beam_power_fraction.time.resize(len(nbi_dict_temp[iunit]['beam_power_fraction_time']))
            i += 1

        # Fill all variables with information from the xml file / interface edition
        i = 0
        for iunit in nbi_dict_temp:
            output.nbi.unit[i].name = nbi_dict_temp[iunit]['name']
            output.nbi.unit[i].identifier = nbi_dict_temp[iunit]['identifier']
            output.nbi.unit[i].species.a = nbi_dict_temp[iunit]['species_a'][0]
            output.nbi.unit[i].species.z_n = nbi_dict_temp[iunit]['species_z'][0]
            output.nbi.unit[i].power_launched.data = nbi_dict_temp[iunit]['power_launched']
            output.nbi.unit[i].power_launched.time = nbi_dict_temp[iunit]['power_launched_time']
            output.nbi.unit[i].energy.data = nbi_dict_temp[iunit]['energy']
            output.nbi.unit[i].energy.time = nbi_dict_temp[iunit]['energy_time']
            output.nbi.unit[i].beam_current_fraction.data = nbi_dict_temp[iunit]['beam_current_fraction']
            output.nbi.unit[i].beam_current_fraction.time = nbi_dict_temp[iunit]['beam_current_fraction_time']
            output.nbi.unit[i].beam_power_fraction.data = nbi_dict_temp[iunit]['beam_power_fraction']
            output.nbi.unit[i].beam_power_fraction.time = nbi_dict_temp[iunit]['beam_power_fraction_time']
            i += 1

        # Save IDS to local database
        output.nbi.ids_properties.homogeneous_time = 0.
        output.nbi.time.resize(len(output.nbi.unit[0].power_launched.time))
        output.nbi.time = output.nbi.unit[0].power_launched.time
        idsprint('output.nbi')
        pdb.set_trace()
        output.nbi.put()
        print('--> Saved nbi IDS.')
        
    if source == 'ec':
        set_ec(sys_dict_temp)
    
    if source == 'ic':
        set_ic(sys_dict_temp)

    if source == 'nbi':
        set_nbi(sys_dict_temp)

    print('----------------------------------------------------------------------------')
    #input.close()
    output.close()
