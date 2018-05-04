#include <sys/mount.h>

#include "updaterbody.hpp"
#include "usbshell.hpp"

extern "C"
{
    #include "mount.h"
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
    mount_vfat("/dev/nflasha2", "/setting");

    try {
        usbshell_loop();
    } catch (...) {
        // ignore
    }

    umount("/setting");
    return true;
}
