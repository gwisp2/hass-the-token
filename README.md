# The Token

Custom component for HomeAssistant that automatically adds deterministic long-lived access token for a user.
This component is intended to be used in development environments where you need to run some scripts that use HomeAssistant REST or WS API.

# Installation

Copy `custom_components/the_token` into your `custom_components` folder.

# Usage

To enable the component you need to add the following line in your `configuration.yaml`.

```
the_token:
```

Probably default configuration is sufficient for you. TheToken will scan for users and if there is only one user then a token will be generated.

The generated token will be exactly like this:
```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCIsImlhdCI6MTY0MDk5NTIwMCwiZXhwIjoxOTU2MzU1MjAwfQ.JDh_0PKh4DufWnmgdsZEH6zjZbnGWyRHSUlWxijAApI
```

You may also look into logs to find a token value.

# About long-lived access tokens

Long-lived access tokens are indeed base64-encoded signed JWT.
That JWT depends on:
1. Refresh token id
2. Access token creation instant `*`
3. Access token expiration instant `*`

`*` Creation and expiration instants for access and refresh tokens may be different. However, to achieve deterministic access tokens, TheToken uses refresh token creation/expiration instant. Also, a refresh token creation instant is fixed, by default it is 2022-01-01 00:00:00 UTC.

Refresh tokens are what HomeAssistant generates and stores when you ask for a long-lived access token. The access token itself is not stored. JWT signature and refresh token ID are used to check access tokens.

# Advanced configuration

Look at the [source code](custom_components/the_token/__init__.py) for configuration options.
Most likely you need a `username` option if you have several users.

```
the_token:
  username: admin
```