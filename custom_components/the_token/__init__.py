import logging
from datetime import datetime, timedelta
from typing import Coroutine, Optional

import jwt
import voluptuous as vol
from homeassistant.auth.models import (TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
                                       RefreshToken, User)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)
DOMAIN = "the_token"
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional("username"): cv.string,
                vol.Optional("refresh_token_client_id"): cv.string,
                vol.Optional(
                    "refresh_token_client_name", default="TheToken"
                ): cv.string,
                vol.Optional("refresh_token", default="0" * 64): cv.string,
                vol.Optional("refresh_token_jwt_key", default="0" * 64): cv.string,
                vol.Optional("refresh_token_id", default="0" * 32): cv.string,
                vol.Optional(
                    "refresh_token_created_at",
                    default=datetime.fromisoformat("2022-01-01 00:00:00.000+00:00"),
                ): cv.datetime,
                vol.Optional("access_token_expiration_days", default=3650): vol.Coerce(
                    int
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def generate_refresh_token(user: User, config) -> RefreshToken:
    kwargs = {
        "id": config["refresh_token_id"],
        "user": user,
        "client_id": config.get("refresh_token_client_id"),
        "client_name": config["refresh_token_client_name"],
        "created_at": config["refresh_token_created_at"],
        "token": config["refresh_token"],
        "jwt_key": config["refresh_token_jwt_key"],
        "token_type": TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        "access_token_expiration": timedelta(
            days=config["access_token_expiration_days"]
        ),
    }
    return RefreshToken(**kwargs)


def generate_access_token(refresh_token: RefreshToken) -> str:
    return jwt.encode(
        {
            "iss": refresh_token.id,
            "iat": refresh_token.created_at,
            "exp": refresh_token.created_at + refresh_token.access_token_expiration,
        },
        refresh_token.jwt_key,
        algorithm="HS256",
    )


def generate_and_print_access_token(refresh_token: RefreshToken):
    _LOGGER.info("Access token is %s", generate_access_token(refresh_token))


async def find_user(
    hass: HomeAssistant, suggested_user_name: Optional[str] = None
) -> Coroutine[None, None, User]:
    # Find user entry in auth providers.
    # If a user didn't login before [for example, if it was added via hass --script auth add]
    # then the user was not actually created so we can't use hass.auth._store.async_get_users().
    provider = hass.auth.auth_providers[0]
    await provider.async_initialize()
    usernames = set([u["username"] for u in provider.data.users])
    if suggested_user_name is not None:
        if suggested_user_name in usernames:
            username = suggested_user_name
        else:
            _LOGGER.error(
                "User '%s' not found, available users: %s",
                suggested_user_name,
                usernames,
            )
            return None
    elif len(usernames) == 1:
        username = list(usernames)[0]
    elif len(usernames) == 0:
        _LOGGER.error("There are no users in HA")
        return None
    else:
        _LOGGER.error(
            "There are several users in HA: %s, please choose one to generate token for",
            usernames,
        )
        return None

    # Create user if needed and return
    credentials = await provider.async_get_or_create_credentials({"username": username})
    user = await hass.auth.async_get_or_create_user(credentials)
    return user


async def async_setup(hass: HomeAssistant, hass_config):
    component_config = hass_config[DOMAIN]
    
    user = await find_user(hass, component_config.get("username"))
    if user is None:
        _LOGGER.error("No user could be selected for creating a token")
        return False
    else:
        _LOGGER.info("User %s is chosen to create a token", user.name)

    refresh_token_id = component_config["refresh_token_id"]
    refresh_token = user.refresh_tokens.get(refresh_token_id)
    if refresh_token is not None:
        _LOGGER.info(
            "Refresh token with id %s already exists for user %s",
            refresh_token_id,
            user.name,
        )
        generate_and_print_access_token(refresh_token)
        return True

    refresh_token_client_name = component_config["refresh_token_client_name"]
    refresh_token = next(
        (
            t
            for t in user.refresh_tokens.values()
            if t.client_name == refresh_token_client_name
        ),
        None,
    )
    if refresh_token is not None:
        _LOGGER.info(
            "Refresh token with client_name=%s already exists for user %s",
            refresh_token_client_name,
            user.name,
        )
        generate_and_print_access_token(refresh_token)
        return True

    _LOGGER.info("Creating refresh & access tokens for %s", user.name)

    refresh_token = generate_refresh_token(user, component_config)
    user.refresh_tokens[refresh_token.id] = refresh_token
    hass.auth._store._async_schedule_save()

    generate_and_print_access_token(refresh_token)

    return True
