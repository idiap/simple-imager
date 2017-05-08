# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import logging
import os
import sqlite3
import stat
import subprocess
import threading
import time


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class SI_Monitor_Backend:
    """
    Simple Imager Monitor backend.

    This class wraps the logic to process target status updates to the SQLite
    database or via external hooks (scripts).
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _sDatabaseFile, _sHooksDir=None, _bThreadSafe=True):
        """
        Constructor.
        """

        # Properties
        # ... arguments
        self.__sDatabaseFile = _sDatabaseFile
        self.__sHooksDir = _sHooksDir.rstrip(os.sep) if _sHooksDir else None
        self.__bThreadSafe = _bThreadSafe

        # ... resources
        self.__oLogger = logging.getLogger('si_monitor.backend')
        self.__oDatabase = None
        self.__dFileHooks = None

        # ... runtime
        self.__oLockLog = threading.Lock() if _bThreadSafe else None
        self.__oLockProcess = threading.Lock() if _bThreadSafe else None

        # Initialize
        SI_Monitor_Backend.initLogger()


    def __del__(self):
        """
        Destructor.
        """

        if self.__oDatabase: self.__oDatabase.close()


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    # Initialization
    #------------------------------------------------------------------------------

    def __initDatabase(self):
        """
        Initialize the SQLite database.
        """

        self.__oLogger.debug('Opening database; %s' % self.__sDatabaseFile)
        try:
            self.__oDatabase = sqlite3.connect(database=self.__sDatabaseFile, isolation_level=None, check_same_thread=(not self.__bThreadSafe))
            self.__oDatabase.row_factory = sqlite3.Row
        except Exception as e:
            raise RuntimeError('Failed to open database; %s' % str(e))
        # ... initialize table
        try:
            self.__oDatabase.execute('CREATE TABLE si_monitor(mac TEXT, ip TEXT, host TEXT, status TEXT, change REAL, message TEXT, progress INTEGER, speed INTEGER, heartbeat REAL)')
        except sqlite3.OperationalError as e:
            # Most likely, the table already exists
            pass
        except Exception as e:
            raise RuntimeError('Failed to initialize database; %s' % str(e))


    def __initHooks(self):
        """
        Initialize the processing hooks (scripts).
        """

        self.__dFileHooks = {}
        if self.__sHooksDir:
            if not os.path.isdir(self.__sHooksDir):
                self.__oLogger.warning('Missing/invalid hooks directory; %s' % self.__sHooksDir)
            else:
                for sHook in ('init', 'start', 'pre-install', 'download', 'install', 'post-install', 'complete', 'error'):
                    sFileHook = self.__sHooksDir+os.sep+sHook
                    if os.path.isfile(sFileHook):
                        if (os.stat(sFileHook).st_mode & (stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)):
                            self.__oLogger.debug('Registering hook; %s' % sFileHook)
                            self.__dFileHooks[sHook] = sFileHook
                        else:
                            self.__oLogger.warning('Hook is not executable; %s' % sFileHook)
    

    # Logging
    #------------------------------------------------------------------------------

    @staticmethod
    def initLogger(_oStream=None):
        """
        Initialize the logger (hierarchy).
        """

        # Parent logger
        oLogger_parent = logging.getLogger('si_monitor')
        if not logging.root.level==logging.NOTSET and oLogger_parent==logging.NOTSET:
            oLogger_parent.setLevel(logging.INFO)
        if _oStream or (not logging.root.handlers and not oLogger_parent.handlers):
            oHandler = logging.StreamHandler(_oStream)
            oHandler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            del oLogger_parent.handlers[:]
            oLogger_parent.addHandler(oHandler)


    def setLogger(self, _oLogger):
        """
        Set the internal logger to the given one.
        """

        # Internal logger
        self.__oLogger = _oLogger


    # Interface
    #------------------------------------------------------------------------------

    def update(self, _sMAC, _sIP, _sHost, _sStatus, _sMessage, _iProgress, _iSpeed, _sClient='n/a'):
        """
        [thread-safe] Update target status.
        """

        # Lock
        if self.__oLockProcess: self.__oLockProcess.acquire()
        try:

            # Initialization
            if self.__oDatabase is None: self.__initDatabase()
            if self.__dFileHooks is None: self.__initHooks()

            # Normalization
            _sMAC = _sMAC.upper()
            _sIP = _sIP.lower()

            # Store data in database
            bStatusChange = False
            try:
                self.__oLogger.debug('[%s(%s)] Updating database; %s' % (_sClient, _sStatus, self.__sDatabaseFile))
                oRow = self.__oDatabase.execute('SELECT ip, status FROM si_monitor WHERE mac=?', (_sMAC,)).fetchone()
                fNow = time.time()
                if oRow is not None:
                    if oRow[0]!=_sIP:
                        self.__oLogger.warning('[%s(%s)] Target MAC/IP has changed; MAC=%s, IP=%s' % (_sClient, _sStatus, _sMAC, _sIP))
                    if oRow[1]!=_sStatus:
                        bStatusChange = True
                        self.__oDatabase.execute(
                            'UPDATE si_monitor SET ip=?, host=?, status=?, change=?, message=?, progress=?, speed=?, heartbeat=? WHERE mac=?',
                            (_sIP, _sHost, _sStatus, fNow, _sMessage, _iProgress, _iSpeed, fNow, _sMAC)
                        )
                    else:
                        self.__oDatabase.execute(
                            'UPDATE si_monitor SET ip=?, host=?, status=?, message=?, progress=?, speed=?, heartbeat=? WHERE mac=?',
                            (_sIP, _sHost, _sStatus, _sMessage, _iProgress, _iSpeed, fNow, _sMAC)
                        )
                else:
                    bStatusChange = True
                    self.__oDatabase.execute(
                        'INSERT INTO si_monitor(mac, ip, host, status, change, message, progress, speed, heartbeat) VALUES(?,?,?,?,?,?,?,?,?)',
                        (_sMAC, _sIP, _sHost, _sStatus, fNow, _sMessage, _iProgress, _iSpeed, fNow)
                    )
            except Exception as e:
                raise RuntimeError('[%si(%s)] Failed to insert/update data in database; %s' % (_sClient, _sStatus, str(e)))

            # Run hooks
            try:
                if _sStatus in self.__dFileHooks:
                    sFileHook = self.__dFileHooks[_sStatus]
                    sStatusAction = 'change' if bStatusChange else 'update'
                    self.__oLogger.debug('[%s(%s)] Running hook; %s' % (_sClient, _sStatus, sFileHook))
                    if _sStatus=='init':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='start':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='pre-install':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='download':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage, str(_iProgress), str(_iSpeed)]
                    elif _sStatus=='install':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='post-install':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='complete':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    elif _sStatus=='error':
                        lArguments = [sFileHook, sStatusAction, _sMAC, _sIP, _sHost, _sMessage]
                    else:
                        raise Exception('WTF!?! Dude, get your statuses together!')
                    oPopen = subprocess.Popen(lArguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    sStdOut, sStdErr = oPopen.communicate()
                    if oPopen.returncode!=0:
                        self.__oLogger.warning('[%s(%s)] Hook return non-zero exit code; %d' % (_sClient, _sStatus, oPopen.returncode))
                    if sStdErr:
                        self.__oLogger.debug('[%s(%s)] %s' % (_sClient, _sStatus, sStdErr.strip('\n')))
            except Exception as e:
                raise RuntimeError('[%s(%s)] Failed to execute hook; %s' % (_sClient, _sStatus, str(e)))

        finally:
            if self.__oLockProcess: self.__oLockProcess.release()


    def query(self, _sKey=None, _sValue=None, _sClient='n/a'):
        """
        Query target(s) status.
        """

        # Validation
        if not _sKey in (None, 'mac', 'ip', 'host', 'status'):
            raise RuntimeError('[%s] Invalid query key; %s' % (_sClient, _sKey))

        # Initialization
        if self.__oDatabase is None: self.__initDatabase()

        # Query
        self.__oLogger.debug('[%s] Querying target(s) status; %s=%s' % (_sClient, _sKey, _sValue))
        aRows = []
        sSQL = 'SELECT mac, ip, host, status, change, message, progress, speed, heartbeat, heartbeat-change AS elapsed FROM si_monitor'
        if _sKey is None or _sValue is None: 
            oCursor = self.__oDatabase.execute(sSQL)
        else:
            if _sKey=='mac':
                _sValue = _sValue.upper()
            elif _sKey=='ip':
                _sValue = _sValue.lower()
            oCursor = self.__oDatabase.execute(sSQL+' WHERE %s=?' % _sKey, (_sValue,))
        oRow=oCursor.fetchone()
        while oRow:
            aRows.append(dict(zip(oRow.keys(),oRow)))
            oRow=oCursor.fetchone()
        return aRows
