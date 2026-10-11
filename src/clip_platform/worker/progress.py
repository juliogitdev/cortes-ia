"""Measured job progress with a conservative, stage-local ETA."""
import math
import time


class ProgressReporter:
    def __init__(self, store, job_id, owner, clock=None):
        self.store = store
        self.job_id = job_id
        self.owner = owner
        self.clock = clock or time.monotonic
        self.stage = None
        self.stage_start = None
        self.stage_base = 0.0
        self.last_write = -math.inf
        self.last_progress = -1.0

    def update(self, stage, progress, stage_progress=None, *, force=False):
        now = self.clock()
        progress = min(.999, max(0.0, float(progress)))
        changed = stage != self.stage
        if changed:
            self.stage = stage
            self.stage_start = now
            self.stage_base = progress
        progress = max(progress, self.last_progress)
        eta = None
        stage_elapsed = now - self.stage_start
        stage_advance = progress - self.stage_base
        if stage_elapsed >= 10 and stage_advance >= .01:
            rate = stage_advance / stage_elapsed
            estimate = (1 - progress) / rate
            if math.isfinite(estimate) and 0 <= estimate <= 24 * 60 * 60:
                eta = estimate
        if not (force or changed or progress - self.last_progress >= .02 or now - self.last_write >= 5):
            return
        self.store.set_progress(self.job_id, self.owner, stage, progress,
            stage_progress, eta)
        self.last_write = now
        self.last_progress = progress
