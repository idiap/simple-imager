# -*- mode:makefile; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=make tabstop=4 softtabstop=4 shiftwidth=4 autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


## Variables
VERSION         := $(shell head -n 1 debian/changelog | sed 's/^[^(]*(\([^)]*\)).*$$/\1/')
MACHINE         := $(shell uname -m)
ifeq ($(MACHINE), x86_64)
    ARCH        := x86_64
    ARCH_BITS   := 64
endif
NCPUS           := $(shell grep -E '^(physical|core) id' /proc/cpuinfo | tr '\n' ' ' | sed 's/ physical id/\nphysical id/g;s/[ \t]//g' | sort -u | wc -l)


## Directories
ROOT_DIR        := $(CURDIR)
DOWNLOAD_DIR    := $(ROOT_DIR)/download
INITRD_DIR      := $(ROOT_DIR)/initrd
KERNEL_DIR      := $(ROOT_DIR)/kernel
BUILD_DIR       := $(ROOT_DIR)/build
RELEASE_DIR     := $(ROOT_DIR)/release
BOOT_DIR        := $(RELEASE_DIR)/simple-imager-target_$(VERSION)/$(ARCH)


## Tools
DOWNLOAD=$(ROOT_DIR)/tools/download
PTAR=$(ROOT_DIR)/tools/ptar
COPY_FIRMWARES=$(ROOT_DIR)/tools/copy_firmwares
COPY_LIBRARIES=$(ROOT_DIR)/tools/copy_libraries


## Target (default)
.PHONY: help
help: show_targets


## Includes
include $(KERNEL_DIR)/kernel.rul
include $(INITRD_DIR)/initrd.rul


## Targets (cont'd)
.PHONY: download
download: $(ROOT_DIR).download

.PHONY: build
build: $(ROOT_DIR).build

.PHONY: release
release: $(RELEASE_DIR).release

.PHONY: tarball
tarball: $(ROOT_DIR)/simple-imager-target_$(VERSION)_$(ARCH).tar.xz

.PHONY: clear
clear: $(ROOT_DIR).clear

.PHONY: clean
clean: $(ROOT_DIR).clean

.PHONY: distclean
distclean: $(ROOT_DIR).distclean

.PHONY: show_targets
show_targets:
	@echo "Available targets:"
	@echo "  download"
	@echo "    Download all upstream resources."
	@echo "  build"
	@echo "    Build everything (initrd and kernel)."
	@echo "  release"
	@echo "    Install everything in the release directory (initrd and kernel)."
	@echo "  tarball"
	@echo "    Create a tarball with the initrd and kernel."
	@echo "  clear"
	@echo "    Uninstall (only top level; see other *_uninstall below)."
	@echo "  clean"
	@echo "    Clean the entire build tree."
	@echo "  distclean"
	@echo "    Clean everything (incl. downloaded resources!)."
	@echo
	@echo "  kernel_{download|build|install|uninstall|clean}"
	@echo "    Download/build/install/uninstall/clean only the kernel."
	@echo
	@echo "  initrd_{download|mkdir|build|install|uninstall|clean}"
	@echo "    Download/build/install/uninstall/clean only the initrd."
	@echo
	@echo "  <package>_{download|build|install|uninstall|clean}"
	@echo "    Download/build/install/uninstall/clean only <package>."
	@echo "    (see initrd/kernel included *.rul for packages name)"

all: show_targets


## Recipes
$(DOWNLOAD_DIR).mkdir:
	test -d $(DOWNLOAD_DIR) || mkdir $(DOWNLOAD_DIR)
	touch $@

$(ROOT_DIR).download: $(DOWNLOAD_DIR).mkdir $(KERNEL_DIR).download $(INITRD_DIR).download

$(BUILD_DIR).mkdir:
	test -d $(BUILD_DIR) || mkdir $(BUILD_DIR)
	touch $@

$(ROOT_DIR).build: $(BUILD_DIR).mkdir $(KERNEL_BUILD_DIR).build $(INITRD_BUILD_DIR).build

$(RELEASE_DIR).mkdir:
	test -d $(RELEASE_DIR) || mkdir $(RELEASE_DIR)
	touch $@

$(BOOT_DIR).mkdir: $(RELEASE_DIR).mkdir
	mkdir -p $(BOOT_DIR)
	touch $@

$(RELEASE_DIR).release: $(BOOT_DIR).mkdir $(KERNEL_BUILD_DIR).install $(INITRD_BUILD_DIR).install
	@echo "## DONE !!!"
	ls -al $(BOOT_DIR)/*
	touch $@

$(ROOT_DIR)/simple-imager-target-_$(VERSION)_$(ARCH).tar.xz: $(RELEASE_DIR).release
	$(PTAR) $@ -C $(RELEASE_DIR) -cp --exclude=*.mkdir simple-imager-target-*

$(ROOT_DIR).clear: $(KERNEL_BUILD_DIR).uninstall $(INITRD_BUILD_DIR).uninstall
	rm -rf $(RELEASE_DIR)*

$(ROOT_DIR).clean: $(ROOT_DIR).clear $(KERNEL_BUILD_DIR).clean $(INITRD_BUILD_DIR).clean
	rm -rf $(BUILD_DIR)*

$(ROOT_DIR).distclean: $(ROOT_DIR).clean
	rm -rf $(DOWNLOAD_DIR)*

