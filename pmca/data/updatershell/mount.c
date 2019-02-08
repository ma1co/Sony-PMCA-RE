#include <sys/mount.h>

#include "mount.h"

int mount_vfat(const char *source, const char *target)
{
    return mount(source, target, "vfat", MS_NOATIME | MS_SYNCHRONOUS, "posix_attr,shortname=mixed");
}
