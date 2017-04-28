"""
Vesper Test Windows service.

This script implements a simple test service named "VesperTest". The
service just logs some events via the Windows Service Control Manager
(SCM). The events can be viewed with the Windows Event Viewer control
panel. The script can be used to install, start, stop, and remove the
service.

The script is best deployed as a PyInstaller executable. Such an executable
is a self-contained directory (in PyInstaller lingo, a "one-folder program")
containing an executable version of the script, a Python interpreter, and
the various Python packages and DLLs on which the script depends.

To install the VesperTest service, issue the command:

    vesper_test_service.exe install
    
from the directory containing the executable in a Windows command prompt.
The command prompt must be run as administrator. The service can subsequently
be started, stopped, or removed with the commands (again, run as
administrator):

    vesper_test_service.exe start
    vesper_test_service.exe stop
    vesper_test_service.exe remove

You can see detailed help for the executable with the command:

    vesper_test_service.exe help

Once the service is installed, you can also start and stop it from the
Windows Services control panel, and view events logged by the service
with the Windows Event Viewer control panel.
"""


from logging import Formatter, Handler
import logging
import sys
 
import servicemanager
import win32event
import win32service
import win32serviceutil


_logger = logging.getLogger(__name__)


def _main():
    
    _initialize_logging()
    
    if len(sys.argv) == 1 and \
            sys.argv[0].endswith('.exe') and \
            not sys.argv[0].endswith(r'win32\VesperTestService.exe'):
        # invoked as non-pywin32-VesperTestService.exe executable
        # without arguments
        
        # We assume here that we were invoked by the Windows Service
        # Control Manager (SCM) as a PyInstaller executable in order to
        # start our service.
        
        # Initialize the service manager and start our service.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(_TestService)
        servicemanager.StartServiceCtrlDispatcher()
    
    else:
        # invoked with arguments, or without arguments as a regular
        # Python script
  
        # We support a "help" command that isn't supported by
        # `win32serviceutil.HandleCommandLine` so there's a way for
        # users who run this script from a PyInstaller executable to see
        # help. `win32serviceutil.HandleCommandLine` shows help when
        # invoked with no arguments, but without the following that would
        # never happen when this script is run from a PyInstaller
        # executable since for that case no-argument invocation is handled
        # by the `if` block above.
        if len(sys.argv) == 2 and sys.argv[1] == 'help':
            sys.argv = sys.argv[:1]
             
        win32serviceutil.HandleCommandLine(_TestService)


def _initialize_logging():
    
    # Create handler that logs messages through the Windows SCM.
    handler = _ScmHandler()
    formatter = Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to root logger.
    logger = logging.getLogger()
    logger.addHandler(handler)
    
    # Set root logger level.
    logger.setLevel(logging.INFO)
    

class _ScmHandler(Handler):
    
    """
    Logging handler that logs a message via the Windows Service Control
    Manager (SCM). Such messages can be viewed with the Windows Event
    Viewer.
    """
    
    def emit(self, record):
        
        message = self.format(record)
        level = record.levelno
        
        if level >= logging.ERROR:
            servicemanager.LogErrorMsg(message)
            
        elif level >= logging.WARNING:
            servicemanager.LogWarningMsg(message)
            
        else:
            servicemanager.LogInfoMsg(message)
        
    
class _TestService(win32serviceutil.ServiceFramework):
    
    
    _svc_name_ = 'VesperTest'
    _svc_display_name_ = 'Vesper Test'
    _svc_description_ = 'Vesper test service.'
 
 
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
 
 
    def GetAcceptedControls(self):
        result = win32serviceutil.ServiceFramework.GetAcceptedControls(self)
        result |= win32service.SERVICE_ACCEPT_PRESHUTDOWN
        return result

    
    def SvcDoRun(self):
        _logger.info('Test service is starting.')
        self._wait_for_stop_request()
        _logger.info('Test service is stopping.')
        
        
    def _wait_for_stop_request(self):
        
        while True:
               
            result = win32event.WaitForSingleObject(self._stop_event, 5000)
              
            if result == win32event.WAIT_OBJECT_0:
                # stop requested
                  
                break


    def SvcOtherEx(self, control, event_type, data):
        
        # See the MSDN documentation for "HandlerEx callback" for a list
        # of control codes that a service can respond to.
        #
        # We respond to `SERVICE_CONTROL_PRESHUTDOWN` instead of
        # `SERVICE_CONTROL_SHUTDOWN` since it seems that we can't log
        # info messages when handling the latter.
        
        if control == win32service.SERVICE_CONTROL_PRESHUTDOWN:
            _logger.info('Received a pre-shutdown notification.')
            self._stop()
        else:
            _logger.info(
                'Received an event: code={}, type={}, data={}.'.format(
                    control, event_type, data))
    

    def _stop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)


    def SvcStop(self):
        self._stop()
 

if __name__ == '__main__':
    _main()
