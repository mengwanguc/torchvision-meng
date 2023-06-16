/* Author:  Gus Waldspurger
   Date:    June 16, 2023.

   Implementation of a MinIO cache.
   */

#ifndef __MINIO_MODULE_H_
#define __MINIO_MODULE_H_

#include <stdlib.h>

/* Cache replacement policy. */
typedef enum {
    POLICY_FIFO,
    POLICY_MINIO,
    N_POLICIES
} policy_t;

/* Cache. */
typedef struct {
    policy_t policy;    /* Replacement policy. Only MinIO supported. */
    size_t size;        /* Size of cache in bytes. */
    size_t used;        /* Number of bytes cached. */
} cache_t;

#endif