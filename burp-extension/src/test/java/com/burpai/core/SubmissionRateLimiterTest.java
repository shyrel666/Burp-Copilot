package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class SubmissionRateLimiterTest {

    private static final class FakeClock implements SubmissionRateLimiter.Clock {
        long now = 0;

        @Override
        public long nanoTime() {
            return now;
        }
    }

    @Test
    void allowsAtMostCapacityInOneWindow() {
        FakeClock clock = new FakeClock();
        SubmissionRateLimiter limiter = new SubmissionRateLimiter(10, clock);

        int granted = 0;
        for (int i = 0; i < 25; i++) {
            if (limiter.tryAcquire()) {
                granted++;
            }
        }
        assertEquals(10, granted);
    }

    @Test
    void refillsOverTime() {
        FakeClock clock = new FakeClock();
        SubmissionRateLimiter limiter = new SubmissionRateLimiter(10, clock);

        for (int i = 0; i < 10; i++) {
            assertTrue(limiter.tryAcquire());
        }
        assertFalse(limiter.tryAcquire());

        // Advance one full second -> bucket fully refilled.
        clock.now += 1_000_000_000L;
        int granted = 0;
        for (int i = 0; i < 15; i++) {
            if (limiter.tryAcquire()) {
                granted++;
            }
        }
        assertEquals(10, granted);
    }

    @Test
    void partialRefillGrantsProportionalTokens() {
        FakeClock clock = new FakeClock();
        SubmissionRateLimiter limiter = new SubmissionRateLimiter(10, clock);
        for (int i = 0; i < 10; i++) {
            limiter.tryAcquire();
        }
        // 100ms -> ~1 token for a 10/s bucket
        clock.now += 100_000_000L;
        assertTrue(limiter.tryAcquire());
        assertFalse(limiter.tryAcquire());
    }
}
