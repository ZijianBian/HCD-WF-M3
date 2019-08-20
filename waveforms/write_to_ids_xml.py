def ec_write_to_ids_and_xml(ec_dict, ec_antennas0): #, ntime_slices, t_begin, t_end):

    import numpy as np



    is_config = True
    i = 0
    for iant in ec_dict:
        
        if is_config == True:
            is_config = False
        else:
            for elem in ec_dict[iant]: 

                

                exec(ec_dict[iant][elem])
                   
                print('ec_antennas0.antenna['+str(i)+'].'+elem)

                print(exec('ec_antennas0.antenna['+str(i)+'].'+elem+' = '+ str(ec_dict[iant][elem]))
                print(exec('ec_antennas0.antenna['+str(i)+'].'+elem))

                 #   print(exec('str(type(ec_antennas0.antenna[i].'+elem+'))[8:-2]'))
                   # print(typestr)
                #    exec('n = '+typestr+'(ec_antennas0.antenna[i].'+elem+')')

               #     print(n)
          
                    
                    
                 #   print('pass')
                    

                    ## ADJUST TIME DEPENDENT VARIABLES TO THE TIMESTEP
                    
                    
                  #  np.linspace(t_begin, t_end, ntime_slices)
                    
                    


                  #  exec('ec_antennas0.antenna[i].'+elem+' = split_float_list')

            #     exec('print(ec_antennas0.antenna[i].'+elem+', type( ec_antennas0.antenna[i].'+elem+') )')

            i += 1
    
 #   ec_antennas0.put()
