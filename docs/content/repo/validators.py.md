# Validators

Validators allow you to verify things within your bundlewrap repository.

<div class="alert alert-warning">
Validators must raise <code>bundlewrap.exceptions.ValidatorError</code> when
validating fails.
</div>

## Available validators

These validators are used within bundlewrap. You can define your own
validators and call them using `repo.run_validator(validator_name, **kwargs)`
in your repo. Bundlewrap will take care of only running a validator if
it actually exists.

<div class="alert alert-info">Validator functions will always get called
with named arguments.</div>

**`validate_bundlewrap_version(version)`**

Called each time the repository gets initialized (usually once per `bw`
invocation).

`version` The currently running version of bundlewrap (tuple of integers: `(5, 0, 2)`)

**`validate_secret_key(key)`**

Called once for each key in your [`.secrets.cfg`](../guide/secrets.md#secretscfg)
at the time when the secret is resolved. If validation fails, all secrets
which use this key will raise `FaultUnavailable`.

`key` The key that will get used to resolve the secret