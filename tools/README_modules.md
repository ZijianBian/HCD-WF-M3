# H&CD actor modules (EasyBuild)

`tools/build_hcd_modules.sh` and the recipes in `easyconfigs/` build every H&CD actor code of HCD-WF as an
Lmod module, in three flavours, and test each module after installation. A module contains the code's
Fortran library, its MUSCLE3 actor executable, its iWrap actor package (on `PYTHONPATH`) and a run kit
from which `<code>_run_setup` makes a writable run directory. HCD-WF can use a module directly as
`ACTOR_FOLDER=$EBROOT<NAME>` (`$ACTOR_FOLDER/<actor>/<actor>_m3.exe`).

27 codes x 3 flavours = 81 modules:

| flavour | toolchain | compiler | DD (IMAS-Fortran 5.6.0) |
|---|---|---|---|
| `intel-2025b-dd4` | intel/2025b | ifx | 4.1.1 |
| `intel-2025b-dd3` | intel/2025b | ifx | 3.42.2 |
| `intel-2023b-dd3` | intel/2023b | ifort | 3.42.2 |

## Layout

```
tools/
  build_hcd_modules.sh      the method: dry run, build, post-install test, submission, source archives
  build_modules.sbatch      Slurm wrapper (one code/flavour pair per job), calls build_hcd_modules.sh
  README_modules.md         this file
easyconfigs/
  _lib/hcd_ec.py            generator library (flavours, dependencies, git archive, the three writers)
  _lib/run_setup.sh.in      template of the <code>_run_setup helpers
  _lib/test_lib.sh          shell functions sourced by the test_module.sh scripts
  sources.sha256            sha256 of the 27 source archives (paths relative to <work>/sources)
  <CODE>/gen_easyconfigs.py code data: pinned commit + git describe, dependencies, build commands,
                            files of the module and of the run kit, sanity checks, test
  <CODE>/<CODE>-<date>-intel-<tc>-DD-<dd>.eb       generated easyconfigs (committed, usable as is)
  <CODE>/<code>_run_setup.sh                        generated helper (source file of the easyconfigs)
  <CODE>/resolve_deps_module.sh                     run-kit stub of some codes (source file of the easyconfigs)
  <CODE>/test_module.sh                             post-install test (not part of the module)
```

`gen_easyconfigs.py` of a code uses one of the three writers of `hcd_ec.py`:

- `generate(code, here)`: dependencies read from `deps.yaml` of the pinned commit, generic template
  (GRAY, GRAYSCALE, TORAY, GENRAY, RELAX, FPSIM, CYRANO, TOMCAT, LION);
- `write_spec(code, here)`: dependencies listed in the code data, easyconfig assembled line by line
  (PION, TORIC, StixReDist, FoPla, NEMO, NBISIM, FUSREAC, SPECE, HCD2CORE_SOURCES);
- `write_template(...)`: easyconfig template inside the generator (HCD_MERGERS, HCD2CORE_PROFILES,
  LHCD-MODULE, CHEASE, RABBIT, RISK, SPOT, ASCOT); TORBEAM has its own template and keeps its
  `torbeam_run_setup.sh` as a plain file.

The `.eb` files and the helpers are generated: edit the generator (or `_lib`), never the generated
files. The checksum of each helper is written into the easyconfigs, so a changed helper changes the
easyconfigs too.

## Naming and install tree

- Module name: `<CODE>/<date>-intel-<tc>-DD-<dd>`, e.g. `TORBEAM/2026.10.22-intel-2025b-DD-4.1.1`.
  The version is a date label (`VERSION` in `easyconfigs/_lib/hcd_ec.py`, or the code's entry in
  `VERSION_OVERRIDES` there, see "Rebuilding one code from a newer commit"); the commit it is built from
  and its `git describe` are in the module help (`module help`, `description` of the easyconfig) and in
  `local_commit` of the easyconfig. The date label keeps the names apart from the official site modules,
  whose versions are release numbers (e.g. `TORBEAM/3.8.0-intel-2023b-DD-3.42.0`).
- Install tree: `/work/projects/pds/stack` (software in `software/`, modules in `modules/all`,
  easyconfig copies in `ebfiles_repo/`), umask 022: readable by all, writable by the owner only; the
  tree directories carry the setgid bit.
- Dependencies: official site modules only (`/work/imas/etc/modules/all`). There is no `--robot`:
  EasyBuild stops with "Missing modules for dependencies" instead of building one.

## Work directory

Everything a build writes goes to the work directory `HCD_MODULES_WORK` (default
`/scratch/users/$USER/hcd_modules`), never into the repository:
`sources/` (source archives), `eb_build/` and `eb_tmp/` (per job, removed after the build), `logs/`,
`tests/`, `dryrun/` (EasyBuild prefix of the dry runs). `/scratch` is purged after 60 days without access:
`--make-sources` recreates the archives at any time.

Other variables: `HCD_EC_DIR` (easyconfig folder, default `<repository>/easyconfigs`), `EB_PREFIX`
(install tree, default `/work/projects/pds/stack`), `HCD_GIT_ROOT` (folder of the code clones, default the
folder that contains the HCD-WF clone, e.g. `/home/ITER/schneim/public/git`), `HCD_REPO_<NAME>` (clone of
one code; `<NAME>` upper case with non-alphanumerics as `_`, e.g. `HCD_REPO_LHCD_MODULE`). The clones
are read only (`git show`, `git describe`, `git archive`); the subfolders are those of
`hcd.repo(...)` in each generator (for example `nolicense/gray`, `nolicense/lion`).

## Source archives

The archives are not stored in git. `<work>/sources/<letter>/<CODE>/<code>-<date>.tar.gz` is
`git archive --format=tar.gz --prefix=<repo>/` of the pinned commit, made from the local clone:

    bash tools/build_hcd_modules.sh --make-sources all     # or one code

It writes the missing archives (`gen_easyconfigs.py --sources-only`), then checks all of them against
`easyconfigs/sources.sha256` (`sha256sum -c`). Most easyconfigs also have a `git_config` entry, so
EasyBuild can clone the commit from git.iter.org when the archive is missing (it then creates the archive
itself; its bytes may differ, which is why the checksum of these archives is `None` in the easyconfigs).
The LION easyconfigs use the local archive only and record its sha256 (see below).

## Re-generating all modules

1. Update the pinned commits where needed: `commit=` / `describe=` in the `CODE` dict (generic and
   spec generators) or `COMMIT` / `DESCRIBE` (template generators, TORBEAM). `git fetch` the clone first;
   the commit must be on the server. For a changed commit, delete the old archive in
   `<work>/sources/...` and its line in `easyconfigs/sources.sha256`.
2. Run the generators (light, login node):

       cd easyconfigs
       for g in */gen_easyconfigs.py; do python3 "$g" || break; done

   They check the commit and describe against the clone, check that every dependency is a site
   module, write the archives and record the sha256 of new archives in `sources.sha256`.
   Review `git diff easyconfigs/`.
3. Check the archives: `bash tools/build_hcd_modules.sh --make-sources all`.
4. Dry run of all 81 easyconfigs (login node, sequential, a few minutes):

       nice -n 19 bash tools/build_hcd_modules.sh --dry-run all

   Each pair writes `logs/summary_<CODE>_<flavour>_login_dryrun.txt` with `eb dry run: rc=0`.
5. Build and test: `bash tools/build_hcd_modules.sh --submit all` submits 81 jobs (below the 100 active
   jobs limit) to partition `sun` (MUSCLE3/0.10.0-intel-2025b dies with SIGILL on the rigel nodes),
   account `iter`, 1 node, 4 CPUs, 32 GB, 3 h each; RISK and SPOT 6 CPUs / 32 GB, ASCOT 6 CPUs / 48 GB /
   4 h (`CODE_SBATCH` in the script). Add `--rebuild` to replace modules that already exist (otherwise
   EasyBuild skips them and only the test runs again), `--no-test` to skip the tests.

## Rebuilding one code or one flavour

    bash tools/build_hcd_modules.sh --submit RABBIT                       # three flavours
    bash tools/build_hcd_modules.sh --submit --rebuild RABBIT intel-2023b-dd3
    bash tools/build_hcd_modules.sh --list all                            # code / flavour / easyconfig

Inside an interactive allocation on a sun node (`srun -p sun -A iter --cpus-per-task=4 --mem=32G
--time=03:00:00 --pty bash -l`), `bash tools/build_hcd_modules.sh RABBIT intel-2023b-dd3` builds in the
current shell.

## Following the jobs

- `squeue -u $USER`; Slurm log `<work>/logs/hcd_<CODE>_<flavour>_<jobid>.log`.
- `<work>/logs/summary_<CODE>_<flavour>_<jobid>.txt`: easyconfig, module, `eb: rc=...`, test results;
  the last line is `test: rc=<n>` (0 = passed; `test: skipped` without test or with `--no-test`).
- EasyBuild log `<work>/logs/eb_<CODE>_<flavour>_<jobid>.log`; test log
  `<work>/tests/<CODE>_<flavour>_<jobid>/test.log` (the test's run directory and outputs are next to it).

The post-install test loads the new module in a clean environment (`env -i`, `module purge`, site tree
and `/work/projects/pds/stack/modules/all`) and runs `easyconfigs/<CODE>/test_module.sh <workdir>
<summary>` under `timeout 30m`: usually the code's CI case `ci-sdcc/st03-run-actor.sh` (iWrap and MUSCLE3
actor) from a run directory made by `<code>_run_setup`, otherwise the documented user sequence
(`run_<code>.py` / `./run_muscle`) with output checks.

## Using a module

    module use /work/imas/etc/modules/all /work/projects/pds/stack/modules/all
    module load GRAY/2026.10.22-intel-2025b-DD-4.1.1
    gray_run_setup ~/scratch/gray_run && cd ~/scratch/gray_run
    python run_gray.py        # iWrap actor
    ./run_muscle              # MUSCLE3 actor

`<code>_run_setup --help` and `module help <module>` list the commands of each code. Do not source the
`config_sdcc*.sh` files of a repository in a run directory: they purge the modules and select a local
build. The module sets `IMAS_VERSION`, `COMBO` and `<NAME>_RUN_KIT` and raises the stack limit
(`ulimit -Ss unlimited`).

## Code-specific points

- PION: `toolchainopts = {'rpath': False}`: with the RPATH wrappers, `make m3` does not link against the
  MKL bundled with NAG/26 (MKL 11.3.3; `libmkl_def.so`: undefined `mkl_sparse_*` symbols).
- RABBIT: `-xHost` is removed from the Intel release flags of the root `CMakeLists.txt` before the build
  (`sed`, then a check that no ` -xHost ` is left), because the module is shared by all node types
  (rigel has no AVX-512). The module sets `OMP_STACKSIZE=64M` (stack of the OpenMP threads).
- TORBEAM: `-DUSE_XHOST=OFF` for intel-2023b (with ifort it adds `-ipo -xHost`); with ifx it adds no flag.
  Dependencies from `tests/test_imas/deps.yaml`.
- NEMO: the run kit keeps the build tree, so the library is at `obj_<FC>/libnemo.a` there (`lib/libnemo.a`
  in the module).
- TORAY: pinned at 13c359b (origin/feature/DD3_and_DD4).
- GRAY, TORAY, GENRAY: `deps.yaml` names the user-tree Waveform-Cooker 14.4.0.dev1 for DD4; the
  easyconfigs use the official Waveform-Cooker 1.10.0 instead (`cooker_map` in the generator; same
  mirror-steering API, `ec_mirror_add_dynamic`).
- LION: built from origin/feature/DD3_and_DD4 of https://gitlab.epfl.ch/spc/LION (a0273ee). The easyconfigs
  have no git fallback and check the archive's sha256; the archive must be in the source path
  (`--make-sources LION`).
- Actor copies: the build scripts of the repositories call `ci-sdcc/copy_actors.sh`, which copies the iWrap
  actors into `~/public/PYTHON_ACTORS/<COMBO>`; every easyconfig sets `ACTORS_COPY_DIR=none` in its build
  environment, so an install copies nothing there. The run kits contain `ci-sdcc/copy_actors.sh` (tracked
  file): a build script run from a run kit copies the actors as in the repository.
- ascot4rfof is not packaged (ASCOT module: ascot, afsi, bbnbi).
- MUSCLE3 tests: the clean test environment gets all `SLURM_*` variables of the job (and
  `SLURM_EXPORT_ENV=ALL`); without `SLURM_(JOB_)NODELIST` the MUSCLE3 instances do not start and the
  manager hangs (hence also the 30 min timeout).

## Bumping the date label

1. Set `VERSION` in `easyconfigs/_lib/hcd_ec.py` (the only place; the template generators, TORBEAM and
   `build_hcd_modules.sh` read it).
2. Run the generators: they write the `.eb` files under the new names and the new archives, and record
   their sha256 in `sources.sha256`. Remove the easyconfigs of the old label (`git rm
   easyconfigs/*/*-<old>-intel-*.eb`) and the old lines of `sources.sha256`, unless both labels are kept.
3. Dry run, `--submit all`. The new modules install next to the old ones (other version), so users switch
   by module name.

## Rebuilding one code from a newer commit

A module name stands for one build: a code rebuilt from a newer commit gets its own date label, the
other codes keep theirs.

1. Add the code to `VERSION_OVERRIDES` in `easyconfigs/_lib/hcd_ec.py` (`'<CODE>': '<date>'`, `<CODE>`
   as in `CODE_ORDER` of `build_hcd_modules.sh`). The writers, the template generators (`VERSION =
   hcd.version_of('<CODE>')`) and `build_hcd_modules.sh` read the label through it; codes not listed use
   `VERSION`.
2. Set the new `commit` / `describe` (or `COMMIT` / `DESCRIBE`) in the code's generator, run it: it
   writes the three `.eb` files under the new label, the archive `<code>-<date>.tar.gz` and its line in
   `sources.sha256`. The `.eb` files and the archive line of the old label stay (the old modules stay
   installed until removed by hand).
3. Run the other generators too and check that `git status easyconfigs/` shows no other generated file
   changed.
4. `--make-sources <CODE>`, `--dry-run <CODE> all`, `--submit <CODE> all`.

Current overrides: FoPla `2026.10.26`, HCD2CORE_SOURCES `2026.10.27`.

## Replacing an older set of modules

Once the new set is built (`--submit all` finished), `tools/cleanup_old_modules.sh` removes the old set
from the install tree, pair by pair. Run it only after the jobs of the new set are done: a pair whose
replacement is not yet validated is kept. Preview first (the default, nothing deleted), then delete:

    bash tools/cleanup_old_modules.sh                    # dry run: prints "would remove" / KEEP per module
    bash tools/cleanup_old_modules.sh --yes              # deletes (--dry-run, if also given, wins)

Options (defaults): `--old-version` (`2026.10.21`), `--old-suffix` (`-pds`, may be empty),
`--new-version` (`VERSION` of `easyconfigs/_lib/hcd_ec.py`), `--prefix` (`EB_PREFIX`, else
`/work/projects/pds/stack`), `--work` (`HCD_MODULES_WORK`, else `/scratch/users/$USER/hcd_modules`).

For each old module `<CODE>/<old-version>-intel-<tc>-DD-<dd><old-suffix>` it deletes the old install
directory and `.lua` only when all of these hold: the new `<CODE>/<new-version>-intel-<tc>-DD-<dd>.lua`
and the new install directory exist, and the newest non-dry-run `logs/summary_<CODE>_<flavour>_*.txt`
of the work directory has `eb: rc=0` and `test: rc=0`. Before each `rm`, the path must match the exact
old name pattern under `<prefix>/software` or `<prefix>/modules/all` and be a real directory / regular
file (no symlink); otherwise it is refused. Code folders left empty are removed with `rmdir`. It never
touches `<prefix>/ebfiles_repo`, the new modules, other versions, or modules with an unexpected name, and
it ends with the counts of removed and kept modules (with the reasons for keeping).

Today's use: the old `2026.10.21-...-pds` set is replaced by `2026.10.22` (the defaults).
