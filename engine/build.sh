#!/bin/bash
# usage: build.sh <cc command> <out>
CC="$1"; OUT="$2"; S=/home/claude/dectalk/src
INC=""; for d in "" dapi/src dapi/src/api dapi/src/cmd dapi/src/dic dapi/src/include dapi/src/kernel dapi/src/lts dapi/src/osf dapi/src/ph dapi/src/protos dapi/src/vtm dapi/src/nt; do INC="$INC -I$S/$d"; done
DEFS="-D_REENTRANT -DNOMME -DLTSSIM -DTTSSIM -DANSI -DBLD_DECTALK_DLL -DENGLISH -DENGLISH_US -DACCESS32 -DTYPING_MODE -DOS_SIXTY_FOUR_BIT -DACNA -DDISABLE_AUDIO"
SRCS=$(sed "s#^#$S/#" /home/claude/engine/files.txt)
$CC -O2 -w -fcommon -std=gnu89 $INC $DEFS dtserver.c $SRCS -o $OUT -lpthread -lm -static
