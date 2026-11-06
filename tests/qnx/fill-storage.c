/* Lab qualification only: exhaust at most 16 MiB on the isolated mounted image. */
#include <sys/statvfs.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    if (argc==2 && !strcmp(argv[1],"--preflight")) {
        struct statvfs v;
        if (statvfs("/data",&v)) return 2;
        unsigned long long available=(unsigned long long)v.f_bavail*v.f_frsize;
        printf("{\"data_available_bytes\":%llu,\"minimum_bytes\":16777216}\n",available);
        return available>=16U*1024U*1024U ? 0 : 2;
    }
    if (argc!=2 || strcmp(argv[1],"/data/resmgrcheck/phase4-full")) return 2;
    struct statvfs before,after;struct stat a,b;
    if (stat(argv[1],&a) || stat("/data/resmgrcheck",&b) || a.st_dev==b.st_dev || statvfs(argv[1],&before)) return 2;
    if (before.f_blocks*before.f_frsize>16U*1024U*1024U) return 2;
    int fd=open("/data/resmgrcheck/phase4-full/sink",O_CREAT|O_EXCL|O_WRONLY,0600);
    if (fd<0) return 2;
    char bytes[4096];memset(bytes,'f',sizeof(bytes));unsigned total=0;int error=0;
    while (total<16U*1024U*1024U) {
        ssize_t n=write(fd,bytes,sizeof(bytes));
        if (n<0) { error=errno;break; }
        if (!n) break;
        total+=(unsigned)n;
    }
    int synced=fsync(fd);close(fd);
    if (statvfs(argv[1],&after)) return 2;
    printf("{\"bytes_written\":%u,\"write_errno\":%d,\"enospc\":%d,\"fsync_rc\":%d,\"blocks\":%llu,\"free_blocks\":%llu}\n",
      total,error,ENOSPC,synced,(unsigned long long)after.f_blocks,(unsigned long long)after.f_bfree);
    return error==ENOSPC ? 0 : 2;
}
