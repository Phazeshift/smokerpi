from simple_pid import PID


class AntiWindupPID(PID):
    """simple_pid's PID with conditional-integration anti-windup.

    simple_pid only clamps the integral term to the output range, so while the output is
    saturated (a long climb to temperature) the integral still climbs to its limit and then
    holds the output at the limit until the temperature has overshot. Here the integral is not
    allowed to grow in a step that leaves the output saturated in the direction of the error."""

    def __call__(self, input_, dt=None):
        before = self._integral
        output = super().__call__(input_, dt)
        if output is None or not self.auto_mode:
            return output
        proportional, integral, derivative = self.components
        low, high = self.output_limits
        unsaturated = proportional + integral + derivative
        error = self.setpoint - input_
        if (high is not None and unsaturated > high and error > 0) or \
                (low is not None and unsaturated < low and error < 0):
            self._integral = before
            output = proportional + before + derivative
            if high is not None:
                output = min(output, high)
            if low is not None:
                output = max(output, low)
            self._last_output = output
        return output
