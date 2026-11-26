#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for NLP lifecycle policy replacement."""

import unittest

from ai_platform.common.core.execution import RuntimePolicy
from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.provider import (
    NLPProviderConfigurationRuntime,
    NLPProviderConfigurationService,
)
from ai_platform.common.nlp.provider.lifecycle import NLPProviderLifecycle

from test_nlp_provider_execution_contract import (
    ContextAwareProvider,
    build_request,
)


class TestNLPPolicyReplacement(unittest.IsolatedAsyncioTestCase):

    async def test_configuration_policy_is_replaced_not_accumulated(self):
        registry = PluginRegistry()
        lifecycle = NLPProviderLifecycle(registry)

        provider = ContextAwareProvider()
        lifecycle.register(
            provider,
            policy=RuntimePolicy(
                max_threads=8,
                max_concurrency=4,
                timeout_seconds=30,
                queue_timeout_seconds=10,
            ),
        )

        runtime = NLPProviderConfigurationRuntime(
            NLPProviderConfigurationService(registry),
            lifecycle,
        )

        restrictive_configuration = {
            "provider_id": "aware",
            "engine": {"engine_name": "fake-engine"},
            "model": {"model_id": "fake-model", "language": "pl"},
            "runtime": {
                "device": "cpu",
                "threads": 2,
                "max_concurrency": 2,
                "timeout_seconds": 5,
                "queue_timeout_seconds": 2,
            },
        }

        relaxed_configuration = {
            "provider_id": "aware",
            "engine": {"engine_name": "fake-engine"},
            "model": {"model_id": "fake-model", "language": "pl"},
            "runtime": {
                "device": "cpu",
                "threads": 6,
                "max_concurrency": 3,
                "timeout_seconds": 20,
                "queue_timeout_seconds": 8,
            },
        }

        await runtime.initialize_from_configuration(
            restrictive_configuration,
            environ={},
        )

        await runtime.initialize_from_configuration(
            relaxed_configuration,
            environ={},
        )

        await lifecycle.analyze_with_context(
            "aware",
            build_request("policy-replacement"),
        )

        policy = provider.seen_context.policy

        self.assertEqual(policy.max_threads, 6)
        self.assertEqual(policy.max_concurrency, 3)
        self.assertEqual(policy.timeout_seconds, 20)
        self.assertEqual(policy.queue_timeout_seconds, 8)

        print("CONFIGURATION POLICY REPLACEMENT: OK")

    async def test_provider_policy_cannot_be_relaxed(self):
        registry = PluginRegistry()
        lifecycle = NLPProviderLifecycle(registry)

        provider = ContextAwareProvider()
        lifecycle.register(
            provider,
            policy=RuntimePolicy(
                max_threads=4,
                max_concurrency=2,
                timeout_seconds=15,
            ),
        )

        runtime = NLPProviderConfigurationRuntime(
            NLPProviderConfigurationService(registry),
            lifecycle,
        )

        await runtime.initialize_from_configuration(
            {
                "provider_id": "aware",
                "engine": {"engine_name": "fake-engine"},
                "model": {"model_id": "fake-model", "language": "pl"},
                "runtime": {
                    "device": "cpu",
                    "threads": 8,
                    "max_concurrency": 8,
                    "timeout_seconds": 60,
                },
            },
            environ={},
        )

        await lifecycle.analyze_with_context(
            "aware",
            build_request("provider-policy"),
        )

        policy = provider.seen_context.policy

        self.assertEqual(policy.max_threads, 4)
        self.assertEqual(policy.max_concurrency, 2)
        self.assertEqual(policy.timeout_seconds, 15)

        print("PROVIDER POLICY CANNOT BE RELAXED: OK")

    async def test_caller_policy_can_only_tighten(self):
        registry = PluginRegistry()
        lifecycle = NLPProviderLifecycle(registry)

        provider = ContextAwareProvider()
        lifecycle.register(
            provider,
            policy=RuntimePolicy(
                max_threads=8,
                max_concurrency=4,
                timeout_seconds=30,
            ),
        )

        await lifecycle.analyze_with_context(
            "aware",
            build_request("caller-policy"),
            policy=RuntimePolicy(
                max_threads=2,
                max_concurrency=1,
                timeout_seconds=5,
            ),
        )

        policy = provider.seen_context.policy

        self.assertEqual(policy.max_threads, 2)
        self.assertEqual(policy.max_concurrency, 1)
        self.assertEqual(policy.timeout_seconds, 5)

        print("CALLER POLICY ONLY TIGHTENS: OK")


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestNLPPolicyReplacement
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print(
        f"\nALL NLP POLICY REPLACEMENT TESTS PASSED: "
        f"{result.testsRun}/{result.testsRun}"
    )


if __name__ == "__main__":
    main()

