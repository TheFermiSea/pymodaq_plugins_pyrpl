import pyrpl

class PyrplManager:
    """
    Manager for PyRPL functionalities.
    """

    def __init__(self):
        self.pyrpl = None

    def connect(self, hostname):
        """
        Connect to the Red Pitaya.
        """
        try:
            self.pyrpl = pyrpl.Pyrpl(hostname=hostname)
            return True
        except Exception as e:
            print(f"Failed to connect to PyRPL: {e}")
            return False

    def disconnect(self):
        """
        Disconnect from the Red Pitaya.
        """
        if self.pyrpl is not None:
            self.pyrpl.close()
            self.pyrpl = None

    def get_pid_modules(self):
        """
        Get a list of available PID modules.
        """
        if self.pyrpl is not None:
            return self.pyrpl.pids
        return []

    def get_pid(self, pid_name):
        """
        Get a PID module from PyRPL.
        """
        if self.pyrpl is not None:
            return getattr(self.pyrpl, pid_name)
        return None

    def set_pid_gains(self, pid_name, p, i, d):
        """
        Set the P, I, and D gains of a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            pid.p = p
            pid.i = i
            pid.d = d

    def enable_pid(self, pid_name, enable):
        """
        Enable or disable a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            pid.on = enable

    def get_pid_output(self, pid_name):
        """
        Get the output of a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            return pid.output
        return 0

    def get_pid_input(self, pid_name):
        """
        Get the input of a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            return pid.input
        return 0

    def get_pid_setpoint(self, pid_name):
        """
        Get the setpoint of a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            return pid.setpoint
        return 0

    def set_pid_setpoint(self, pid_name, setpoint):
        """
        Set the setpoint of a PID module.
        """
        pid = self.get_pid(pid_name)
        if pid is not None:
            pid.setpoint = setpoint
