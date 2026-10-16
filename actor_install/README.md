# actor_install

Fetches an actor's source, builds it, and wraps it with iWrap, all from one small YAML file.
Each actor used by the HCD workflow has its own YAML in this folder.

```bash
export ACTOR_FOLDER=$HOME/my_actors          # where the actors get installed
python actor_install.py grayscale.yml         # one actor
python actor_install.py grayscale.yml toray.yml gray.yml   # several
```

Then put `$ACTOR_FOLDER` on your `PYTHONPATH` and the workflow will find them.

## The YAML file

```yaml
SOURCES:
  - VCS: git                      # git or svn
    REPO: ssh://git@git.iter.org/heat/grayscale.git
    VERSION: develop              # branch, tag or commit hash
    DIR: grayscale

MODULES: [IMAS-Python, iWrap, XMLlib, lxml, IMAS-Fortran]

BUILDS:
  - DIR: grayscale
    CMD: make clean library FC="$FC" DEBUG=yes

ACTORS:
  - DIR: grayscale
    CMD: make clean iwrap_actor FC="$FC" DEBUG=yes

ACTOR_NAMES: [grayscale]          # optional, see below
```

`CMD` can also be a list of commands, which run one after the other.

`ACTOR_NAMES` lists the packages the actor installs. After installing, the script checks
that `$ACTOR_FOLDER/<name>/actor.py` exists for each one. You only need `ACTOR_NAMES` when the names
differ from the file name: by default `hcd2core-sources.yml` means `hcd2core_sources`.

Always write `FC="$FC"`, never a hard-coded compiler. The script picks the compiler for you (see below).

## Changing things without editing the YAML

The YAML files hold sensible defaults. In CI, or when you're testing a branch, you can override them
with environment variables:

| Variable | What it does |
|---|---|
| `MODULES` | Space-separated list of modules, loaded **instead of** the YAML `MODULES` section of every file |
| `ACTOR_VERSIONS` | Space-separated `DIR=VERSION` pairs that replace the YAML `VERSION`, e.g. `grayscale=develop torbeam=89b416c9` |
| `FC` | Fortran compiler. If unset, the first of `ifort`, `ifx`, `gfortran` found in the loaded modules is used |
| `ACTOR_FOLDER` | Install destination, also used for the `actor.py` check |

`-V DIR=VERSION` on the command line does the same as `ACTOR_VERSIONS`, and wins if both are given.
If an override doesn't match any `DIR` (a typo, usually), the run fails rather than quietly building
the default version.

In Bamboo, define `MODULES` and `ACTOR_VERSIONS` as plan variables and pass them through:

```bash
MODULES="$bamboo_MODULES" ACTOR_VERSIONS="$bamboo_ACTOR_VERSIONS" \
    python actor_install/actor_install.py -p grayscale.yml hcd_mergers.yml
```

## Options

| Option | Use it to |
|---|---|
| `-V DIR=VERSION` | Build another branch, tag or commit (repeatable) |
| `-D DIR` | Choose the work directory for sources (default: `build_<date>`) |
| `-R` | Check that the checkout really is the requested branch, tag or commit |
| `-M MODULE` | Load one extra module first (also works with `--skipModules`) |
| `--skipModules` | Keep the modules you already have loaded |
| `--skipSources` / `--skipBuilds` / `--skipActors` | Skip that step, e.g. to rebuild without cloning again |
| `-p` | Stop at the first failure |
| `-v` | Print more detail |

## What you get

- The actors in `$ACTOR_FOLDER`, one folder per actor.
- A `RELEASE.yaml` recording who built what, when, and with which modules.
- Exit code `0` only if every YAML succeeded, `1` otherwise. So CI notices when something breaks.

## When it goes wrong

- **Module fails to load:** check the name with `module avail <name>`. Two modules that pull in
  conflicting IMAS stacks can't be loaded together.
- **Clone fails:** check your SSH key for `git.iter.org`.
- **"Actor ... not found" after a successful build:** the actor's Makefile probably ignores
  `ACTOR_FOLDER` and installed somewhere else, or the package name differs, so add `ACTOR_NAMES`.
- **Rebuild quickly after a change:** `python actor_install.py --skipModules --skipSources -D <old work dir> grayscale.yml`
