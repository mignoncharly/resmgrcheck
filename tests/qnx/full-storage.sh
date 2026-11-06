#!/bin/sh
# Keep the driver a child of this live shell; exact PID cleanup and wait only.
set -eu
cd "$1"
test ! -e /data/resmgrcheck/phase4-full
mkdir /data/resmgrcheck/phase4-full
image=$1/volume.img
owned=;mounted=0;image_owned=0
cleanup() {
    original=$?
    set +e
    failed=$original
    if test "$mounted" = 1; then
        umount /data/resmgrcheck/phase4-full || failed=1
    fi
    if test -n "$owned"; then
        kill -TERM "$owned"
        wait "$owned" || test "$?" -ge 128 || failed=1
        echo "storage_driver_reaped=$owned"
    fi
    if test "$image_owned" = 1; then rm "$image" || failed=1; fi
    rmdir /data/resmgrcheck/phase4-full || failed=1
    exit "$failed"
}
trap cleanup EXIT
set -C
: > "$image"
image_owned=1
set +C
./mkqnx6fs -q -r 0 -n 2048 "$image"
devb-loopback loopback prefix=rmcfull,fd="$image" blk cache=512k >driver.log 2>&1 &
owned=$!
echo "storage_driver_spawned=$owned"
waitfor /dev/rmcfull0 5
mount -t qnx6 /dev/rmcfull0 /data/resmgrcheck/phase4-full
mounted=1
./fill-storage /data/resmgrcheck/phase4-full
echo STORAGE_READY
read finish
test "$finish" = finish
