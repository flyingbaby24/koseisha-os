"""Rate limiting: refuse cheaply, forget cleanly, never trust a header blindly."""

from __future__ import annotations

import unittest

from api.rate_limit import RateLimiter, client_key


class Clock:
    """A hand-cranked clock; a limiter tested against real time is a flaky test."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RateLimiterTests(unittest.TestCase):
    def test_a_zero_rate_disables_the_limiter(self) -> None:
        limiter = RateLimiter(rate=0, burst=0, now=Clock())
        for _ in range(1000):
            allowed, _ = limiter.allow("a")
            self.assertTrue(allowed)

    def test_the_burst_is_allowed_then_refused(self) -> None:
        clock = Clock()
        limiter = RateLimiter(rate=1, burst=3, now=clock)

        self.assertEqual([limiter.allow("a")[0] for _ in range(3)], [True, True, True])
        allowed, retry_after = limiter.allow("a")
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_tokens_refill_over_time(self) -> None:
        clock = Clock()
        limiter = RateLimiter(rate=2, burst=2, now=clock)

        limiter.allow("a")
        limiter.allow("a")
        self.assertFalse(limiter.allow("a")[0])

        clock.advance(0.5)  # 2/s -> one token
        self.assertTrue(limiter.allow("a")[0])

    def test_refill_never_exceeds_the_burst(self) -> None:
        clock = Clock()
        limiter = RateLimiter(rate=5, burst=2, now=clock)
        clock.advance(3600)  # a long quiet period

        self.assertTrue(limiter.allow("a")[0])
        self.assertTrue(limiter.allow("a")[0])
        self.assertFalse(limiter.allow("a")[0])

    def test_clients_have_independent_buckets(self) -> None:
        clock = Clock()
        limiter = RateLimiter(rate=1, burst=1, now=clock)

        self.assertTrue(limiter.allow("a")[0])
        self.assertFalse(limiter.allow("a")[0])
        # One noisy client must not refuse everyone else.
        self.assertTrue(limiter.allow("b")[0])

    def test_retry_after_is_a_usable_estimate(self) -> None:
        clock = Clock()
        limiter = RateLimiter(rate=2, burst=1, now=clock)
        limiter.allow("a")
        _, retry_after = limiter.allow("a")

        clock.advance(retry_after)
        self.assertTrue(limiter.allow("a")[0])

    def test_idle_buckets_are_forgotten(self) -> None:
        # Otherwise a stream of distinct addresses is a slow memory leak that
        # only appears in production.
        clock = Clock()
        limiter = RateLimiter(rate=1, burst=1, now=clock)

        for index in range(50):
            limiter.allow(f"client-{index}")
        self.assertEqual(limiter.tracked, 50)

        clock.advance(3600)
        limiter.allow("someone-new")
        self.assertLessEqual(limiter.tracked, 2)

    def test_a_sweep_does_not_forgive_a_client_still_over_its_limit(self) -> None:
        # The sweep may only drop buckets that have refilled. A slow rate keeps
        # this one part-empty across the sweep, so forgetting it would hand a
        # blocked client a full bucket for free.
        clock = Clock()
        limiter = RateLimiter(rate=0.01, burst=5, now=clock)  # refills in 500 s
        for _ in range(5):
            limiter.allow("busy")

        clock.advance(61)  # long enough to trigger a sweep, far short of a refill
        limiter.allow("other")

        self.assertFalse(limiter.allow("busy")[0])

    def test_a_refilled_bucket_may_be_forgotten_safely(self) -> None:
        # The other half of the rule: a full bucket is indistinguishable from a
        # new one, so dropping it changes nothing a client can observe.
        clock = Clock()
        limiter = RateLimiter(rate=1, burst=5, now=clock)
        for _ in range(5):
            limiter.allow("bursty")

        clock.advance(61)  # 5 s would have been enough to refill
        limiter.allow("other")

        self.assertTrue(limiter.allow("bursty")[0])


class ClientKeyTests(unittest.TestCase):
    def test_uses_the_socket_address_by_default(self) -> None:
        # X-Forwarded-For is client-controlled: trusting it unasked would let
        # anyone forge their way into a fresh bucket.
        self.assertEqual(client_key("10.0.0.1", "1.2.3.4", trust_proxy=False), "10.0.0.1")

    def test_uses_the_forwarded_client_when_told_to(self) -> None:
        self.assertEqual(
            client_key("10.0.0.1", "1.2.3.4, 10.0.0.9", trust_proxy=True), "1.2.3.4"
        )

    def test_falls_back_when_nothing_is_known(self) -> None:
        self.assertEqual(client_key(None, None, trust_proxy=True), "unknown")

    def test_an_empty_forwarded_header_falls_back_to_the_socket(self) -> None:
        self.assertEqual(client_key("10.0.0.1", "   ", trust_proxy=True), "10.0.0.1")


if __name__ == "__main__":
    unittest.main()
