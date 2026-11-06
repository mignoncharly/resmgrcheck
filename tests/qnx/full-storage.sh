#!/bin/sh
# Keep the driver a child of this live shell; exact PID cleanup and wait only.
set -eu
cd "$1"
test ! -e /data/resmgrcheck/phase4-full
mkdir /data/resmgrcheck/phase4-full
touch volume.img
./mkqnx6fs -q -r 0 -n 2048 volume.img
devb-loopback loopback prefix=rmcfull,fd="$1/volume.img" blk cache=512k >driver.log 2>&1 &
owned=$!
echo "storage_driver_spawned=$owned"
mounted=0
cleanup() {
    if test "$mounted" = 1; then
        umount /data/resmgrcheck/phase4-full
    fi
    kill -TERM "$owned"
    wait "$owned" || test "$?" -ge 128
    rmdir /data/resmgrcheck/phase4-full
    echo "storage_driver_reaped=$owned"
}
trap cleanup EXIT
waitfor /dev/rmcfull0 5
mount -t qnx6 /dev/rmcfull0 /data/resmgrcheck/phase4-full
mounted=1
./fill-storage /data/resmgrcheck/phase4-full
echo STORAGE_READY
read finish
test "$finish" = finish
