*** Test Cases ***
Login Smoke Test
    [Tags]    octane_tag:LOGIN_SMOKE_001
    Log    This result will be synced to the Octane child run with matching user tag.

Checkout Smoke Test
    [Tags]    octane_tag:CHECKOUT_SMOKE_001
    Log    This result will be synced to the Octane child run with matching user tag.

Local Only Test
    Log    This Robot test is not synced to Octane because it has no octane_tag.
