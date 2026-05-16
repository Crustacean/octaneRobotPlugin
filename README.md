# Octane Robot Plugin Embiti

Robot Framework listener that updates ALM Octane child runs for tests in an existing suite run.

## How mapping works

Each Robot test uses a stable tag:

```robotframework
[Tags]    octane_tag:LOGIN_SMOKE_001
```

The matching ALM Octane test case must have the same value as a user tag:

```text
LOGIN_SMOKE_001
```

At runtime, the user provides only the current suite run ID. The listener reads the suite run, discovers child runs, reads the linked Octane tests and their user tags, and updates only matching child runs.

Unmatched Robot tests continue running and are reported in the final reconciliation summary. Octane child runs that were not matched are left untouched for manual update.

## Required environment variables

```bash
export OCTANE_BASE_URL="https://octane.example.com"
export OCTANE_SHARED_SPACE_ID="1001"
export OCTANE_WORKSPACE_ID="2002"
export OCTANE_CLIENT_ID="client-id"
export OCTANE_CLIENT_SECRET="client-secret"
export OCTANE_SUITE_RUN_ID="123456"
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

## Run Robot with the listener

```bash
robot --listener octane_robot_plugin_embiti.listener.OctaneRobotListener path/to/tests
```

To pass the suite run ID as a listener argument instead of an environment variable:

```bash
robot --listener octane_robot_plugin_embiti.listener.OctaneRobotListener:123456 path/to/tests
```

## Local tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
