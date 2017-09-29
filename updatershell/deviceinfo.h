#pragma once

#define BACKUP_ID_MODEL_NAME 0x003e0005
#define BACKUP_ID_MODEL_CODE 0x00e70000
#define BACKUP_ID_SERIAL 0x00e70003

struct device_info {
    char model[16];
    char product[5];
    char serial[4];
    char firmware[2];
};

int get_device_info(struct device_info *info);
