#!/usr/bin/env python
import os
import sys
import shutil
import argparse
import subprocess
from getpass import getuser
from datetime import datetime
from io import open

import yaml
import sh


# adapted from $MODULESHOME/init/python.py
def module(*args):
    if type(args[0]) == type([]):
        args = args[0]
    else:
        args = list(args)
        (output, error) = subprocess.Popen(
            ["/usr/bin/modulecmd", "python"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).communicate()
        exec(output)
        return str(error.decode("utf-8"))


def setup_env(desc, args):
    print("***** SETUP ENVIRONMENT *****")
    if args.verbose:
        print(desc)
    err = module("purge")
    if err != "":
        print(err)
        return 1

    if args.preModule != None:
        err = module("load", args.preModule)
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

    if args.setKEPLER != "":
        os.environ["KEPLER"] = args.setKEPLER
        print("Using " + args.setKEPLER + " as destination for actors!")

    return 0


def get_sources(desc, args):
    print("***** GET SOURCES *****")
    if args.verbose:
        print(desc)

    for s in desc:
        if s.get("DIR") == "":
            print("Please specify destination DIR for the sources!")
            return 1

        if os.path.isdir(s.get("DIR")):
            sh.rm("-rf", "." + s.get("DIR") + "_BACKUP")
            sh.mv(s.get("DIR"), "." + s.get("DIR") + "_BACKUP")

        if s.get("VCS").lower() == "svn":
            logs = sh.svn.checkout(s.get("REPO"), s.get("DIR"))
            print(logs)
            wcrev = sh.svnversion(s.get("DIR"))
            if args.checkRevision:
                if wcrev != s.get("VERSION"):
                    print("Wrong revision of checked-out SVN repo")
                    print(
                        "Got "
                        + str(wcrev)
                        + " and was expecting "
                        + str(s.get("VERSION"))
                    )
                    return 1
            else:
                print("Checked-out " + s.get("REPO") + " in revision " + str(wcrev))

        elif s.get("VCS").lower() == "git":
            logs = sh.git.clone(
                "--single-branch", "-b", s.get("VERSION"), s.get("REPO"), s.get("DIR")
            )
            print(logs)
            prevdir = os.getcwd()
            os.chdir(s.get("DIR"))
            hhash = sh.git("rev-parse", "--verify", "HEAD")
            if args.checkRevision:
                if hhash != s.get("VERSION"):
                    print("Wrong hash of cloned GIT repo")
                    print(
                        "Got "
                        + str(hhash)
                        + " and was expecting "
                        + str(s.get("VERSION"))
                    )
                    return 1
            else:
                print("Cloned " + s.get("REPO") + " with HEAD at " + str(hhash))
            os.chdir(prevdir)

        else:
            print("Unsupported Version Control System (VCS)")
            return 1

    return 0


def build_libs(desc, verb):
    print("***** BUILD LIBRARIES *****")
    if args.verbose:
        print(desc)
        cmd = os.popen("/usr/bin/modulecmd python list")
        exec(cmd)

    prevdir = os.getcwd()
    for b in desc:
        try:
            os.chdir(b.get("DIR"))
        except:
            print("Can't get in directory " + b.get("DIR"))
            return 1

        status = subprocess.call(b.get("CMD").split(" "))
        os.chdir(prevdir)
        if status:
            return 1

    return 0


def install_actors(desc, args):
    print("***** INSTALL ACTORS *****")
    if args.verbose:
        print(desc)

    prevdir = os.getcwd()
    for b in desc:
        try:
            os.chdir(b.get("DIR"))
        except:
            print("Can't get in directory " + b.get("DIR"))
            return 1

        xml = b.get("XML")
        # print xml

        if isinstance(xml, list):
            for x in xml:
                subprocess.call(
                    [
                        "fc2k "
                        + x
                        + " -nokepler -pyworkspace "
                        + os.getenv("ACTOR_FOLDER")
                    ],
                    shell=True,
                )
        else:
            subprocess.call(
                [
                    "fc2k "
                    + xml
                    + " -nokepler -pyworkspace "
                    + os.getenv("ACTOR_FOLDER")
                ],
                shell=True,
            )

        os.chdir(prevdir)

    return 0


# main
argp = argparse.ArgumentParser(
    prog="actor_install.py",
    description="This program installs IMAS actors in Kepler given a release description from the code developers",
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
    help="Specifies module to be loaded if for instance imasenv is not available by default",
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
    "--skipModules",
    action="store_true",
    help="Skip the environment modules setup steps",
)
argp.add_argument(
    "--skipSources", action="store_true", help="Skip the source checkout steps"
)
argp.add_argument("--skipBuilds", action="store_true", help="Skip the building steps")
argp.add_argument(
    "--skipActors", action="store_true", help="Skip the actor install steps"
)
argp.add_argument(
    "--setKEPLER",
    default="",
    help="Sets non-standard KEPLER variable (to be used with care!)",
)
argp.add_argument(
    "-v", "--verbose", action="store_true", help="Run the script in verbose mode"
)
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


stream = open("RELEASE.yaml", "w")
release = {}
if args.skipModules:
    release["Default Modules"] = []
    for m in module("-t", "list").split(":")[1].split():
        release["Default Modules"].append(m)

release["Projects"] = []

for yml in args.yml:
    fname = yml.name
    if fname == "TEMPLATE.yml":
        continue

    try:
        desc = yaml.load(yml, Loader=yaml.CLoader)

        if args.verbose:
            print(desc)

        project = {
            "DEPLOYER": getuser(),
            "DATE": datetime.now(),
        }  # .strftime('%Y-%m-%d_%Hh%Mm%Ss')}

        #'SOURCES': desc.get('SOURCES'),
        #'MODULES': desc.get('MODULES'),
        #'BUILDS': desc.get('BUILDS'),
        #'ACTORS': desc.get('ACTORS')
        # release['Projects'] += [{fname: project}]

        print("============" + len(fname) * "=" + "=======")
        print(" ===== from " + fname + " =====")
        print("============" + len(fname) * "=" + "=======")

        if args.skipModules:
            print("Bypassing environment modules setup")
        else:
            project["MODULES"] = desc.get("MODULES")
            if setup_env(desc.get("MODULES"), args):
                print("Error during MODULE steps for " + fname)
                if args.pedantic:
                    sys.exit()
                else:
                    continue

        if args.verbose:
            print("Check modules list:")
            print(module("list"))

        try:
            os.mkdir(args.workDir)
            print("Workdir=" + args.workDir + " created successfully")
        except:
            print("Workdir=" + args.workDir + " exists already")
        prevdir = os.getcwd()
        os.chdir(args.workDir)

        if args.skipSources:
            print("Bypassing sources checkout")
        else:
            project["SOURCES"] = desc.get("SOURCES")
            if get_sources(desc.get("SOURCES"), args):
                print("Error during SOURCE steps for " + fname)
                if args.pedantic:
                    sys.exit()
                else:
                    continue

        if args.skipBuilds:
            print("Bypassing libraries build")
        else:
            project["BUILDS"] = desc.get("BUILDS")
            if build_libs(desc.get("BUILDS"), args):
                print("Error during BUILD steps for " + fname)
                if args.pedantic:
                    sys.exit()
                else:
                    continue

        if args.skipActors:
            print("Bypassing actors install")
        else:
            project["ACTORS"] = desc.get("ACTORS")
            if install_actors(desc.get("ACTORS"), args):
                print("Error during ACTOR steps for " + fname)
                if args.pedantic:
                    sys.exit()
                else:
                    continue

        os.chdir(prevdir)

        release["Projects"] += [{fname: project}]

    except yaml.YAMLError as exc:
        print(exc)


yaml.dump(release, stream)
