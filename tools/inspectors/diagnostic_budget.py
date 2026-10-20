"""BC01–05: local monotonic budget and cooperative stop/publication boundary."""

import math
import threading


class BudgetStopped(ValueError):
    """A fixed local reason, never text originating in the remote payload."""


class DiagnosticSessionBudget:
    """One owner calls begin/checkpoint/remaining/publish; any thread may stop.

    The trusted clock must be fast and nonreentrant. publish's callback only
    commits owner state; it must not call external code or reenter this budget.
    """

    def __init__(self, clock):
        self._clock = clock
        self._lock = threading.Lock()
        self._reason = ""
        self._last = self._deadline = None
        self._active = False

    @property
    def reason(self):
        with self._lock:
            return self._reason

    def stop(self, reason):
        with self._lock:
            if not self._reason:
                self._reason = reason
            return self._reason

    def _fail(self, reason):
        # Called under the lock after _now has ruled out an existing stop.
        self._reason = reason
        raise BudgetStopped(self._reason)

    def _now(self):
        if self._reason:
            raise BudgetStopped(self._reason)
        try:
            now = self._clock()
            valid = type(now) in (int, float) and math.isfinite(now)
        except (ValueError, TypeError, OverflowError):
            valid = False
        if not valid or (self._last is not None and now < self._last):
            self._fail("clock_invalid")
        self._last = now
        return now

    def begin(self, *, initial):
        with self._lock:
            now = self._now()
            if self._active:
                self._fail("reentrant")
            self._deadline = now + (5 if initial else 2)
            if not math.isfinite(self._deadline) or self._deadline <= now:
                self._fail("clock_invalid")
            self._active = True

    def _remaining(self):
        now = self._now()
        if not self._active:
            self._fail("budget_inactive")
        if now >= self._deadline:
            self._fail("deadline")
        return self._deadline - now

    def checkpoint(self):
        with self._lock:
            self._remaining()

    def remaining(self):
        with self._lock:
            return self._remaining()

    def publish(self, commit):
        with self._lock:
            self._remaining()
            result = commit()
            self._active = False
            return result
