/* SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note */
#ifndef _ASM_POSIX_TYPES_H
#define _ASM_POSIX_TYPES_H

/* h8300-unknown-linux required long */
#define __kernel_size_t __kernel_size_t
typedef unsigned long	__kernel_size_t;
typedef long		__kernel_ssize_t;
typedef long		__kernel_ptrdiff_t;

#include <asm-generic/posix_types.h>

#endif /* _ASM_POSIX_TYPES_H */
