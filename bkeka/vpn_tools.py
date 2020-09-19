import platform
from subprocess import Popen, PIPE, TimeoutExpired
from time import sleep
from os import O_NONBLOCK, read, path, listdir
import bot_logger
from random import shuffle

# Platform specific imports for openvpn process
# We need to set the stdout of the openvpn process to non blocking
# otherwise reading from the pipe output woud cause the whole thing
# to block
if platform.system().lower().startswith('win'):
    # Windows is 'phtupid' and doesn't know about fcntl
    import msvcrt
    from ctypes import windll, byref, wintypes, GetLastError, WinError
    from ctypes.wintypes import HANDLE, DWORD, POINTER, BOOL
    LPDWORD = POINTER(DWORD)
    PIPE_NOWAIT = wintypes.DWORD(0x00000001)
elif platform.system().lower().startswith('lin') or platform.system().lower().startswith('dar'):
    from fcntl import fcntl, F_GETFL, F_SETFL

SUCCESS_MESSAGE = "Initialization Sequence Completed"
OPENVPN_COMMAND = "openvpn"
VPN_SUCCESS = 1
VPN_ERROR = 0
MAX_RETRIES = 255

# Global variable for VPN subprocess
openvpn_process = None


class OpenVPNProcessExceptions(Exception):
    """Raised for different internal errors"""
    pass


def pipe_no_wait(process):
    """ pipefd is a integer as returned by os.pipe """
    if platform.system().lower().startswith('win'):
        pipefd = process.stdout.fileno()
        SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
        SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
        SetNamedPipeHandleState.restype = BOOL

        h = msvcrt.get_osfhandle(pipefd)

        res = windll.kernel32.SetNamedPipeHandleState(h, byref(PIPE_NOWAIT), None, None)
        if res == 0:
            print(WinError())
            return False
        return True
    elif platform.system().lower().startswith('lin') or platform.system().lower().startswith('dar'):
        # set the O_NONBLOCK flag of openvpn_process.stdout file descriptor:
        flags = fcntl(process.stdout, F_GETFL)  # get current p.stdout flags
        fcntl(process.stdout, F_SETFL, flags | O_NONBLOCK)
        return True


def openvpn_start_subprocess(config_file, credentials_file):
    # Connect to vpn
    print("----->", config_file)
    process = Popen(['sudo', OPENVPN_COMMAND, config_file], stdout=PIPE, stderr=PIPE, shell=False)
    if not pipe_no_wait(process):
        raise OpenVPNProcessExceptions("Failed to set file descriptor non blocking")

    return process


def get_config_file(vpn_config_dir):
    vpn_config_files = [path.abspath(path.join(vpn_config_dir, x)) for x in listdir(vpn_config_dir)]
    for x in vpn_config_files:
        if x.endswith('.ovpn'):
            return x
    return None


def openvpn_close_connection():
    global openvpn_process
    # if openvpn_process is not None and openvpn_process.poll() is not None:
    #    openvpn_process.kill()
    #    openvpn_process = None
    if openvpn_process is not None:
        prc = Popen(['sudo', 'killall', OPENVPN_COMMAND], stdout=PIPE, stderr=PIPE, shell=False)
        try:
            outs, errs = prc.communicate(timeout=5)
        except TimeoutExpired:
            prc.kill()
            outs, errs = prc.communicate()
        openvpn_process = None


def openvpn_connect(vpn_config_dir, vpn_credentials_file, disable_logging):
    global openvpn_process

    logger = bot_logger.get_logger(__name__ + '.log', __name__ + '.log')
    vpn_config_file = None
    init_success = False
    retry_no = 0

    while retry_no < MAX_RETRIES:
        # Debug openvpn output
        vpn_output = ""
        # Close any previous openvpn connection
        openvpn_close_connection()
        # Get config files path
        vpn_config_file = get_config_file(vpn_config_dir)

        logger.info(
            "Trying to connect to vpn with config '%s' and credentials '%s'."
            % (vpn_config_file, vpn_credentials_file))
        # Start vpn subprocess
        openvpn_process = openvpn_start_subprocess(vpn_config_file, vpn_credentials_file)
        # Let the openvpn process write output
        sleep(30)

        # get the output
        while True:
            try:
                vpn_output = read(openvpn_process.stdout.fileno(), 100000)
                logger.info(str(vpn_output))
                sleep(1)
                # If success message was read from output, everything is ok
                if SUCCESS_MESSAGE in str(vpn_output):
                    logger.info("Initialization Complete.")
                    bot_logger.close_logger(logger, disable_logging)
                    return VPN_SUCCESS
                # If line is empty, the process exited
                if vpn_output == b'':
                    break
            except OSError:
                # the os throws an exception if there is no data
                logger.exception("Done reading data from OpenVPN process.")
                break

        retry_no = retry_no + 1

    logger.info("Failed to start vpn")
    bot_logger.close_logger(logger, disable_logging)

    return VPN_ERROR
