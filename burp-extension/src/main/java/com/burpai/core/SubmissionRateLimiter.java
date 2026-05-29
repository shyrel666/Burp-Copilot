package com.burpai.core;

/**
 * Token-bucket rate limiter capping auto-submissions to avoid overwhelming the
 * backend. Default capacity and refill rate are 10 tokens per second.
 *
 * A {@link Clock} is injectable so the limiter can be unit-tested deterministically.
 */
public final class SubmissionRateLimiter {
    public interface Clock {
        long nanoTime();
    }

    private static final int MAX_PER_SECOND = 10;
    private static final long ONE_SECOND_NANOS = 1_000_000_000L;

    private final int capacity;
    private final Clock clock;
    private double tokens;
    private long lastRefillNanos;

    public SubmissionRateLimiter() {
        this(MAX_PER_SECOND, System::nanoTime);
    }

    public SubmissionRateLimiter(int capacity, Clock clock) {
        this.capacity = capacity;
        this.clock = clock;
        this.tokens = capacity;
        this.lastRefillNanos = clock.nanoTime();
    }

    public synchronized boolean tryAcquire() {
        refill();
        if (tokens >= 1.0) {
            tokens -= 1.0;
            return true;
        }
        return false;
    }

    private void refill() {
        long now = clock.nanoTime();
        long elapsed = now - lastRefillNanos;
        if (elapsed <= 0) {
            return;
        }
        double refillRatePerNano = (double) capacity / ONE_SECOND_NANOS;
        tokens = Math.min(capacity, tokens + elapsed * refillRatePerNano);
        lastRefillNanos = now;
    }
}
