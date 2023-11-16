#!/bin/bash

# 3-fingered-claw 
function yell () 
{ 
  echo "$0: $*" >&2
}

function die () 
{ 
  yell "$*"; # exit 1
}

function try () 
{ 
  "$@" || die "cannot $*" 
}
