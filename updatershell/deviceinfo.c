#include <fcntl.h>
#include <sys/mount.h>
#include <unistd.h>

#include "deviceinfo.h"
#include "drivers/backup.h"

#ifdef DRIVER_backup
int read_fw_version(short *version)
{
    int err;
    err = mount("/dev/nflasha2", "/setting", "vfat", MS_RDONLY, "");
    if (err)
        return err;

    int fd = open("/setting/updater/dat4", O_RDONLY);
    if (fd < 0)
        return fd;

    if (read(fd, version, sizeof(*version)) != sizeof(*version))
        return -1;

    err = close(fd);
    if (err)
        return err;

    err = umount("/setting");
    if (err)
        return err;

    return 0;
}

int backup_read(int id, char *buf, size_t size)
{
    if (Backup_get_datasize(id) != (int) size)
        return -1;
    if (Backup_read(id, buf) != (int) size)
        return -1;
    return 0;
}

int get_device_info(struct device_info *info)
{
    if (backup_read(BACKUP_ID_MODEL_NAME, info->model, sizeof(info->model)))
        return -1;
    if (backup_read(BACKUP_ID_MODEL_CODE, info->product, sizeof(info->product)))
        return -1;
    if (backup_read(BACKUP_ID_SERIAL, info->serial, sizeof(info->serial)))
        return -1;
    if (read_fw_version((short *) info->firmware))
        return -1;
    return 0;
}
#else
int get_device_info(struct device_info *info)
{
    return -1;
}
#endif
