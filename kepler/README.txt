# -----------------------------------------------------------------------
The Kepler workflow "hcd_kepler_wf_calling_python_wf.xml" calls
the Python H&CD workflow from Kepler. It uses the time loop from the 100% 
Kepler H&CD workflow developed by Thomas Johnson, except that the HCD 
component has been replaced by the H&CD Python workflow.
# -----------------------------------------------------------------------

In order to run it:

- Open the workflow in Kepler and change the 'hcd_location' variable to where
you have checked out your 'hcd' project

- The H&CD configuration files are located in your 'hcd/kepler/' folder. You 
can modify them from the GUI of the Python H&CD interface, executing
"python hcd_gui.py" and choosing 'hcd/kepler/' as the destination folder when
you save your configuration.

- Be careful: the shot, run numbers, tbegin, tend etc. that are used in the
Python H&CD workflow are those configured through the Python H&CD GUI 
interface: for consistency with the Kepler part of the workflow, they have 
to match the choices of the Kepler interface (user_in, machine_in, shot_in, run_in, run_out, dt_in, tbegin_in, tend_in).



