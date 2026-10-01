#define _GNU_SOURCE
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef __x86_64__
#error This demonstration only supports x86_64 Linux
#endif

int main(void) {
    struct sock_filter instructions[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_getpid, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    struct sock_fprog filter = {
        .len = sizeof(instructions) / sizeof(instructions[0]),
        .filter = instructions,
    };

    printf("before_getpid=%ld\n", syscall(SYS_getpid));
    fflush(stdout);
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == -1) {
        perror("PR_SET_NO_NEW_PRIVS");
        return 1;
    }
    printf("no_new_privs=%d\n", prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0));
    fflush(stdout);
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter) == -1) {
        perror("PR_SET_SECCOMP");
        return 1;
    }
    errno = 0;
    long denied_pid = syscall(SYS_getpid);
    int denied_errno = errno;
    long allowed_parent = syscall(SYS_getppid);
    printf("after_getpid=%ld errno=%d allowed_getppid=%ld\n", denied_pid, denied_errno, allowed_parent);
    return denied_pid == -1 && denied_errno == EPERM && allowed_parent > 0 ? 0 : 1;
}
