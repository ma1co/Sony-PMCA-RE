#pragma once
#include "api/usbcmd.hpp"

class UsbTransfer
{
public:
    virtual ~UsbTransfer() {};
    virtual void read(void *buffer, size_t size) = 0;
    virtual void write(const void *buffer, size_t size) = 0;
};

class UsbSequenceTransfer : public UsbTransfer
{
private:
    UsbCmd *cmd;
    unsigned int sequence;
public:
    UsbSequenceTransfer(UsbCmd *cmd): cmd(cmd), sequence(0) {}
    virtual void read(void *buffer, size_t size);
    virtual void write(const void *buffer, size_t size);
};

void usb_transfer_socket(UsbTransfer *transfer, int fd_in, int fd_out);
void usb_transfer_read_fd(UsbTransfer *transfer, int fd);
void usb_transfer_write_fd(UsbTransfer *transfer, int fd);
void usb_transfer_read_buffer(UsbTransfer *transfer, const char *buffer, size_t size);
