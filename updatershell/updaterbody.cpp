#include <sys/mount.h>

#include "updaterbody.hpp"
#include "usbshell.hpp"

extern "C"
{
    #include "drivers/backup.h"
}

using namespace Updater;
using namespace UpdaterAPI;

UpdaterBody *GetBody(bool flag, UPDATER_ACTION_MODE mode, firmware_information_t::information *info)
{
    return new UpdaterBodyImpl;
}

void ReleaseBody(UpdaterBody *body)
{
    delete body;
}

bool UpdaterBodyImpl::Execute(RingBuffer *buffer, CallbackInterface *interface)
{
    mount("/dev/nflasha2", "/setting", "vfat", MS_NOATIME | MS_SYNCHRONOUS, "posix_attr,shortname=mixed");

    try {
        usbshell_loop();
#ifdef DRIVER_backup
        Backup_sync_all();
#endif
    } catch (...) {
        // ignore
    }

    umount("/setting");
    return true;
}
