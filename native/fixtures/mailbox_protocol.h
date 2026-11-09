#ifndef RMC_MAILBOX_PROTOCOL_H
#define RMC_MAILBOX_PROTOCOL_H
#include <stdint.h>
#include <devctl.h>
/* One retained message, independent of its short-lived waiting consumers.
 * FETCH is non-consuming; only explicit matching-generation ACK consumes it. */
struct mailbox_result { uint64_t channel; int32_t value; uint32_t reserved; };
struct mailbox_ack { uint64_t channel; uint32_t generation, reserved; };
struct mailbox_state {
    uint32_t pending, unblocks, completed, generation;
    uint32_t message_exists, message_ready, acknowledgements;
};
struct mailbox_identity { uint32_t protocol, pid; char instance[64]; };
#define MAILBOX_ARM __DIOF(_DCMD_MISC,0xb1,struct mailbox_state)
#define MAILBOX_PUBLISH __DIOF(_DCMD_MISC,0xb2,struct mailbox_state)
#define MAILBOX_STATE __DIOF(_DCMD_MISC,0xb3,struct mailbox_state)
#define MAILBOX_FETCH __DIOTF(_DCMD_MISC,0xb4,struct mailbox_result)
#define MAILBOX_ACK __DIOTF(_DCMD_MISC,0xb5,struct mailbox_ack)
#define MAILBOX_IDENTITY __DIOF(_DCMD_MISC,0xb6,struct mailbox_identity)
#endif
