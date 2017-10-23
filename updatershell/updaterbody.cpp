#include <sys/mount.h>

#include "updaterbody.hpp"
#include "usbshell.hpp"

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
    mount("/dev/nflasha2", "/setting", "vfat", MS_RDONLY, "");

    try {
        usbshell_loop();
    } catch (...) {
        // ignore
    }

    umount("/setting");
    return true;
}
