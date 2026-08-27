# benchmark/fixtures/compliant/

CloudFormation templates that create AWS resources configured *correctly* (encrypted,
least-privilege, monitored, etc.) for each service under test. Used as the "should not flag"
side of scenarios — agents are expected to leave these resources alone.

Deployed/torn down via [`../deploy.sh`](../deploy.sh). See [../README.md](../README.md) for
prerequisites and usage.
