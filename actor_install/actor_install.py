#!/usr/bin/env python
import os
import sys
import shutil
import argparse
import subprocess
from getpass import getuser
from datetime import datetime
from io import open

from yaml import load as yamlload, dump as yamldump

try:
    from yaml import CLoader as yamlLoader
except ImportError:
    from yaml import Loader as yamlLoader


# adapted from $MODULESHOME/init/python.py
def module(*args):
    """Universal module function that works with both Environment Modules and Lmod"""
    if isinstance(args[0], list):
        args = args[0]
    else:
        args = list(args)

    # Detect module command location and type
    modulecmd = None

    # Option 1: Check MODULESHOME environment variable (Environment Modules)
    if os.environ.get("MODULESHOME"):
        modulecmd_path = os.path.join(os.environ["MODULESHOME"], "bin", "modulecmd")
        if os.path.exists(modulecmd_path):
            modulecmd = [modulecmd_path, "python"]

    # Option 2: Check for Lmod
    if not modulecmd and os.environ.get("LMOD_CMD"):
        modulecmd = [os.environ["LMOD_CMD"], "python"]

    # Option 3: Try common locations for modulecmd
    if not modulecmd:
        for path in [
            "/usr/bin/modulecmd",
            "/usr/share/Modules/bin/modulecmd",
            "/opt/modules/bin/modulecmd",
            "/sw/modules/bin/modulecmd",
        ]:
            if os.path.exists(path):
                modulecmd = [path, "python"]
                break

    # Option 4: Try to find modulecmd in PATH
    if not modulecmd:
        try:
            modulecmd_path = subprocess.check_output(["which", "modulecmd"], stderr=subprocess.DEVNULL).decode().strip()
            if modulecmd_path:
                modulecmd = [modulecmd_path, "python"]
        except subprocess.CalledProcessError:
            pass

    # Fallback: Try using module as a shell function (works with Lmod)
    if not modulecmd:
        try:
            # Try calling module directly as it might be a shell function
            cmd = [
                "bash",
                "-c",
                f'source /etc/profile.d/modules.sh 2>/dev/null || true; module python {" ".join(args)}',
            ]
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                output, error = proc.communicate()
            exec(output)  # pylint: disable=exec-used
            return str(error.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(
                f"Could not find module command. "
                f"Please ensure Environment Modules or Lmod is properly configured.\nError: {e}"
            ) from e

    # Execute the module command
    try:
        with subprocess.Popen(
            modulecmd + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            output, error = proc.communicate()
        exec(output)  # pylint: disable=exec-used
        return str(error.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Error executing module command: {e}") from e


def setup_env(desc, args):
    print("***** SETUP ENVIRONMENT *****")
    if args.verbose:
        print(desc)
    err = module("purge")
    if err != "":
        if "ERROR" in err:
            print("Error during module purge:")
            print(err)
            return 1
        if args.verbose:
            print(err)

    if args.preModule is not None:
        err = module("load", args.preModule)
        print(f"loaded {args.preModule}")
        if err != "":
            print(err)
            return 1

    for m in desc:
        print("loading module " + m)
        err = module("load", m)
        if err != "":
            if "conflicts with the currently loaded module" in err:
                # failed, try switching instead?
                print("switching module " + m)
                err = module("switch", m)
                if err != "":
                    print(err)
                    return 1
            elif "ERROR" in err:
                print("Error while loading module " + m)
                print(err)
                return 1
            else:
                if args.verbose:
                    print(err)

    err = module("list")
    print(err)

    return 0


def get_sources(desc, args):
    print("***** GET SOURCES *****")
    if args.verbose:
        print(desc)

    for s in desc:
        if s.get("DIR") == "":
            print("Please specify destination DIR for the sources!")
            return 1

        source_dir = s.get("DIR")
        backup_dir = "." + source_dir + "_BACKUP"

        if os.path.isdir(source_dir):
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.move(source_dir, backup_dir)

        if s.get("VCS").lower() == "svn":
            try:
                result = subprocess.run(
                    ["svn", "checkout", s.get("REPO"), s.get("DIR")], capture_output=True, text=True, check=True
                )
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"SVN checkout error: {e}")
                print(e.stderr)
                return 1

            try:
                result = subprocess.run(["svnversion", s.get("DIR")], capture_output=True, text=True, check=True)
                wcrev = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                print(f"SVN version error: {e}")
                return 1

            if args.checkRevision:
                if wcrev != s.get("VERSION"):
                    print("Wrong revision of checked-out SVN repo")
                    print("Got " + str(wcrev) + " and was expecting " + str(s.get("VERSION")))
                    return 1
            else:
                print("Checked-out " + s.get("REPO") + " in revision " + str(wcrev))

        elif s.get("VCS").lower() == "git":
            version = str(s.get("VERSION"))
            if is_commit_hash(version):
                clone_cmds = [
                    ["git", "clone", s.get("REPO"), s.get("DIR")],
                    ["git", "-C", s.get("DIR"), "checkout", "--detach", version],
                ]
            else:
                clone_cmds = [["git", "clone", "--single-branch", "-b", version, s.get("REPO"), s.get("DIR")]]
            try:
                for cmd in clone_cmds:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"Git clone error: {e}")
                print(e.stderr)
                return 1

            prevdir = os.getcwd()
            os.chdir(s.get("DIR"))

            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD"], capture_output=True, text=True, check=True
                )
                hhash = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                print(f"Git rev-parse error: {e}")
                os.chdir(prevdir)
                return 1

            if not args.checkRevision:
                print(f"Cloned {s.get('REPO')} with HEAD at {hhash}")
                os.chdir(prevdir)
                continue

            if is_commit_hash(version):
                # Compare commit hashes (VERSION may be abbreviated)
                if not hhash.startswith(version.lower()):
                    print("Wrong commit hash of cloned GIT repo")
                    print(f"Got {hhash} and was expecting {version}")
                    return 1
                print(f"Verified commit hash: {hhash}")
                os.chdir(prevdir)
                continue

            # VERSION is a branch or tag name - verify we're on it
            try:
                # Get current branch name
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True
                )
                current_branch = result.stdout.strip()

                if current_branch == version:
                    print(f"Verified on branch: {version} (commit: {hhash})")
                    os.chdir(prevdir)
                    continue

                # Maybe it's a tag - check if tag exists and points to HEAD
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", version], capture_output=True, text=True, check=True
                    )
                    tag_hash = result.stdout.strip()

                    if tag_hash == hhash:
                        print(f"Verified tag: {version} (commit: {hhash})")
                    else:
                        print(
                            f"Warning: Expected {version}, "
                            f"got branch {current_branch} (commit: {hhash})"
                        )
                except subprocess.CalledProcessError:
                    print(
                        f"Warning: Not on expected branch/tag {version}, "
                        f"on {current_branch} (commit: {hhash})"
                    )
            except subprocess.CalledProcessError as e:
                print(f"Could not verify branch/tag: {e}")
                print(f"Cloned with HEAD at {hhash}")

            os.chdir(prevdir)

        else:
            print("Unsupported Version Control System (VCS)")
            return 1

    return 0


def build_libs(desc, args):
    print("***** BUILD LIBRARIES *****")
    if args.verbose:
        print(desc)

    prevdir = os.getcwd()
    for b in desc:
        try:
            os.chdir(b.get("DIR"))
        except OSError:
            print("Can't get in directory " + b.get("DIR"))
            return 1

        cmd = b.get("CMD")

        if isinstance(cmd, list):
            for c in cmd:
                print(f"Executing: {c}")
                status = subprocess.call(c, shell=True)
                if status:
                    print(f"Error executing command: {c}")
                    os.chdir(prevdir)
                    return 1
        else:
            print(f"Executing: {cmd}")
            status = subprocess.call(cmd, shell=True)
            if status:
                print(f"Error executing command: {cmd}")
                os.chdir(prevdir)
                return 1

        os.chdir(prevdir)

    return 0


def install_actors(desc, args):
    print("***** INSTALL ACTORS *****")
    if args.verbose:
        print(desc)

    prevdir = os.getcwd()
    for b in desc:
        try:
            os.chdir(b.get("DIR"))
        except OSError:
            print("Can't get in directory " + b.get("DIR"))
            return 1

        cmd = b.get("CMD")

        if isinstance(cmd, list):
            for c in cmd:
                print(f"Executing: {c}")
                status = subprocess.call(c, shell=True)
                if status:
                    print(f"Error executing command: {c}")
                    os.chdir(prevdir)
                    return 1
        else:
            print(f"Executing: {cmd}")
            status = subprocess.call(cmd, shell=True)
            if status:
                print(f"Error executing command: {cmd}")
                os.chdir(prevdir)
                return 1

        os.chdir(prevdir)

    return 0


def is_commit_hash(version):
    """True if VERSION looks like a (possibly abbreviated) git commit hash rather than a branch or tag"""
    return 7 <= len(version) <= 40 and all(c in "0123456789abcdef" for c in version.lower())


def parse_version_overrides(specs):
    """Parse ["DIR=VERSION", ...] into a dict, keyed by the SOURCES DIR"""
    overrides = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Invalid version override '{spec}', expected DIR=VERSION")
        src_dir, version = spec.split("=", 1)
        overrides[src_dir.strip()] = version.strip()
    return overrides


def apply_version_overrides(sources, overrides, used):
    for s in sources:
        if s.get("DIR") in overrides:
            print(f"Overriding VERSION of {s.get('DIR')}: {s.get('VERSION')} -> {overrides[s.get('DIR')]}")
            s["VERSION"] = overrides[s.get("DIR")]
            used.add(s.get("DIR"))


def setup_fc(user_fc):
    """Select the Fortran compiler from the loaded modules unless FC was given by the caller"""
    if user_fc:
        fc = user_fc
    else:
        fc = next((c for c in ("ifort", "ifx", "gfortran") if shutil.which(c)), None)
        if fc is None:
            print("No supported Fortran compiler (ifort/ifx/gfortran) found in loaded modules. Set FC explicitly.")
            return 1
    os.environ["FC"] = fc
    print(f"Using FC={fc}")
    return 0


def check_actors(names):
    """Verify that each actor package was installed in ACTOR_FOLDER"""
    actor_folder = os.environ.get("ACTOR_FOLDER")
    if not actor_folder:
        print("Warning: ACTOR_FOLDER is not set, skipping installed actor check")
        return 0
    missing = [n for n in names if not os.path.isfile(os.path.join(actor_folder, n, "actor.py"))]
    for n in missing:
        print(f"Actor {n} not found: {os.path.join(actor_folder, n, 'actor.py')} does not exist")
    return 1 if missing else 0


# main
argp = argparse.ArgumentParser(
    prog="actor_install.py",
    description="This program installs IMAS actors in Python given a release description from the code developers",
)
argp.add_argument(
    "yml",
    type=argparse.FileType("r"),
    nargs="+",
    help="Yaml description of the project / actors",
)
argp.add_argument(
    "-M",
    "--preModule",
    help="Specifies module to be loaded if for instance IMAS environment is not available by default",
)
argp.add_argument(
    "-D",
    "--workDir",
    default="build_" + datetime.now().strftime("%Y-%m-%d_%Hh%Mm%Ss"),
    metavar=("DIR"),
    help="Specifies working directory in which sources will be saved (default: %(default)s)",
)
argp.add_argument(
    "-R",
    "--checkRevision",
    action="store_true",
    help="Check if checked-out sources correspond to expected revision",
)
argp.add_argument(
    "-V",
    "--version",
    action="append",
    default=[],
    metavar="DIR=VERSION",
    help="Override VERSION (branch, tag or commit) of the source checked out in DIR; can be repeated. "
    "Also read from the space-separated ACTOR_VERSIONS environment variable (command line wins)",
)
argp.add_argument(
    "--skipModules",
    action="store_true",
    help="Skip the environment modules setup steps",
)
argp.add_argument("--skipSources", action="store_true", help="Skip the source checkout steps")
argp.add_argument("--skipBuilds", action="store_true", help="Skip the building steps")
argp.add_argument("--skipActors", action="store_true", help="Skip the actor install steps")
argp.add_argument("-v", "--verbose", action="store_true", help="Run the script in verbose mode")
argp.add_argument(
    "-p",
    "--pedantic",
    action="store_true",
    help="Stop the whole script at first detected error",
)
args = argp.parse_args()

# with open(args.yml, 'r') as stream:
# desc = yaml.load(stream)
if args.verbose:
    print(args.yml)

release = {}
if args.skipModules:
    release["Default Modules"] = []
    try:
        module_output = module("-t", "list")
        # Parse module list output (format varies between Environment Modules and Lmod)
        if ":" in module_output:
            # Environment Modules format: "Currently Loaded Modulefiles:\nmodule1\nmodule2"
            # or "Currently Loaded Modulefiles:module1:module2"
            parts = module_output.split(":")
            if len(parts) > 1:
                for m in parts[1].split():
                    if m.strip():
                        release["Default Modules"].append(m.strip())
        else:
            # Lmod or other format: just split by whitespace/newlines
            for line in module_output.split("\n"):
                line = line.strip()
                if line and not line.startswith("Currently") and not line.startswith("No "):
                    release["Default Modules"].append(line)
    except Exception as e:
        print(f"Warning: Could not parse module list: {e}")
        release["Default Modules"] = []

release["Projects"] = []
failures = []
user_fc = os.environ.get("FC")
# MODULES and ACTOR_VERSIONS from the environment (e.g. Bamboo plan variables) replace the YAML values
env_modules = os.environ.get("MODULES", "").split()
version_overrides = parse_version_overrides(os.environ.get("ACTOR_VERSIONS", "").split() + args.version)
used_overrides = set()


def fail(fname, step):
    print(f"Error during {step} steps for {fname}")
    return 1


def process_yml(desc, fname, project):
    """Run all steps for one YAML description, return non-zero on the first failing step"""
    if args.skipModules:
        print("Bypassing environment modules setup")
        # But still load preModule if specified
        if args.preModule is not None:
            print(f"Loading pre-module: {args.preModule}")
            err = module("load", args.preModule)
            if err != "":
                print(err)
                if "ERROR" in err:
                    return fail(fname, "MODULE")
            print(f"Loaded {args.preModule}")
    else:
        modules = env_modules or desc.get("MODULES")
        if env_modules:
            print("Using modules from MODULES environment variable instead of " + fname)
        project["MODULES"] = modules
        if setup_env(modules, args):
            return fail(fname, "MODULE")

    if args.verbose:
        print("Check modules list:")
        print(module("list"))

    if setup_fc(user_fc):
        return fail(fname, "COMPILER")

    try:
        os.mkdir(args.workDir)
        print("Workdir=" + args.workDir + " created successfully")
    except OSError:
        print("Workdir=" + args.workDir + " exists already")
    prevdir = os.getcwd()
    os.chdir(args.workDir)
    try:
        if args.skipSources:
            print("Bypassing sources checkout")
        else:
            if desc.get("SOURCES") is not None:
                apply_version_overrides(desc.get("SOURCES"), version_overrides, used_overrides)
            project["SOURCES"] = desc.get("SOURCES")
            if desc.get("SOURCES") is None:
                print(f"Warning: No SOURCES section in {fname}, skipping source checkout")
            elif get_sources(desc.get("SOURCES"), args):
                return fail(fname, "SOURCE")

        if args.skipBuilds:
            print("Bypassing libraries build")
        else:
            project["BUILDS"] = desc.get("BUILDS")
            if desc.get("BUILDS") is None:
                print(f"Warning: No BUILDS section in {fname}, skipping build")
            elif build_libs(desc.get("BUILDS"), args):
                return fail(fname, "BUILD")

        if args.skipActors:
            print("Bypassing actors install")
        else:
            project["ACTORS"] = desc.get("ACTORS")
            if desc.get("ACTORS") is None:
                print(f"Warning: No ACTORS section in {fname}, skipping actor install")
            elif install_actors(desc.get("ACTORS"), args):
                return fail(fname, "ACTOR")
            # Actor package names default to the YAML file name (hcd2core-sources.yml -> hcd2core_sources)
            default_name = os.path.splitext(os.path.basename(fname))[0].replace("-", "_")
            if check_actors(desc.get("ACTOR_NAMES", [default_name])):
                return fail(fname, "ACTOR CHECK")
    finally:
        os.chdir(prevdir)

    return 0


for yml in args.yml:
    fname = yml.name
    if fname == "TEMPLATE.yml":
        continue

    print("============" + len(fname) * "=" + "=======")
    print(" ===== from " + fname + " =====")
    print("============" + len(fname) * "=" + "=======")

    project = {
        "DEPLOYER": getuser(),
        "DATE": datetime.now(),
    }
    try:
        desc = yamlload(yml, Loader=yamlLoader)
        if args.verbose:
            print(desc)
        status = process_yml(desc, fname, project)
    except Exception as exc:
        print(f"Error processing {fname}: {exc}")
        status = 1

    if status:
        failures.append(fname)
        if args.pedantic:
            break
    else:
        release["Projects"] += [{fname: project}]

# Write release information to file
with open("RELEASE.yaml", "w", encoding="utf-8") as stream:
    yamldump(release, stream)

unused_overrides = set(version_overrides) - used_overrides
if unused_overrides and not args.skipSources and not (args.pedantic and failures):
    print("Version overrides matching no SOURCES DIR: " + ", ".join(sorted(unused_overrides)))
    failures.append("ACTOR_VERSIONS")

if failures:
    print("Failed: " + ", ".join(failures))
    sys.exit(1)
