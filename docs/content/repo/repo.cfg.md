# repo.cfg.md

This file contains repository-wide configuration.

Example:
```cfg
[DEFAULT]
password_provider = pass

[password_providers]
pass = pass show {}
```

# Sections

## DEFAULT

This section allows you to define default values for certain options:

- `password_provider`: The name of the default [external password provider](/guide/secrets/#external-password-providers) to use. See the [password_providers](#password_providers) section for more info.

Example:
```cfg
[DEFAULT]
password_provider = pass
```

## password_providers

This section allows you to define external password providers that can be used instead of or in addition to the internal password generation. Each provider should have a name and a command, which will be interpolated with the identifier of the password to load.

Example:
```cfg
[password_providers]
pass = pass show {}
```

When a password is loaded from the `pass` provider, it will execute the following command: `pass show password_name`.
