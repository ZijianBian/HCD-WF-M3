#!/bin/bash

python hcd_nogui -c data/DT_baseline_example || exit 1
python hcd_nogui -c tests/data/EC_IC_NBI || exit 1
python hcd_nogui -c tests/data/FOPLA_TEST || exit 1
python hcd_nogui -c tests/data/GRAYSCALE || exit 1