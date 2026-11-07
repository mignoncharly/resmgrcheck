#include "../fixtures/control_v1.h"
static int barrier_control(int fd,const char *op,int *handled) {
    struct rmc_fixture_command command={0};*handled=1;
    if (!strcmp(op,"cycle")) { command.action=RMC_SET_CYCLE;command.cycle=(unsigned)strtoul(getenv("RMC_CYCLE"),NULL,10); }
    else if (!strcmp(op,"arm_complete")) command.action=RMC_ARM_COMPLETE;
    else if (!strcmp(op,"drain_stale")) command.action=RMC_DRAIN_STALE;
    else if (!strcmp(op,"hold_next")) command.action=RMC_HOLD_NEXT;
    else if (!strcmp(op,"park")) command.action=RMC_PARK;
    else { *handled=0;return 0; }
    return devctl(fd,RMC_FIXTURE_COMMAND,&command,sizeof(command),NULL);
}
