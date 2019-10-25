module unload Python 
module unload matplotlib 
module unload PyYAML 
module unload UDA 
module unload IDStools
module unload PostgreSQL
module unload SWIG
module unload HDF5
module unload MDSplus
module unload MDSplus-Python
module unload Boost 
module unload Tkinter 
module unload Anaconda3

if [ "$FCOMPILER" == "gfortran" ]; then

  #echo gfortran
  module load Python/3.6.4-foss-2018a 
  module load matplotlib/2.1.2-foss-2018a-Python-3.6.4
  module load PyYAML/3.12-foss-2018a-Python-3.6.4 
  module load UDA/2.2.5-foss-2018a 
  module load IDStools/1.0.9-Python-3.6.4 
  module load PostgreSQL/10.3-foss-2018a-Python-3.6.4
  module load SWIG/3.0.12-foss-2018a-Python-3.6.4
  module load HDF5/1.10.1-foss-2018a
  module load MDSplus/7.46.1-foss-2018a
  module load MDSplus-Python/7.46.1-foss-2018a-Python-3.6.4
  module load Boost/1.66.0-foss-2018a # ?
  module load Tkinter/3.6.4-foss-2018a-Python-3.6.4

else

  #echo intel
  module load Python/3.6.4-intel-2018a 
  module load matplotlib/2.1.2-intel-2018a-Python-3.6.4
  module load PyYAML/3.12-intel-2018a-Python-3.6.4 
  module load UDA/2.2.5-intel-2018a 
  module load IDStools/1.0.9-Python-3.6.4 
  module load PostgreSQL/10.3-intel-2018a-Python-3.6.4
  module load SWIG/3.0.12-intel-2018a-Python-3.6.4
  module load HDF5/1.10.1-intel-2018a
  module load MDSplus/7.46.1-intel-2018a
  module load MDSplus-Python/7.46.1-intel-2018a-Python-3.6.4
  module load Boost/1.66.0-intel-2018a # ?
  module load Tkinter/3.6.4-intel-2018a-Python-3.6.4

fi
