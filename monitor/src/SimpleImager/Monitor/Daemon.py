# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import errno
import logging
import os
import signal
import sqlite3
import stat
import subprocess
import sys
import syslog
import threading
import time

# Extra
# ... deb: python-argparse, python-daemon
import argparse
from daemon import \
    DaemonContext
from daemon.runner import \
    emit_message, \
    is_pidfile_stale, \
    make_pidlockfile

# Simple Imager
from SimpleImager.Monitor import \
    SI_Monitor_Backend, \
    SI_Monitor_Logger


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class SI_Monitor_Daemon:
    """
    Simple Imager Monitor daemon (skeleton)
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self):
        """
        Constructor.
        """

        # Properties
        # ... resources
        self._oLogger = logging.getLogger('si_monitor.service')
        self._oBackend = None

        # ... runtime
        self.__oFileLog = None
        self._bStop = False

        # Initialization
        SI_Monitor_Backend.initLogger()
        self._initArgumentParser()


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    # Initialization
    #------------------------------------------------------------------------------

    def _initArgumentParser(self):
        """
        Creates the arguments parser (and help generator).
        """

        # Create argument parser
        self._oArgumentParser = argparse.ArgumentParser(sys.argv[0].split(os.sep)[-1])

        # ... version
        self._oArgumentParser.add_argument(
            '-v', '--version', action='version',
            version=('Simple Imager Monitor - %{VERSION} - Cedric Dufour <http://cedric.dufour.name>'))

        # ... remain in foreground
        self._oArgumentParser.add_argument(
            '-f', '--foreground', action='store_true',
            default=False,
            help='Do not fork to background / Remain on foreground')

        # ... PID file
        self._oArgumentParser.add_argument(
            '-p', '--pid', type=str,
            metavar='<pid-file>',
            default='/var/run/si_monitor.pid',
            help='Path to daemon PID file (default:/var/run/si_monitor.pid)')

        # ... log file
        self._oArgumentParser.add_argument(
            '-l', '--log', type=str,
            metavar='<log-file>',
            default='/var/log/simple-imager/si_monitor.legacy.log',
            help='Path to daemon log file (default:/var/log/simple-imager/si_monitor.legacy.log)')

        # ... debug
        self._oArgumentParser.add_argument(
            '-d', '--debug', action='store_true',
            default=False,
            help='Enable debugging messages')

        # ... database file
        self._oArgumentParser.add_argument(
            '-D', '--database', type=str,
            metavar='<database-file>',
            default='/var/lib/simple-imager/si_monitor.sqlite',
            help='Path to SQLite database file (default:/var/lib/simple-imager/si_monitor.sqlite)')

        # ... hooks directory
        self._oArgumentParser.add_argument(
            '-H', '--hooks', type=str,
            metavar='<hooks-dir>',
            default='/etc/simple-imager/si_monitor.hooks.d',
            help='Path to hooks directory (default:/etc/simple-imager/si_monitor.hooks.d)')


    def _initArguments(self, _aArguments=None):
        """
        Parses the command-line arguments; returns a non-zero exit code in case of failure.
        """

        # Parse arguments
        if _aArguments is None:
             _aArguments = sys.argv
        try:
            self._oArguments = self._oArgumentParser.parse_args()
        except Exception as e:
            self._oArguments = None
            self._oLogger.error('Failed to parse arguments; %s' % str(e))
            return errno.EINVAL

        return 0


    def _initDatabase(self):
        """
        Initialize the SQLite database; returns a non-zero exit code in case of failure.
        """

        self._oLogger.debug('Opening database; %s' % self._oArguments.database)
        try:
            self.__oDatabase = sqlite3.connect(database=self._oArguments.database, isolation_level=None, check_same_thread=False)
        except Exception as e:
            self._oLogger.error('Failed to open database; %s' % str(e))
            return errno.EIO
        # ... initialize table
        try:
            self.__oDatabase.execute('CREATE TABLE si_monitor(mac TEXT, ip TEXT, host TEXT, status TEXT, change REAL, message TEXT, progress INTEGER, speed INTEGER, heartbeat REAL)')
        except sqlite3.OperationalError as e:
            # Most likely, the table already exists
            pass
        except Exception as e:
            self._oLogger.error('Failed to initialize database; %s' % str(e))
            return errno.EIO

        return 0


    def _initHooks(self):
        """
        Initialize the processing hooks (scripts); returns a non-zero exit code in case of failure.
        """

        if len(self._oArguments.hooks):
            if not os.path.isdir(self._oArguments.hooks):
                self._oLogger.warning('Missing/invalid hooks directory; %s' % self._oArguments.hooks)
            else:
                for sHook in ['start', 'download', 'install', 'complete', 'error']:
                    sFileHook = self._oArguments.hooks.rstrip(os.sep)+os.sep+sHook
                    if os.path.isfile(sFileHook):
                        if (os.stat(sFileHook).st_mode & (stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)):
                            self._oLogger.debug('Registering hook; %s' % sFileHook)
                            self.__dFileHooks[sHook] = sFileHook
                        else:
                            self._oLogger.warning('Hook is not executable; %s' % sFileHook)

        return 0


    # Logging
    #------------------------------------------------------------------------------

    def __syslog(self, _sMessage):
        iLevel = syslog.LOG_INFO
        if _sMessage.find('ERROR') >= 0:
            iLevel = syslog.LOG_ERR
        elif _sMessage.find('WARNING') >= 0:
            iLevel = syslog.LOG_WARNING
        elif _sMessage.find('DEBUG') >= 0:
            iLevel = syslog.LOG_DEBUG
        syslog.syslog(iLevel, _sMessage)


    def __filelog(self, _sMessage):
        self.__oFileLog.write(_sMessage+'\n')
        self.__oFileLog.flush()


    # Daemon
    #------------------------------------------------------------------------------

    def __daemon(self):
        """
        Daemonizes the process; returns a non-zero exit code in case of failure.
        """

        # Daemonize
        try:
            # Create and check PID file
            oPidLockFile = make_pidlockfile(self._oArguments.pid, 0)
            if is_pidfile_stale(oPidLockFile):
                oPidLockFile.break_lock()
            if oPidLockFile.is_locked():
                self._oLogger.error('Daemon process already running; PID=%s' % oPidLockFile.read_pid())
                return errno.EEXIST

            # Create daemon context
            oDaemonContext = DaemonContext(pidfile=oPidLockFile)
            oDaemonContext.signal_map = {signal.SIGTERM: self.__signal}
            oDaemonContext.open()
            emit_message('[%s]' % os.getpid())

            # Redirect standard error to logfile/syslog
            if len(self._oArguments.log)==0 or self._oArguments.log=='syslog':
                syslog.openlog('si_monitor', syslog.LOG_PID, syslog.LOG_DAEMON)
                sys.stderr = SI_Monitor_Logger(self.__syslog)
            else:
                self.__oFileLog = open(self._oArguments.log, 'a')
                sys.stderr = SI_Monitor_Logger(self.__filelog)
            SI_Monitor_Backend.initLogger(sys.stderr)
            self._oLogger.debug('Successfully daemonized; PID=%s' % os.getpid())

            # Execute
            return self._run()
        except Exception as e:
            self._oLogger.error('Failed to daemonize; %s' % str(e))
            return errno.ESRCH


    def __signal(self, signal, frame):
        """
        Stop daemon.
        """

        self._oLogger.info('Signal received; stopping...')
        self._stop()


    # Service
    #------------------------------------------------------------------------------

    def _run(self):
        """
        Run the service; returns a non-zero exit code in case of failure.
        """

        # Create backend
        try:
            self._oBackend = SI_Monitor_Backend(self._oArguments.database, self._oArguments.hooks)
        except Exception as e:
            self._oLogger.error('Failed to create monitoring backend; %s' % str(e))
            return errno.EIO

        # TO BE OVERRIDEN!
        # Please implement your service interface by overriding this function
        # and calling the '_update' function when appropriate
        return 0


    def _update(self, _sClient, _sMAC, _sIP, _sHost, _sStatus, _sMessage, _iProgress, _iSpeed):
        """
        Update client status; returns a non-zero exit code in case of failure.
        """
        
        # Update backend
        try:
            self._oBackend.update(_sClient, _sMAC, _sIP, _sHost, _sStatus, _sMessage, _iProgress, _iSpeed)
        except Exception as e:
            self._oLogger.error('Failed to update monitoring backend; %s' % str(e))
            return errno.EIO
        return 0


    def _stop(self):
        """
        Stop the service; returns a non-zero exit code in case of failure.
        """

        # TO BE OVERRIDEN!
        self._bStop = True
        return 0


    # Main
    #------------------------------------------------------------------------------

    def run(self):
        """
        Run the service; returns a non-zero exit code in case of failure.
        """

        # Initialize arguments
        iReturn = self._initArguments()
        if iReturn:
            return iReturn

        # Configure logging
        if self._oArguments.debug:
            logging.getLogger('si_monitor').setLevel(logging.DEBUG)

        # Fork to background (?)
        if not self._oArguments.foreground:
            self._oLogger.debug('Starting background daemon')
            return self.__daemon()

        # Foreground processing
        self._oLogger.debug('Starting foreground processing')
        signal.signal(signal.SIGINT, self.__signal)
        signal.signal(signal.SIGTERM, self.__signal)
        return self._run()
