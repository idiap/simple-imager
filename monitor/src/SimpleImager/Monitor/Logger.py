# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class SI_Monitor_Logger:
    """
    Simple Imager Monitor logger.

    This class is used to redirect the standard log output (sys.stdout or
    sys.stderr) to another destination; e.g. syslog.

    A logging function must be provided  at instantiation time. This user-
    provided function is responsible to feed each log *line* to the proper
    destination.

    Once instantiated, the logger object is "activated" by re-defining the
    required output; e.g. sys.stderr = SI_Monitor_Logger(myLoggingFunction)
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _fnLog):
        """
        Constructor.
        """

        # Properties
        # ... user-provided logging function
        self.__fnLog = _fnLog
        # ... (line) buffer
        self.__sBuffer = ''


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def flush(self):
        """
        Flush the (line) buffer to the user-provided logging function.
        """

        if self.__sBuffer:
            self.__fnLog(self.__sBuffer)
            self.__sBuffer = ''


    def write(self, _s):
        """
        Write provided string to our buffer.
        The (line) buffer is flushed to the user-provided logging function on each
        new line (\\n).
        WARNING: New line characters (\\n) are NOT passed to the user-provided
                 logging function!
        """

        while _s:
            i = _s.find('\n')
            if i < 0:
                self.__sBuffer += _s
                break
            self.__sBuffer += _s[:i]
            if self.__sBuffer:
                self.__fnLog(self.__sBuffer)
                self.__sBuffer = ''
            _s = _s[i+1:]


    def writelines(self, _lsLines):
        """
        Write provided (strings) list as independent lines.
        """

        for sLine in _lsLines:
            self.write(sLine.rstrip('\n')+'\n')
