#!/bin/bash
python -m build
rm -rf hcdenv
python -m venv hcdenv
source hcdenv/bin/activate
pip install .
echo "Executing standalone"
# python hcd_nogui -c data/DT_baseline_example || exit 1
# python hcd_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcd_nogui -c tests/data/FOPLA_TEST || exit 1
hcd_nogui -c tests/data/GRAYSCALE 

echo "Executing single time slice"
# python hcdslice_nogui -c data/DT_baseline_example || exit 1
# python hcdslice_nogui -c tests/data/EC_IC_NBI || exit 1
# python hcdslice_nogui -c tests/data/FOPLA_TEST || exit 1
hcdslice_nogui -c tests/data/GRAYSCALE
deactivate