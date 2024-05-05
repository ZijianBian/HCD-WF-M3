#!/bin/bash
##########################################################################################
#                              Common functions                                          #
##########################################################################################
getIMASModuleName() {
    # This function returns IMAS module name
    # example : getIMASModuleName intel-2020b
    local TOOLCHAIN_VERSION=$1
    local ACCESS_LAYER_VERSION=$2
    local DD_VERSION=$3
    if [ -z "$ACCESS_LAYER_VERSION" ]; then
        ACCESS_LAYER_VERSION="4"
    else
        ACCESS_LAYER_VERSION="$2"
    fi
    if [ -z "$DD_VERSION" ]; then
        DD_VERSION="3"
    else
        DD_VERSION="$3"
    fi

    IMASVERSIONSLIST=$(module av -t IMAS/ 2>&1 | grep "$DD_VERSION.*.*-$ACCESS_LAYER_VERSION.*.*-$TOOLCHAIN_VERSION")

    if [[ $TOOLCHAIN_VERSION == *"intel"* ]]; then
        IMAS_MODULE_VERSION=$(echo "$IMASVERSIONSLIST" | grep "intel" | sort -rV | head -n 1)
    fi
    if [[ $TOOLCHAIN_VERSION == *"foss"* ]]; then
        IMAS_MODULE_VERSION=$(echo "$IMASVERSIONSLIST" | grep "foss" | sort -rV | head -n 1)
    fi
    echo "${IMAS_MODULE_VERSION//(default)/}"
}

getModuleName() {
    # This function returns available module name based on toolchain, GCCCore version and Module Name
    # example : getModuleName XMLlib intel-2020b 10.2.0
    local MODULE_NAME=$1
    local TOOLCHAIN_VERSION=$2
    local GCCcore_VERSION=$3
    IFS='-' read -r TNAME TVERSION <<<"$TOOLCHAIN_VERSION"

    # Check GCCcore version
    gcccore_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "GCCcore-$GCCcore_VERSION")
    MODULE_VERSION=$(echo "$gcccore_filtered" | sort -rV | head -n 1)
    if [ -z "$MODULE_VERSION" ]; then
        if [[ $TOOLCHAIN_VERSION == *"intel"* ]]; then
            intel_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "$TOOLCHAIN_VERSION")
            MODULE_VERSION=$(echo "$intel_filtered" | sort -rV | head -n 1)
        fi
        if [[ $TOOLCHAIN_VERSION == *"foss"* ]]; then
            foss_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "$TOOLCHAIN_VERSION")
            MODULE_VERSION=$(echo "$foss_filtered" | sort -rV | head -n 1)
            if [ -z "$MODULE_VERSION" ]; then
                gcc_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "GCC-$GCCcore_VERSION")
                MODULE_VERSION=$(echo "$gcc_filtered" | sort -rV | head -n 1)
            fi
            if [ -z "$MODULE_VERSION" ]; then
                gfbf_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "gfbf-""$TVERSION")
                MODULE_VERSION=$(echo "$gfbf_filtered" | sort -rV | head -n 1)
            fi
        fi
    fi
    # check if name has iimpi or gompi
    if [ -z "$MODULE_VERSION" ]; then
        if [[ $TOOLCHAIN_VERSION == *"intel"* ]]; then
            IIMPI_VERSION=${TOOLCHAIN_VERSION//intel/iimpi}
            iimpi_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "$IIMPI_VERSION")
            MODULE_VERSION=$(echo "$iimpi_filtered" | sort -rV | head -n 1)
        fi
        if [[ $TOOLCHAIN_VERSION == *"foss"* ]]; then
            GOMPI_VERSION=${TOOLCHAIN_VERSION//foss/gompi}
            gompi_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "$GOMPI_VERSION")
            MODULE_VERSION=$(echo "$gompi_filtered" | sort -rV | head -n 1)
        fi
    fi
    # TOOLCHAIN_VERSION and GCCcore_VERSION is not present
    if [ -z "$MODULE_VERSION" ]; then
        modules_filtered=$(module av -t "$MODULE_NAME"/ 2>&1 | grep "$MODULE_NAME")
        MODULE_VERSION=$(echo "$modules_filtered" | sort -rV | head -n 1)
    fi
    echo "${MODULE_VERSION//(default)/}"
}

getGCCcoreVersion() {
    # Get GCCcore version loaded
    # ensure that IMAS module should be loaded before calling this function
    GCCcore_VERSION=$(module -t list 2>&1 | grep GCCcore | head -n 1 | awk -F'/' '{print $2}')
    echo "$GCCcore_VERSION"
}

getModuleNameAndVersion() {
    local input=$1
    local mname=
    local mversion=
    mname=$(echo "$input" | cut -d'/' -f1)
    mversion=$(echo "$input" | cut -d'/' -f2)

    local version=${mversion%%-*}
    if [[ $input == *"intel"* ]] || [[ $input == *"foss"* ]] || [[ $input == *"gfbf"* ]] || [[ $input == *"GCC"* ]] || [[ $input == *"iimpi"* ]] || [[ $input == *"gompi"* ]]; then

        echo "('$mname', '$version'),"
    else
        echo "('$mname', '$version','', True),"
    fi
}

getUpperCase() {
    local input=$1
    local output=
    output=$(echo "$input" | tr '[:lower:]' '[:upper:]')
    echo "$output"
}

writeGitHeaderFile() {
    local HTTP_AUTH_BEARER_PASSWORD=$1
    HTTPHEADERS=http-headers.txt

    rm -rf "$HTTPHEADERS"

    if [ "x$HTTP_AUTH_BEARER_PASSWORD" != "x" ]; then
        cat >>"$HTTPHEADERS" <<EOF
iter.org::Authorization: Bearer $HTTP_AUTH_BEARER_PASSWORD
EOF
        EB_HTTP_OPTS="--http-header-fields-urlpat=${HTTPHEADERS}"
    fi
    echo "$EB_HTTP_OPTS"
}

deleteGitHeaderFile() {
    HTTPHEADERS=http-headers.txt

    if [ -e ${HTTPHEADERS} ]; then
        rm ${HTTPHEADERS}
    fi
}


# module use /work/imas/etc/modules/all
# module use -p /work/imas/opt/bamboo_deploy/easybuild/modules/all
# TEST
# toolchain=intel-2020b
# module purge
# getIMASModuleName $toolchain 4
# getIMASModuleName $toolchain 5
# getIMASModuleName $toolchain 5 3
# module load "$(getIMASModuleName $toolchain 4)"
# getModuleName netCDF-Fortran $toolchain
# getModuleName netCDF-Fortran foss-2020b
# getModuleName netCDF-Fortran intel-2023b
# getModuleName netCDF-Fortran foss-2023b
# getModuleName GRAYSCALE $toolchain "$(getGCCcoreVersion)"
# getModuleName Fundamental-Constants foss-2023b 13.2.0
# getModuleName XMLlib $toolchain "$(getGCCcoreVersion)"
# getModuleName iWrap $toolchain "$(getGCCcoreVersion)"
# getModuleName Waveform-Cooker $toolchain "$(getGCCcoreVersion)"
# getModuleName INTERPOS $toolchain "$(getGCCcoreVersion)"
# getModuleNameAndVersion Waveform-Cooker/1.4.0-GCCcore-10.2.0
# getModuleNameAndVersion iWrap/0.9.2-GCCcore-10.2.0
# getModuleNameAndVersion netCDF-Fortran/4.5.3-iimpi-2020b
# getModuleNameAndVersion Fundamental-Constants/0.1.1
