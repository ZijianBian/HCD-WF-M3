def ec_write_to_ids_and_xml(ec_dict, param): #, ntime_slices, t_begin, t_end):
    import os, sys, imas, copy
    import numpy as np
    import matplotlib.pyplot as plt


    #### OPEN IDS: 
    # remote and local database environment
    user_in     = param['user']
    local_user  = os.getenv('USER')
    tokamakname = param['machine'] # assumed to be the same for remote/local DB
    version     = os.getenv('IMAS_VERSION')[0]
    
    # If the local database for the required tokamak does not exist yet: create it
    if not os.path.exists(os.getenv('HOME')+'/public/imasdb/'+tokamakname):
        print('--> Create local database '+os.getenv('HOME')+'/public/imasdb/'+tokamakname)
        os.popen("imasdb "+tokamakname).read()


    is_config = True
    i = 0

                   

    ## PREPARE PUTTING TO IDS STRUCTURE -> adjust the number of timesteps
    ec_dict_temp =  {}
    for iant in ec_dict:
        if is_config == True:
             is_config = False
        else:
            ec_dict_temp[iant] = copy.deepcopy(ec_dict[iant])
            for elem in ec_dict[iant]:
                try: 
                    ec_dict_temp[iant][elem]  = [float(i) for i in ec_dict[iant][elem].split()]
                except:
                    try:
                        for id in range(len(ec_dict_temp[iant][elem])):
                            ec_dict_temp[iant][elem][id] = [float(i) for i in ec_dict[iant][elem][id].split()]
                       
                    except:
                        ec_dict_temp[iant][elem]  =  ec_dict[iant][elem]
                
                               
    for iant in ec_dict_temp: 
        for elem in ec_dict_temp[iant]:
       
            if '_time' not in elem:
                i = 0
                if isinstance(ec_dict_temp[iant][elem], str): 
                # if it is still a string it means that it was not possible to convert it into a list -> aka things that should stay strings like the name
                    pass 

                elif len(ec_dict_temp[iant][elem]) <=1:
                # if it is not a string, but now a list with only one or zero entries, then there is  no need to spread it to the number of timeslices (interpolate) (?) if this is a wrong assumption, just delete the elif condition:  the reason to use the timevector to check if it contains only one entry is because it might be a two dimensional entry, in which case the length of the entry itself would be the nr of dimensions
                    pass 

                elif isinstance(ec_dict_temp[iant][elem][0], list):
                ## if it is a list, this means we are dealing with a timedependent two or more dimensional entry, which means we have to iterate through the dimensions for interpolation
                    for id in range(len(ec_dict_temp[iant][elem])):
                        val_list = ec_dict_temp[iant][elem][id]
                        t_list = ec_dict_temp[iant][elem+'_time']
                        
                        timearray = np.linspace(float(ec_dict['configure']['t_begin']), float(ec_dict['configure']['t_end']), int(ec_dict['configure']['n_time_slices']))
                        interpolated_values = np.interp(timearray, t_list, val_list)
                     
                        ec_dict_temp[iant][elem][id] = interpolated_values

                    ec_dict_temp[iant][elem+'_time'] = timearray


                else: 
                ## the only option left, is that we are dealing with a timedependent one dimensional entry: so we treat it the same as before, but we dont have to iterate through the dimensions

                    val_list = ec_dict_temp[iant][elem]
                    t_list = ec_dict_temp[iant][elem+'_time']
                    
                    timearray = np.linspace(float(ec_dict['configure']['t_begin']), float(ec_dict['configure']['t_end']), int(ec_dict['configure']['n_time_slices']))
                    interpolated_values = np.interp(timearray, t_list, val_list)
                
                    ec_dict_temp[iant][elem] = interpolated_values
                    ec_dict_temp[iant][elem+'_time'] = timearray




  
# -------------------------- set to ids 
    print('open input and output file')
    input = imas.ids(param['shot_nr'], param['run_in'], 0,0)
    input.open_env(user_in,tokamakname,version)
    output  = imas.ids(param["shot_nr"], param["run_out"], 0,0)
    output.create_env(user_in,tokamakname,version)
    idx_out = output.core_profiles.idx

    input.ec_antennas.get()

    output.ec_antennas = copy.deepcopy(input.ec_antennas)
    output.ec_antennas.setExpIdx(idx_out)

               
    

    for iant in ec_dict_temp:
        print(iant)
        if is_config == True:
             is_config = False
        else:
            output.ec_antennas.antenna[i].name = ec_dict_temp[iant]['name']
            output.ec_antennas.antenna[i].power_launched.data = ec_dict_temp[iant]['power_launched']
            output.ec_antennas.antenna[i].power_launched.time = ec_dict_temp[iant]['power_launched_time']
            output.ec_antennas.antenna[i].frequency = ec_dict_temp[iant]['frequency'][0]
            output.ec_antennas.antenna[i].mode.data = ec_dict_temp[iant]['mode']
            output.ec_antennas.antenna[i].mode.time = ec_dict_temp[iant]['mode_time']
            output.ec_antennas.antenna[i].launching_position.r.data  = ec_dict_temp[iant]['launching_position_r']
            output.ec_antennas.antenna[i].launching_position.r.time  = ec_dict_temp[iant]['launching_position_r_time']
            output.ec_antennas.antenna[i].launching_position.z.data = ec_dict_temp[iant]['launching_position_z']
            output.ec_antennas.antenna[i].launching_position.z.time = ec_dict_temp[iant]['launching_position_z_time']
            output.ec_antennas.antenna[i].launching_position.phi.data = ec_dict_temp[iant]['launching_position_phi']
            output.ec_antennas.antenna[i].launching_position.phi.time = ec_dict_temp[iant]['launching_position_phi_time']
            output.ec_antennas.antenna[i].launching_angle_pol.data = ec_dict_temp[iant]['launching_angle_pol']
            output.ec_antennas.antenna[i].launching_angle_pol.time= ec_dict_temp[iant]['launching_angle_pol_time']
            output.ec_antennas.antenna[i].launching_angle_tor.data = ec_dict_temp[iant]['launching_angle_tor']
            output.ec_antennas.antenna[i].launching_angle_tor.time = ec_dict_temp[iant]['launching_angle_tor_time']
            output.ec_antennas.antenna[i].beam.spot.size.data = ec_dict_temp[iant]['beam_spot_size']
            output.ec_antennas.antenna[i].beam.spot.size.time = ec_dict_temp[iant]['beam_spot_size_time']
            output.ec_antennas.antenna[i].beam.spot.angle.data = ec_dict_temp[iant]['beam_spot_angle']
            output.ec_antennas.antenna[i].beam.spot.angle.time = ec_dict_temp[iant]['beam_spot_angle_time']
          #  output.ec_antennas.antenna[i].beam.phase.curvature.data = ec_dict_temp[iant]['beam_phase_curvature1']
            output.ec_antennas.antenna[i].beam.phase.curvature.time = ec_dict_temp[iant]['beam_phase_curvature_time']
            output.ec_antennas.antenna[i].beam.phase.angle.data = ec_dict_temp[iant]['beam_phase_angle']
            output.ec_antennas.antenna[i].beam.phase.angle.time = ec_dict_temp[iant]['beam_phase_angle_time']
                        
            i += 1

    output.ec_antennas.ids_properties.homogeneous_time = 0
    
    output.ec_antennas.put()

    print('saved ec waveform configuration')
