#include <cstring>
#include <fcntl.h>
#include <signal.h>
#include <stdexcept>
#include <string>
#include <unistd.h>

#include "usbtransfer.hpp"

extern "C"
{
    #include "errno.h"
}

using namespace std;

struct usb_sequence_transfer_header {
    unsigned int sequence;
};

void UsbSequenceTransfer::read(void *buffer, size_t size)
{
    size_t buf_size = sizeof(usb_sequence_transfer_header) + size;
    char *buf = new char[buf_size];
    int n = cmd->read(buf, buf_size, 0);
    if (n != (int) buf_size)
        throw runtime_error("Read error");
    if (((usb_sequence_transfer_header *) buf)->sequence != sequence)
        throw runtime_error("Sequence error");
    memcpy(buffer, buf + sizeof(usb_sequence_transfer_header), size);
    delete[] buf;
}

void UsbSequenceTransfer::write(const void *buffer, size_t size)
{
    size_t buf_size = sizeof(usb_sequence_transfer_header) + size;
    char *buf = new char[buf_size];
    ((usb_sequence_transfer_header *) buf)->sequence = sequence;
    memcpy(buf + sizeof(usb_sequence_transfer_header), buffer, size);
    int n = cmd->write(buf, buf_size, 0);
    if (n != (int) buf_size)
        throw runtime_error("Write error");
    delete[] buf;
    sequence++;
}

#define USB_STATUS_EOF 1
#define USB_STATUS_CANCEL 1

struct usb_status_msg {
    int status;
};

struct usb_data_msg {
    size_t size;
    char data[0xfff8];
};

struct usb_socket_header {
    unsigned int status;
    size_t rx_size;
    size_t tx_size;
};

struct usb_socket_buf {
    size_t offset;
    size_t size;
    char data[0xfff4];
};

void usb_transfer_socket(UsbTransfer *transfer, int fd_in, int fd_out)
{
    sighandler_t sigpipe = signal(SIGPIPE, SIG_IGN);
    if (fd_in)
        fcntl(fd_in, F_SETFL, O_NONBLOCK);
    if (fd_out)
        fcntl(fd_out, F_SETFL, O_NONBLOCK);

    usb_socket_buf rx_buf = {0}, tx_buf = {0};
    while (1) {
        // Write to stdin
        if (fd_in && rx_buf.size > 0) {
            int n = write(fd_in, &rx_buf.data + rx_buf.offset, rx_buf.size);
            if (n >= 0) {
                rx_buf.offset += n;
                rx_buf.size -= n;
            } else if (errno == EPIPE) {
                close(fd_in);
                fd_in = 0;
            } else if (errno != EAGAIN) {
                throw runtime_error("Write error");
            }
        }
        if (!fd_in)
            rx_buf.size = 0;

        // Read from stdout
        if (fd_out && tx_buf.size == 0) {
            int n = read(fd_out, &tx_buf.data, sizeof(tx_buf.data));
            if (n > 0) {
                tx_buf.offset = 0;
                tx_buf.size = n;
            } else if (n == 0) {
                close(fd_out);
                fd_out = 0;
            } else if (errno != EAGAIN) {
                throw runtime_error("Read error");
            }
        }

        // Receive master header
        usb_socket_header master_header;
        transfer->read(&master_header, sizeof(master_header));

        // Send slave header
        usb_socket_header slave_header;
        slave_header.status = fd_out ? 0 : USB_STATUS_EOF;
        slave_header.tx_size = tx_buf.size;
        slave_header.rx_size = rx_buf.size == 0 ? sizeof(rx_buf.data) : 0;
        transfer->write(&slave_header, sizeof(slave_header));

        // Calculate transfer size
        size_t rx_size = master_header.tx_size <= slave_header.rx_size ? master_header.tx_size : slave_header.rx_size;
        size_t tx_size = master_header.rx_size <= slave_header.tx_size ? master_header.rx_size : slave_header.tx_size;

        // End condition
        if (master_header.status == USB_STATUS_EOF && slave_header.status == USB_STATUS_EOF)
            break;

        // Close pipe if requested
        if (fd_in && rx_buf.size == 0 && master_header.status == USB_STATUS_EOF) {
            close(fd_in);
            fd_in = 0;
        }

        // Receive data
        transfer->read(&rx_buf.data, rx_size);
        if (rx_size > 0) {
            rx_buf.offset = 0;
            rx_buf.size = rx_size;
        }

        // Send data
        transfer->write(&tx_buf.data, tx_size);
        tx_buf.offset += tx_size;
        tx_buf.size -= tx_size;
    }

    signal(SIGPIPE, sigpipe);
    if (fd_in)
        close(fd_in);
    if (fd_out)
        close(fd_out);
}

void usb_transfer_read_fd(UsbTransfer *transfer, int fd)
{
    fcntl(fd, F_SETFL, 0);
    while (1) {
        usb_status_msg status_msg;
        usb_data_msg data_msg;

        int n = read(fd, data_msg.data, sizeof(data_msg.data));
        if (n < 0)
            throw runtime_error("Read error");
        data_msg.size = n;

        transfer->read(&status_msg, sizeof(status_msg));
        transfer->write(&data_msg, sizeof(data_msg));

        if (n == 0 || status_msg.status == USB_STATUS_CANCEL)
            break;
    }
    close(fd);
}

void usb_transfer_write_fd(UsbTransfer *transfer, int fd)
{
    fcntl(fd, F_SETFL, 0);
    while (1) {
        usb_status_msg status_msg = {0};
        usb_data_msg data_msg;

        transfer->read(&data_msg, sizeof(data_msg));
        transfer->write(&status_msg, sizeof(status_msg));

        int n = write(fd, data_msg.data, data_msg.size);
        if (n != (int) data_msg.size)
            throw runtime_error("Write error");

        if (data_msg.size == 0)
            break;
    }
    close(fd);
}

void usb_transfer_read_buffer(UsbTransfer *transfer, const char *buffer, size_t size)
{
    usb_status_msg status_msg;
    usb_data_msg data_msg;

    for (size_t i = 0; i < size; i += sizeof(data_msg.data)) {
        data_msg.size = (size - i) >= sizeof(data_msg.data) ? sizeof(data_msg.data) : (size - i);
        memcpy(data_msg.data, buffer + i, data_msg.size);

        transfer->read(&status_msg, sizeof(status_msg));
        transfer->write(&data_msg, sizeof(data_msg));

        if (status_msg.status == USB_STATUS_CANCEL)
            break;
    }

    data_msg.size = 0;
    transfer->read(&status_msg, sizeof(status_msg));
    transfer->write(&data_msg, sizeof(data_msg));
}
