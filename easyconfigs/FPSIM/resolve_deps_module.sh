# ci-sdcc/resolve_deps.sh of the run kit of an H&CD actor module (sourced by ci-sdcc/st00-header.sh):
# the environment is the one of the loaded module, which sets COMBO and IMAS_VERSION and loads the
# dependency modules of its combination; nothing is resolved or loaded here and no module is purged.
if [[ -z "${COMBO:-}" || -z "${IMAS_VERSION:-}" ]]; then
    echo "resolve_deps (module run kit): COMBO or IMAS_VERSION not set: load the code's module first" >&2
    return 1 2>/dev/null || exit 1
fi
echo "resolve_deps (module run kit): environment of the loaded module, COMBO=$COMBO IMAS_VERSION=$IMAS_VERSION"
return 0 2>/dev/null || exit 0
