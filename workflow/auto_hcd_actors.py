import os, imas, sys, copy

actor_path = os.path.join(os.getenv("KEPLER"), "imas/src/org/iter/imas/python")
list_of_actors = ["genray","gray","iccoup","Cyrano","tomcat","lion","StixReDist","nemo","bbnbi","risk","spot","ascot4serial","ascot4parallel","afsi","spot","ascot4serial","ascot4parallel","hcd2core_sources","hcd2core_profiles", "empty_distribution_sources", "empty_waves", "empty_distributions"]


for name in list_of_actors:
   sys.path[:0] = [os.path.join(actor_path,name)]
   globals()[name] = getattr(__import__(name), name)




def ec_wave_solver(bundle, parameters): 
   if parameters["ec_wave_solver"] == 1:
       print("--GENRAY--")
       waves_temp = genray(bundle["equilibrium"], bundle["core_profiles"], bundle["ec_antennas"], (parameters["input_path"]+"/ECRH/input_genray.xml"),  "mpi_local")

   elif parameters["ec_wave_solver"] == 2:
       print("--GRAY--")
       waves_temp = gray(bundle["equilibrium"], bundle["core_profiles"], bundle["ec_antennas"], (parameters["input_path"]+"/ECRH/input_gray.xml"))


   else: 
       waves_temp = empty_waves(bundle["core_profiles"])

   return(waves_temp)

def ic_coup(bundle, parameters): 
   if parameters["ic_coup"] == 1:
       print("--ICCOUP--")
       waves_temp = iccoup(bundle["equilibrium"], bundle["ic_antennas"], parameters["ic_wave_nr_toroidal_modes"], (parameters["input_path"]+"/ICRH/input_iccoup.xml"))


   else: 
       waves_temp = empty_waves(bundle["core_profiles"])

   return(waves_temp)

def ic_wave_solver(bundle, parameters): 
   if parameters["ic_wave_solver"] == 1:
       print("--CYRANO--")
       waves_temp = Cyrano(bundle["equilibrium"], bundle["core_profiles"], bundle["ic_antennas"], bundle["waves"], bundle["distributions"], (parameters["input_path"]+"/ICRH/input_Cyrano.xml"))

   elif parameters["ic_wave_solver"] == 2:
       print("--TOMCAT--")
       waves_temp = tomcat(bundle["equilibrium"], bundle["core_profiles"], bundle["ic_antennas"], bundle["distributions"], (parameters["input_path"]+"/ICRH/input_tomcat.xml"))

   elif parameters["ic_wave_solver"] == 3:
       print("--LION--")
       waves_temp = lion(bundle["equilibrium"], bundle["core_profiles"], bundle["ic_antennas"], bundle["waves"], (parameters["input_path"]+"/ICRH/input_lion.xml"))


   else: 
       waves_temp = empty_waves(bundle["core_profiles"])

   return(waves_temp)

def ic_wave_fp(bundle, parameters): 
   if parameters["ic_wave_fp"] == 1:
       print("--STIXREDIST--")
       distributions_temp = StixReDist(bundle["equilibrium"], bundle["core_profiles"], bundle["ic_antennas"], bundle["waves"], (parameters["input_path"]+"/ICRH/input_StixReDist.xml"))


   else: 
       distributions_temp = empty_distributions(bundle["core_profiles"])

   return(distributions_temp)

def nbi_source(bundle, parameters): 
   if parameters["nbi_source"] == 1:
       print("--NEMO--")
       distribution_sources_temp = nemo(bundle["equilibrium"], bundle["core_profiles"], bundle["nbi"], bundle["distribution_sources"], parameters["fokker_flag"], parameters["nmarker"], (parameters["input_path"]+"/NBI/input_nemo.xml"))

   elif parameters["nbi_source"] == 2:
       print("--BBNBI--")
       distribution_sources_temp = bbnbi(parameters["fokker_flag"], bundle["nbi"], bundle["wall"], bundle["core_profiles"], bundle["equilibrium"], (parameters["input_path"]+"/NBI/input_bbnbi.xml"))


   else: 
       distribution_sources_temp = empty_distribution_sources(bundle["core_profiles"])

   return(distribution_sources_temp)

def nbi_fp(bundle, parameters): 
   if parameters["nbi_fp"] == 1:
       print("--RISK--")
       distributions_temp = risk(bundle["equilibrium"], bundle["core_profiles"], bundle["nbi"], bundle["distribution_sources"], bundle["distributions"], parameters["dt_required"], (parameters["input_path"]+"/NBI/input_risk.xml"))

   elif parameters["nbi_fp"] == 2:
       print("--SPOT--")
       distributions_temp = spot(bundle["equilibrium"], bundle["core_profiles"], bundle["wall"], bundle["nbi"], bundle["distribution_sources"], bundle["distributions"], parameters["dt_required"], (parameters["input_path"]+"/NBI/input_spot.xml"),  "mpi_local")

   elif parameters["nbi_fp"] == 3:
       print("--ASCOT4SERIAL--")
       distributions_temp = ascot4serial(bundle["core_profiles"], bundle["equilibrium"], bundle["wall"], bundle["distribution_sources"], bundle["distributions"], (parameters["input_path"]+"/NBI/input_ascot4serial.xml"))

   elif parameters["nbi_fp"] == 4:
       print("--ASCOT4PARALLEL--")
       distributions_temp = ascot4parallel(bundle["core_profiles"], bundle["equilibrium"], bundle["wall"], bundle["distribution_sources"], bundle["distributions"], (parameters["input_path"]+"/NBI/input_ascot4parallel.xml"),  "mpi_local")


   else: 
       distributions_temp = empty_distributions(bundle["core_profiles"])

   return(distributions_temp)

def nuclear_source(bundle, parameters): 
   if parameters["nuclear_source"] == 1:
       print("--AFSI--")
       distribution_sources_temp = afsi(bundle["equilibrium"], bundle["core_profiles"], bundle["wall"], bundle["distributions"], (parameters["input_path"]+"/NUCLEAR/input_afsi.xml"))


   else: 
       distribution_sources_temp = empty_distribution_sources(bundle["core_profiles"])

   return(distribution_sources_temp)

def nuclear_fp(bundle, parameters): 
   if parameters["nuclear_fp"] == 1:
       print("--SPOT--")
       distributions_temp = spot(bundle["equilibrium"], bundle["core_profiles"], bundle["wall"], bundle["nbi"], bundle["distribution_sources"], bundle["distributions"], parameters["dt_required"], (parameters["input_path"]+"/NUCLEAR/input_spot.xml"),  "mpi_local")

   elif parameters["nuclear_fp"] == 2:
       print("--ASCOT4SERIAL--")
       distributions_temp = ascot4serial(bundle["core_profiles"], bundle["equilibrium"], bundle["wall"], bundle["distribution_sources"], bundle["distributions"], (parameters["input_path"]+"/NUCLEAR/input_ascot4serial.xml"))

   elif parameters["nuclear_fp"] == 3:
       print("--ASCOT4PARALLEL--")
       distributions_temp = ascot4parallel(bundle["core_profiles"], bundle["equilibrium"], bundle["wall"], bundle["distribution_sources"], bundle["distributions"], (parameters["input_path"]+"/NUCLEAR/input_ascot4parallel.xml"),  "mpi_local")


   else: 
       distributions_temp = empty_distributions(bundle["core_profiles"])

   return(distributions_temp)

def hcd2core_sources(bundle, parameters): 
   if parameters["hcd2core_sources"] == 1:
       print("--HCD2CORE_SOURCES--")
       core_sources_temp = hcd2core_sources(bundle["distributions"], bundle["distribution_sources"], bundle["waves"], bundle["core_profiles"])


   else: 
       core_sources_temp = empty_core_sources(bundle["core_profiles"])

   return(core_sources_temp)

def hcd2core_profiles(bundle, parameters): 
   if parameters["hcd2core_profiles"] == 1:
       print("--HCD2CORE_PROFILES--")
       core_profiles_temp = hcd2core_profiles(bundle["distributions"], bundle["core_profiles"], (parameters["input_path"]+"/profiles/input_hcd2core_profiles.xml"))


   else: 
       core_profiles_temp = empty_core_profiles(bundle["core_profiles"])

   return(core_profiles_temp)

