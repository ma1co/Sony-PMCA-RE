#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "process.h"

#define PIPE_READ 0
#define PIPE_WRITE 1

pid_t popen2(char *const *command, int *stdin, int *stdout)
{
    int p_stdin[2], p_stdout[2];
    if (pipe(p_stdin) || pipe(p_stdout))
        return -1;

    pid_t pid = fork();
    if (pid < 0)
        return pid;

    if (pid == 0) {
        close(p_stdin[PIPE_WRITE]);
        close(p_stdout[PIPE_READ]);

        dup2(p_stdin[PIPE_READ], STDIN_FILENO);
        dup2(p_stdout[PIPE_WRITE], STDOUT_FILENO);
        dup2(p_stdout[PIPE_WRITE], STDERR_FILENO);

        execvp(*command, command);
        exit(EXIT_FAILURE);
    }

    close(p_stdin[PIPE_READ]);
    close(p_stdout[PIPE_WRITE]);

    if (stdin)
        *stdin = p_stdin[PIPE_WRITE];
    else
        close(p_stdin[PIPE_WRITE]);

    if (stdout)
        *stdout = p_stdout[PIPE_READ];
    else
        close(p_stdout[PIPE_READ]);

    return pid;
}
