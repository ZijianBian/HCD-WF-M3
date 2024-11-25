#!/bin/bash
source /etc/profile.d/modules.sh
source ./ci-sdcc/utils.sh
##########################################################################################
#                     Set environment based on toolchain                                 #
##########################################################################################
module use /work/imas/etc/modules/all
module use -p /work/imas/opt/bamboo_deploy/easybuild/modules/all

# expand aliases
shopt -s expand_aliases

#print hostname
hostname -f

IMAS_EXISTS=$(module -r -t list 2>&1 | grep -E "IMAS/"  | head -n 1)
if [ -n "$IMAS_EXISTS" ]; then
    echo "> Found already loaded IMAS Module : $IMAS_EXISTS"
    IMAS_MODULE_VERSION="$IMAS_EXISTS"
    ACCESS_LAYER_VERSION=$(echo "$AL_VERSION" | cut -d '.' -f 1)
    TOOLCHAIN_VERSION=$(echo "$IMAS_EXISTS" | awk -F '-' '{print $(NF-1)"-"$NF}')
else
    echo "> IMAS Module is not loaded"
fi

if [ -n "$1" ] || [ -n "$2" ]; then
    echo "> Compiling with $1 and Access Layer $2 with latest version of installed modules.Previously loaded modules will be purged.."
    module purge
    # If toolchain version is passed then purge all modules
    if [ -n "$1" ]; then
        TOOLCHAIN_VERSION="$1"
    fi

    # Get AL version
    if [ -n "$2" ]; then
        ACCESS_LAYER_VERSION="$2"
    else
        ACCESS_LAYER_VERSION="5"
    fi
fi

if [ -z "$TOOLCHAIN_VERSION" ]; then
    echo "> No toolchain found, Setting it to default : intel-2023b"
    TOOLCHAIN_VERSION="intel-2023b"
fi

if [ -z "$ACCESS_LAYER_VERSION" ]; then
    ACCESS_LAYER_VERSION="5"
fi

echo "> Building for $TOOLCHAIN_VERSION and Access Layer $ACCESS_LAYER_VERSION"

if [[ $TOOLCHAIN_VERSION == *"intel"* ]]; then
    FC="ifort"
fi
if [[ $TOOLCHAIN_VERSION == *"foss"* ]]; then
    FC="gfortran"
fi

if [ -z "$IMAS_EXISTS" ]; then
    IMAS_MODULE_VERSION=$(getIMASModuleName "$TOOLCHAIN_VERSION" "$ACCESS_LAYER_VERSION")
    # load IMAS module first
    echo "> IMAS is not loaded.. Loading Module $IMAS_MODULE_VERSION"
    module load "$IMAS_MODULE_VERSION"
fi

GCCcore_VERSION=$(getGCCcoreVersion)

buildtime_dependencies="./ci-sdcc/buildtime_dependencies.txt"
runtime_dependencies="./ci-sdcc/runtime_dependencies.txt"
# Check if the file exists
if [ ! -f "$buildtime_dependencies" ]; then
    echo "File $buildtime_dependencies not found."
    return 1
fi

# Check if the file exists
if [ ! -f "$runtime_dependencies" ]; then
    echo "File $runtime_dependencies not found."
    return 1
fi
echo "> Listing available modules"
echo "-------------------------------------------------------"
echo "> build time modules"

declare -a BUILDMODULES=()
declare -a RUNMODULES=()
declare -a EBBUILDMODULES=()
declare -a EBBRUNMODULES=()


# actors have version suffix so better to provide them as EXTERNAL_MODULE
actorslist=("GENRAY" "GRAY ""GRAYSCALE" "TORBEAM" "TORAY" "HCD2CORE_PROFILES" "HCD2CORE_SOURCES" "HCD_MERGERS")

counter=0
# Read the file line by line
while IFS= read -r line || [[ -n $line ]]; do
    # for empty string continue
    if [[ -z "${line// /}" ]]; then
        counter=$(("$counter" + 1))
        continue
    fi
    isModuleNameSolved=no
    for actor in "${actorslist[@]}"; do
        if [[ "$line" == "$actor" ]]; then
            module_version=$(getModuleName "$line" "$TOOLCHAIN_VERSION" "$GCCcore_VERSION")
            RUNMODULES["$counter"]="$module_version"
            EBBRUNMODULES["$counter"]="('$module_version', EXTERNAL_MODULE),"
            isModuleNameSolved=yes
            break
        fi
    done
    if [[ $isModuleNameSolved == "yes" ]]; then
        counter=$(("$counter" + 1))
        continue
    fi
    # latest module version as it is not given
    if [[ $line == *"IMAS"* ]]; then
        echo "Using latest version of IMAS $IMAS_MODULE_VERSION"
        BUILDMODULES["$counter"]="$IMAS_MODULE_VERSION"
        EBBUILDMODULES["$counter"]="('$IMAS_MODULE_VERSION', EXTERNAL_MODULE),"
    else
        module_version=$(getModuleName "$line" "$TOOLCHAIN_VERSION" "$GCCcore_VERSION")
        echo "Using latest version of $line $module_version"
        BUILDMODULES["$counter"]="$module_version"
        EBBUILDMODULES["$counter"]=$(getModuleNameAndVersion "$module_version")

    fi
    counter=$(("$counter" + 1))
done <"$buildtime_dependencies"

counter=0
while IFS= read -r line || [[ -n $line ]]; do
    line="${line// /}"
    # for empty string continue
    if [[ -z "$line" ]]; then
        counter=$(("$counter" + 1))
        continue
    fi
    isModuleNameSolved=no
    for actor in "${actorslist[@]}"; do
        if [[ "$line" == "$actor" ]]; then
            module_version=$(getModuleName "$line" "$TOOLCHAIN_VERSION" "$GCCcore_VERSION")
            RUNMODULES["$counter"]="$module_version"
            EBBRUNMODULES["$counter"]="('$module_version', EXTERNAL_MODULE),"
            isModuleNameSolved=yes
            break
        fi
    done
    if [[ $isModuleNameSolved == "yes" ]]; then
        counter=$(("$counter" + 1))
        continue
    fi
    # latest module version as it is not given
    if [[ $line == *"IMAS"* ]]; then
        echo "Using latest version of IMAS $IMAS_MODULE_VERSION"
        RUNMODULES["$counter"]="$IMAS_MODULE_VERSION"
        EBBRUNMODULES["$counter"]="('$IMAS_MODULE_VERSION', EXTERNAL_MODULE),"
    else
        module_version=$(getModuleName "$line" "$TOOLCHAIN_VERSION" "$GCCcore_VERSION")
        echo "Using latest version of $line $module_version"
        RUNMODULES["$counter"]="$module_version"
        EBBRUNMODULES["$counter"]=$(getModuleNameAndVersion "$module_version")

    fi
    counter=$(("$counter" + 1))
done <"$runtime_dependencies"
echo "-------------------------------------------------------"

echo "> Details of environment"
echo "    TOOLCHAIN_VERSION : $TOOLCHAIN_VERSION"
echo "    GCCcore_VERSION : $GCCcore_VERSION"
echo "    IMAS VERSION : $IMAS_MODULE_VERSION"
echo "    BUILDMODULES : " "${BUILDMODULES[@]}"
echo "    RUNMODULES : " "${RUNMODULES[@]}"
echo "    EBBUILDMODULES : " "${EBBUILDMODULES[@]}"
echo "    EBRUNMODULES : " "${EBBRUNMODULES[@]}"
echo "    Compiler : $FC"
echo "-------------------------------------------------------"


echo "Loading modules..."
module purge
module load "${BUILDMODULES[@]}"
module load "${RUNMODULES[@]}"
echo "Done loading modules..."
