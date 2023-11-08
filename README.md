
Python Heating Current And Drive Workflow
# For users
These instructions are for users who needs to run the H&CD workflow for physics analysis purpose.

## Get the source:
```
> git clone ssh://git@git.iter.org/wf/hcd.git
> git checkout develop
```

## Setup the environment
```
> cd hcd
> . config_hcd.sh
> pip install -r requirements.txt
```
You may need to provide path to compiled actors in `config_hcd.sh`
```
# Start from clean environment
module purge >&/dev/null

# Need to remove the stack limit to avoid segmentation fault inside codes
ulimit -Ss unlimited

# Load the default IMAS version
module load IMAS

# Workflow tools needed mostly for the HCD gui
module load WFtools
module load Waveform-Cooker/1.3.3-GCCcore-10.2.0

pip install -r requirements.txt

export ACTOR_FOLDER=~/public/PYTHON_ACTORS  <--- Change here
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
```

## Install HCDWorkflow using pip install
```
> python -m build # This will create distribution package
> pip install dist/HCDWorkflow-<version>-py3-none-any.whl # Install distribution package
```

## Using hcd workflow
```
# [hcd_nogui ] run standalone hcd workflow 
> hcd_nogui -c <configuration path> 

# [hcdslice_nogui] run hcd workflow on time slice
> hcdslice_nogui -c <configuration path> 

# [hcd_gui] run standalone hcd workflow using gui, create machine description using waveform cooker etc.
> hcd_gui 

# [hcd_batch] batch exectution of hcd_workflow
> hcd_batch 
```

# For developers

## First time usage:

### Get the source:
```
> git clone ssh://git@git.iter.org/wf/hcd.git
> git checkout develop
```


### Setup the environment
```
> cd hcd
> . config_hcd_iter_sdcc.sh
```


### Setup the different actors

```
> cd actor_install
> python actor_install.py --skipModules *.yml
```

You can select which actors you want to install by specifying a complete name instead of the  wildcard. Choose from the different \*.yml files available in this folder.

The build of each actor takes place inside a temporary folder called `build-<DATE>-<TIME>`. This folder is not deleted automatically.


### Run

```
> cd .. #make sure we are back in hcd folder
> python hcd_gui.py
```

## Regular usage

You just need to setup the environment and  launch the GUI:
```
> cd hcd
> . config_hcd_iter_sdcc.sh
> python hcd_gui.py
```

## Updating the actors

When an actor gets updated, you want to use that new version. Simply go to `actor_install` folder and run `actor_install.py` just for that actor. For example, for the ascot actor:
```
cd actor_install
python actor_install.py --skipModules ascot.yml
```

# Further instructions

For usage instructions, see [this confluence page](https://confluence.iter.org/display/IMP/How+to+install+and+run+the+Python+HCD+workflow).

At the moment we don't have a central installation of hcd.
 
