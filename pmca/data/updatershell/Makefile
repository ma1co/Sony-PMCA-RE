MODE = UPDATER

BUILD = build
FDAT = fdat
BUILDDIR = $(BUILD)/gen$(GEN)
PLATFORMDIR = platform

CSOURCES = mount process
CPPSOURCES = updaterbody usbshell usbtransfer
MAIN = $(BUILD)/libupdaterbody_gen$(GEN).so

.PHONY: pack
pack: all
	./pack.py $(BUILD) $(FDAT)

.PHONY: all
all:
	$(MAKE) main GEN=1
	$(MAKE) main GEN=2
	$(MAKE) main GEN=3

.PHONY: main
main: $(MAIN)

.PHONY: clean
clean:
	rm -rf $(BUILD)/*
	rm -rf $(FDAT)/*
	$(MAKE) -C $(PLATFORMDIR)/stlport/build/lib -f gcc.mak clean

include $(PLATFORMDIR)/build.mk

$(MAIN): $(OBJS) $(LIBOBJS)
	$(CXX) $(LDFLAGS) -L$(BUILDDIR)/$(LIBDIR) $(OBJS) $(LIBS:%=-l%) -shared -o $@
