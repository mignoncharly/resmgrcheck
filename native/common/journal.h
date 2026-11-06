#ifndef RMC_JOURNAL_H
#define RMC_JOURNAL_H
#include "event.h"
void rmc_journal_start(void);
int rmc_journal_sink_error(void);
int rmc_journal_overflow(void);
int rmc_journal_seal(int fd);
void rmc_journal_fault(int quota);
void rmc_journal_sink_failed(int error);
void rmc_journal_free(void);
#endif
