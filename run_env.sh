#!/bin/bash
source /home/ITER/bianz/public/git/repository/hcd-wf/snapshot_env.sh
PY_EXE="/home/ITER/bianz/public/git/repository/hcd-wf/devenv_m3/bin/python"
exec "$PY_EXE" "$@"
