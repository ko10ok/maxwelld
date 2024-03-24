"""
This module used for the vedro plugin integration for Maxwell Demon

Enabled plugin (in vedro.cfg) catches stage before tests run (StartupEvent) and before each test run (ScenarioRunEvent).

On each stage it starts testing environment required by selected tests.

Plugin communicate with maxwelld service container via http client - maxwelld/client
"""
