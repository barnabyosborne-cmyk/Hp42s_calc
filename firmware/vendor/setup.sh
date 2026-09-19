#!/bin/sh
# Lays out Intel's decimal floating-point library as an ESP-IDF component.
#
# Plus42 does its arithmetic in decimal, not binary, the way a real HP-42S
# does, and that comes from Intel's BID library. It is BSD licensed and about
# 16 MB extracted, so the tarball is what lives in git; run this once after
# cloning and the build finds everything it needs.
#
#   cd firmware && ./vendor/setup.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
dest="$here/../components/libbid"

if [ -d "$dest/src" ]; then
  echo "Already set up. Delete $dest/src and $dest/float128 to redo it."
  exit 0
fi

tmp=$(mktemp -d)
echo "Extracting Intel's library..."
tar xzf "$here/IntelRDFPMathLib20U1.tar.gz" -C "$tmp"

echo "Patching..."
# Thomas Okken's patch. The only part that matters to us is <sys/signal.h>
# becoming <signal.h>; the rest touches Intel's own test programs.
( cd "$tmp/IntelRDFPMathLib20U1" && patch -p0 --forward < "$here/intel-lib-linux.patch" ) || true

cp -r "$tmp/IntelRDFPMathLib20U1/LIBRARY/src" "$dest/"
cp -r "$tmp/IntelRDFPMathLib20U1/LIBRARY/float128" "$dest/"
rm -rf "$tmp"

echo "Done. Now: idf.py set-target esp32s3 && idf.py build"
