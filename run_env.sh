#!/bin/bash
export PYTHONNOUSERSITE=1

# 1. 加载全套 Intel 环境
source /etc/profile.d/modules.sh
module purge
module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
module load IMAS-AL-Fortran/5.4.0-intel-2023b-DD-3.42.0
module load INTERPOS/9.2.0-iimkl-2023b
module load XMLlib/3.3.2-intel-compilers-2023.2.1
module load TORBEAM/3.8.0-intel-2023b-DD-3.42.0
#module load Waveform-Cooker/1.6.0-GCCcore-13.2.0

# 2. 激活虚拟环境
source /home/ITER/bianz/public/git/repository/hcd-wf/devenv_m3/bin/activate

# 3. 路径配置
CURRENT_DIR="/home/ITER/bianz/public/git/repository/hcd-wf"
VENV_LIB="$CURRENT_DIR/devenv_m3/lib/python3.11/site-packages"

# 4. 关键：确保系统 MUSCLE3 在 Python 路径中
# (module load 通常会设置 PYTHONPATH，但为了防止被覆盖，我们将系统路径追加在后，或者依赖模块系统的自动设置)
# 这里我们采用“信任模块系统”策略，但把虚拟环境放在前面以加载其他库(如lxml)
# 注意：因为我们卸载了 venv 里的 muscle3，Python 在 venv 里找不到，自然会去系统路径找。
export PYTHONPATH="$VENV_LIB:$CURRENT_DIR:$PYTHONPATH"

# 5. 执行
exec "$CURRENT_DIR/devenv_m3/bin/python" "$@"
