# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 1999-2010 Brian Elliott Finley [SystemImager]
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import errno
import socket
import sys
import threading

# Simple Imager
from SimpleImager.Monitor import \
    SI_Monitor_Daemon


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class SI_Monitor_DaemonLegacy(SI_Monitor_Daemon):
    """
    Simple Imager Monitor daemon; (SystemImager) legacy protocol
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self):
        """
        Constructor.
        """

        # Parent
        SI_Monitor_Daemon.__init__(self)

        # Properties
        # ... runtime
        self.__oSocket = None


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    # Initialization
    #------------------------------------------------------------------------------

    def _initArgumentParser(self):
        """
        Creates the arguments parser (and help generator).
        """

        # Parent
        SI_Monitor_Daemon._initArgumentParser(self)

        # Add arguments to parser

        # ... bind address
        self._oArgumentParser.add_argument(
            '-B', '--bind', type=str,
            metavar='<bind-address>',
            default='*',
            help='Specific IP address to bind the daemon to (default:*)')

        # ... port
        self._oArgumentParser.add_argument(
            '-P', '--port', type=int,
            metavar='<tcp-port>',
            default=8181,
            help='TCP port to have the daemon listen on (default:8181)')


    # Service
    #------------------------------------------------------------------------------

    def _run(self):
        """
        Run the (daemon/foreground) service; returns a non-zero exit code in case of failure.
        """

        # Parent
        iReturn = SI_Monitor_Daemon._run(self)
        if iReturn:
            return iReturn

        # Open TCP socket and listen on configured address/port
        try:
            if self._oArguments.bind=='*':
                self._oArguments.bind = ''
            self.__oSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__oSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__oSocket.bind((self._oArguments.bind, self._oArguments.port))
            self.__oSocket.listen(5)
        except Exception as e:
            self._oLogger.error('Failed to open network socket; %s' % str(e))
            return errno.EIO

        # Loop through client connections
        # WARNING: Multi-threading!
        while True:

            # Stop ?
            if self._bStop:
                break

            # Accept client connections
            try:
                oConnection, tAddress = self.__oSocket.accept()
                oConnection.settimeout(10)
                sThreadName = '%s:%d' % tAddress[:2]
                oThread = threading.Thread(name=sThreadName, target=self.__connection, args=(oConnection, tAddress))
                oThread.start()
            except socket.error as (iError, sError):
                if iError!=errno.EINTR:
                    self._oLogger.error('Socket error while waiting for client connections; %s' % sError)
                    return errno.EIO
            except Exception as e:
                self._oLogger.error('Unexpected error while waiting for client connections; %s' % str(e))
                return errno.EIO

        # Close TCP socket
        try:
            self.__oSocket.shutdown(socket.SHUT_RDWR)
            self.__oSocket.close()
        except Exception as e:
            self._oLogger.error('Failed to close network socket; %s' % str(e))
            return errno.EIO

        # Done
        self._oLogger.info('Done')
        return 0


    def __connection(self, _oConnection, _tAddress):
        """
        Handle client connection; returns a non-zero exit code in case of failure.
        """

        sClient = '%s:%d' % _tAddress[:2]
        self._oLogger.debug('[%s] New client connection' % sClient)

        # Receive client data
        byData = b''
        while True:
            try:
                byRecv = _oConnection.recv(1024)
                if not byRecv: break
                byData += byRecv
                self._oLogger.debug('[%s] Client data (chunk) received; Chunk=%s' % (sClient, str(byRecv).strip('\n')))
                if len(byData)>4096:
                    raise RuntimeError('Received client data exceed 4096 bytes')
            except socket.error as (iError, sError):
                _oConnection.close()
                if iError!=errno.EINTR:
                    self._oLogger.error('[%s] Socket error while receiving client data; %s' % (sClient, sError))
                    return errno.EIO
                return 0
            except Exception as e:
                _oConnection.close()
                self._oLogger.error('[%s] Unexpected error while receiving client data; %s' % (sClient, str(e)))
                return errno.EIO
        _oConnection.close()
        self._oLogger.debug('[%s] Client disconnected' % sClient)

        # Process data
        return self.__process(_tAddress, byData)


    def __process(self, _tAddress, _byData):
        """
        Process client data; returns a non-zero exit code in case of failure.
        """

        sClient = '%s:%d' % _tAddress[:2]
        self._oLogger.debug('[%s] Processing client data; Data=%s' % (sClient, str(_byData).strip('\n')))

        # Data (split 'key1=value1:key2:...' string in {key1: value1, key2: '', ...} dictionary)
        # NOTE: valid keys are: mac, ip, host, cpu, ncpus, kernel, mem, os, tmpfs, time, status, speed, first_timestamp, error, message
        try:
            dData = {k.strip():v.strip() for k,v in [kv.split('=',1) if kv.find('=')>=0 else [kv,''] for kv in str(_byData).split(':')]}
        except Exception as e:
            self._oLogger.error('[%s] Invalid data (key/value pairs); Data=%s' % (sClient, str(_byData).strip('')))
            return errno.EINVAL

        # Validation
        # NOTE: we store only installation status/progress information; other data are out of the scope of our purpose
        if not 'mac' in dData or not dData['mac']:
            self._oLogger.error('[%s] Missing/empty MAC address' % sClient)
            return errno.EINVAL
        if not 'status' in dData or not dData['status']:
            self._oLogger.debug('[%s] Missing/empty status; ignoring data' % sClient)
            return 0

        # Parse data
        try:
            sMAC = dData['mac'].replace('.', ':')
            sIP = _tAddress[0]
            try:
                sHost = socket.gethostbyaddr(sIP)[0]
            except Exception as e:
                sHost = 'n/a'
            iStatus = int(dData['status'])
            sMessage = dData['message'].replace('^', ':') if 'message' in dData else ''
            iProgress = -1
            iSpeed = -1
            if iStatus<0:
                sStatus = 'error'
                if len(sMessage): sMessage += ' '
                sMessage += '[%d]' % iStatus
            elif 'first_timestamp' in dData:
                sStatus = 'start'
            elif iStatus>=300:
                sStatus='complete'
            elif iStatus>=200:
                sStatus = 'install'
                if iStatus>200:
                    iProgress = iStatus-100
            elif iStatus>101:
                sStatus='complete'
            elif iStatus>100:
                sStatus='install'
            else:
                sStatus = 'download'
                iProgress = iStatus
                if 'speed' in dData:
                    iSpeed = int(dData['speed'])
        except Exception as e:
            self._oLogger.error('[%s] Invalid data (parsing error); Data=%s; %s' % (sClient, str(_byData).strip(''), str(e)))
            return errno.EINVAL
        self._oLogger.debug('[%s] Data parsed; MAC=%s, IP=%s, Host=%s, Status=%s, Message=%s, Progress=%d, Speed=%d' % (sClient, sMAC, sIP, sHost, sStatus, sMessage, iProgress, iSpeed))

        # Done; update status
        return self._update(sMAC, sIP, sHost, sStatus, sMessage, iProgress, iSpeed, sClient)
