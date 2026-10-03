from simple_pid import PID


class AntiWindupPID(PID):
    """simple_pid's PID with clamping anti-windup.

    simple_pid only clamps the integral term to the output range, so while the output is
    saturated (a long climb to temperature) the integral still climbs to its limit and then
    holds the output at the limit until the temperature has overshot. Here, in a step that
    would leave the output saturated in the direction of the error, the integral grows only as
    far as it takes to reach the limit, and never shrinks for being saturated.

    It used to roll the whole step back instead. With ~10 s passes one step of integral is
    large (Ki 0.1 x 78 degrees x 10 s = 78), so from cold the integral never grew at all: the
    output sat at the proportional term (78.25 on the Pi) and the blower, which needs more than
    99, never came on during warm-up."""

    def __call__(self, input_, dt=None):
        before = self._integral
        output = super().__call__(input_, dt)
        if output is None or not self.auto_mode:
            return output
        proportional, integral, derivative = self.components
        low, high = self.output_limits
        error = self.setpoint - input_
        if high is not None and proportional + integral + derivative > high and error > 0:
            self._integral = max(before, min(integral, high - proportional - derivative))
        elif low is not None and proportional + integral + derivative < low and error < 0:
            self._integral = min(before, max(integral, low - proportional - derivative))
        else:
            return output
        output = proportional + self._integral + derivative
        if high is not None:
            output = min(output, high)
        if low is not None:
            output = max(output, low)
        self._last_output = output
        return output
