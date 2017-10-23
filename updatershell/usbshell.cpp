#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>

#include "api/bootloader.hpp"
#include "api/properties.hpp"
#include "api/usbcmd.hpp"
#include "usbshell.hpp"
#include "usbtransfer.hpp"

extern "C"
{
    #include "process.h"
}

using namespace std;

#define USB_FEATURE_SHELL 0x23
#define USB_RESULT_SUCCESS 0
#define USB_RESULT_ERROR -1

struct list_entry {
    int id;
    void *value;
};

static list_entry property_list[] = {
    {*(int *) "MODL", &prop_model_name()},
    {*(int *) "PROD", &prop_model_code()},
    {*(int *) "SERN", &prop_serial_number()},
    {*(int *) "BKRG", &prop_backup_region()},
    {*(int *) "FIRM", &prop_firmware_version()},
};

struct usb_list_response {
    int id;
    int status;
    char value[0xfff4];
};

struct usb_shell_request {
    int cmd;
    char data[0xfff8];
};

struct usb_shell_response {
    int result;
};

void usbshell_loop()
{
    UsbCmd *cmd = new UsbCmd(USB_FEATURE_SHELL);
    UsbTransfer *transfer = new UsbSequenceTransfer(cmd);

    while (1) {
        usb_shell_request request;
        usb_shell_response response;
        transfer->read(&request, sizeof(request));

        if (request.cmd == *(int *) "TEST") {
            response.result = USB_RESULT_SUCCESS;
            transfer->write(&response, sizeof(response));
        } else if (request.cmd == *(int *) "PROP") {
            vector<list_entry> props;
            for (int i = 0; i < (int) (sizeof(property_list) / sizeof(property_list[0])); i++) {
                if (((Property *) property_list[i].value)->is_available())
                    props.push_back(property_list[i]);
            }

            response.result = props.size();
            transfer->write(&response, sizeof(response));

            for (vector<list_entry>::iterator it = props.begin(); it != props.end(); it++) {
                transfer->read(NULL, 0);
                usb_list_response prop_response;
                prop_response.id = it->id;
                strncpy(prop_response.value, ((Property *) it->value)->get_string_value().c_str(), sizeof(prop_response.value));
                transfer->write(&prop_response, sizeof(prop_response));
            }
        } else if (request.cmd == *(int *) "SHEL") {
            int fd_stdin, fd_stdout;
            const char *args[] = { "sh", "-i", NULL };
            int pid = popen2((char *const *) args, &fd_stdin, &fd_stdout);
            response.result = pid >= 0 ? USB_RESULT_SUCCESS : pid;
            transfer->write(&response, sizeof(response));

            if (pid >= 0)
                usb_transfer_socket(transfer, fd_stdin, fd_stdout);
        } else if (request.cmd == *(int *) "EXEC") {
            int fd_stdout;
            const char *args[] = { "sh", "-c", request.data, NULL };
            int pid = popen2((char *const *) args, NULL, &fd_stdout);
            response.result = pid >= 0 ? USB_RESULT_SUCCESS : pid;
            transfer->write(&response, sizeof(response));

            if (pid >= 0)
                usb_transfer_socket(transfer, 0, fd_stdout);
        } else if (request.cmd == *(int *) "PULL") {
            int fd = open(request.data, O_RDONLY);
            response.result = fd >= 0 ? USB_RESULT_SUCCESS : fd;
            transfer->write(&response, sizeof(response));

            if (fd >= 0)
                usb_transfer_read_fd(transfer, fd);
        } else if (request.cmd == *(int *) "BLDR") {
            int fd = open(BOOTLOADER_DEV, O_RDONLY);
            vector<bootloader_block> blocks;
            try {
                blocks = bootloader_get_blocks(fd);
                response.result = blocks.size();
            } catch (const bootloader_error &) {
                response.result = USB_RESULT_ERROR;
            }
            transfer->write(&response, sizeof(response));

            for (vector<bootloader_block>::iterator it = blocks.begin(); it != blocks.end(); it++) {
                vector<char> data;
                try {
                    data = bootloader_read_block(fd, *it);
                } catch (const bootloader_error &) {
                    // ignore
                }
                usb_transfer_read_buffer(transfer, &data[0], data.size());
            }
            close(fd);
        } else if (request.cmd == *(int *) "EXIT") {
            response.result = USB_RESULT_SUCCESS;
            transfer->write(&response, sizeof(response));
            break;
        } else {
            response.result = USB_RESULT_ERROR;
            transfer->write(&response, sizeof(response));
        }
    }

    usleep(500e3);
    delete transfer;
    delete cmd;
}
