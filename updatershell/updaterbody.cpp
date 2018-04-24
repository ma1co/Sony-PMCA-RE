#include <sys/mount.h>

#include "api/android_data_backup.hpp"
#include "updaterbody.hpp"
#include "usbshell.hpp"

using namespace Updater;
using namespace UpdaterAPI;

static int mount_vfat(const char *source, const char *target)
{
    return mount(source, target, "vfat", MS_NOATIME | MS_SYNCHRONOUS, "posix_attr,shortname=mixed");
}

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
    AndroidDataBackup *android_data_ptr = NULL;

    mount_vfat("/dev/nflasha2", "/setting");

#ifdef API_android_data_backup
    mount_vfat(ANDROID_DATA_DEV, "/mnt");
    AndroidDataBackup android_data("/mnt");
    android_data.initialize();
    if (android_data.is_available()) {
        try {
            android_data.read();
            android_data.mount();
            android_data_ptr = &android_data;
        } catch (...) {
            // ignore
        }
    }
#endif

    try {
        usbshell_loop(android_data_ptr);
    } catch (...) {
        // ignore
    }

#ifdef API_android_data_backup
    if (android_data.is_available()) {
        try {
            android_data.unmount();
        } catch (...) {
            // ignore
        }
    }
    umount("/mnt");
#endif

    umount("/setting");
    return true;
}
