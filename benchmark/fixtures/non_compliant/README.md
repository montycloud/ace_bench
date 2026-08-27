# benchmark/fixtures/non_compliant/

CloudFormation templates that create AWS resources with deliberate misconfigurations
(disabled encryption/rotation, public access, missing alarms, overly permissive policies,
etc.) for each service under test. These are the resources scenarios expect agents to
correctly identify and flag — see [`../../gold_labels/`](../../gold_labels/) for the expected
findings per scenario.

Deployed/torn down via [`../deploy.sh`](../deploy.sh). See [../README.md](../README.md) for
prerequisites and usage.
