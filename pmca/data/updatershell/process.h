#pragma once
#include <sys/types.h>

pid_t popen2(char *const *command, int *stdin, int *stdout);
