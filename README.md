
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

For usage instructions, see [this confluence page](https://confluence.iter.org/display/IMP/How+to+run+the+Python+HCD+workflow).

At the moment we don't have a central installation of hcd.
 
