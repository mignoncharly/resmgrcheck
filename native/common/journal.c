#include "journal.h"
#include <errno.h>
#include <limits.h>
#include <fcntl.h>
#define JOURNAL_FRAMES 8192
#define JOURNAL_BYTES (8U*1024U*1024U)
static unsigned frame_limit=512;
static size_t byte_limit=2U*1024U*1024U;
static char *frames[JOURNAL_FRAMES];
static size_t lengths[JOURNAL_FRAMES],total;
static unsigned count;
static int sink_error,overflow,fault;
static int writer(const cJSON *o) {
    char *s=cJSON_PrintUnformatted(o);
    if (!s) { overflow=1;return 0; }
    size_t n=strlen(s);
    if (count==frame_limit || total+n+1>byte_limit || n+1>PIPE_BUF) {
        cJSON_free(s);overflow=1;return 0;
    }
    char *frame=malloc(n+1);
    if (!frame) { cJSON_free(s);overflow=1;return 0; }
    memcpy(frame,s,n);frame[n]='\n';cJSON_free(s);
    frames[count]=frame;lengths[count++]=n+1;total+=n+1;
    if (sink_error) return 0;
    if (fault==1) { close(STDOUT_FILENO);fault=0; }
    if (fault==2) {
        /* Explicit lab-only switch to an already exhausted, isolated filesystem.
         * The write below must return the real filesystem error. An ineffective
         * setup is rejected by qualification, never promoted to a sink failure. */
        int fd=open("/data/resmgrcheck/phase4-full/sink",O_WRONLY|O_APPEND|O_NOFOLLOW|O_CLOEXEC);
        if (fd>=0) { if (dup2(fd,STDOUT_FILENO)<0) sink_error=errno;close(fd); }
        else sink_error=errno;
        fault=0;
    }
    if (sink_error) return 0;
    ssize_t result=write(STDOUT_FILENO,frame,n+1);int error=result==(ssize_t)(n+1) ? 0 : errno ? errno : EIO;
    if (error) sink_error=error;
    return !error;
}
void rmc_journal_limits(unsigned cycles,int extended) { if (cycles>1) { frame_limit=JOURNAL_FRAMES;byte_limit=JOURNAL_BYTES; } else if (extended) { frame_limit=2048;byte_limit=4U*1024U*1024U; } }
void rmc_journal_start(void) { rmc_set_writer(writer); }
int rmc_journal_sink_error(void) { return sink_error; }
void rmc_journal_sink_failed(int error) { if (!sink_error) sink_error=error ? error : EIO; }
int rmc_journal_overflow(void) { return overflow; }
void rmc_journal_fault(int quota) { fault=quota ? 2 : 1; }
int rmc_journal_seal(int fd) {
    if (fd<0 || overflow) return 0;
    for (unsigned i=0;i<count;++i) {
        size_t sent=0;
        while (sent<lengths[i]) {
            ssize_t n=write(fd,frames[i]+sent,lengths[i]-sent);
            if (n<0 && errno==EINTR) continue;
            if (n<=0) return 0;
            sent+=(size_t)n;
        }
    }
    return fsync(fd)==0;
}
void rmc_journal_free(void) {
    for (unsigned i=0;i<count;++i) free(frames[i]);
    rmc_set_writer(NULL);
}
