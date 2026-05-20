# Octane Robot Plugin Embiti

Robot Framework listeners for ALM Octane.

Two flows are available:

- `OctaneRobotListener`: updates existing automated child runs in an existing suite run.
- `OctaneTestResultsListener`: posts Robot results to Octane's `test-results` API so Octane creates/updates automated tests and automated runs.

## How mapping works

Each Robot test uses a stable tag:

```robotframework
[Tags]    octane_tag:LOGIN_SMOKE_001
```

The matching ALM Octane test case must have the same value as a user tag:

```text
LOGIN_SMOKE_001
```

At runtime, the user provides only the current suite run ID. The direct child-run listener reads the suite run, discovers child runs, reads the linked Octane tests and their user tags, and updates only matching automated child runs.

Unmatched Robot tests continue running and are reported in the final reconciliation summary. Octane child runs that were not matched, or child runs for manual tests, are left untouched for manual update.

## Common Environment Variables

```bash
export OCTANE_BASE_URL="https://octane.example.com"
export OCTANE_SHARED_SPACE_ID="1001"
export OCTANE_WORKSPACE_ID="2002"
export OCTANE_CLIENT_ID="client-id"
export OCTANE_CLIENT_SECRET="client-secret"
```

Optional variables:

```bash
export OCTANE_TIMEOUT_SECONDS="30"
export OCTANE_VERIFY_SSL="true"
```

## Install locally

From this directory:

```bash
python3 -m pip install -e .
```

## Flow 1: Update Existing Automated Suite Child Runs

Use this when the Octane suite run already contains automated child runs.

This flow also requires:

```bash
export OCTANE_SUITE_RUN_ID="123456"
```

```bash
robot --listener octane_robot_plugin_embiti.listener.OctaneRobotListener path/to/tests
```

To pass the suite run ID as a listener argument instead of an environment variable:

```bash
robot --listener octane_robot_plugin_embiti.listener.OctaneRobotListener:123456 path/to/tests
```

## Flow 2: Inject Robot Results As Automated Tests

Use this when Octane only has manual/Gherkin tests or when you want Octane to create/update automated tests from Robot results.

`OCTANE_SUITE_RUN_ID` is not required for this flow.

```bash
robot --listener octane_robot_plugin_embiti.test_results_listener.OctaneTestResultsListener path/to/tests
```

Optional test-results settings:

```bash
export OCTANE_TEST_RESULTS_MODULE="/robot"
export OCTANE_TEST_RESULTS_CLASS="RobotFramework"
export OCTANE_TEST_RESULTS_RELEASE_NAME="_default_"
export OCTANE_TEST_RESULTS_REPORT_URL="https://ci.example.com/robot/log.html"
export OCTANE_TESTING_TOOL_TYPE="Robot Framework"
export OCTANE_TEST_FRAMEWORK="Robot Framework"
export OCTANE_TEST_RESULTS_WAIT_SECONDS="0"
```

Robot `octane_tag:<key>` values are sent as Octane `external_test_id` values when present. Octane identifies automated tests primarily by module, package, class, and name.

## Local tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
