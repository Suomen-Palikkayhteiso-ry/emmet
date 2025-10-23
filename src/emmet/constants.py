# List of usernames that should never be disabled or deleted from Keycloak.
# These users are typically administrative accounts or system users.
PROTECTED_USERS = [
    "admin",
    "service-account-emmet-cli-client",  # Example: The service account for this CLI tool itself
    # Add any other protected usernames here
]

# List of required user actions for newly created Keycloak users.
REQUIRED_USER_ACTIONS = [
    "UPDATE_PASSWORD",
    "VERIFY_EMAIL",
    "WEBAUTHN_REGISTER_PASSWORDLESS",
    # Add any other required actions here
]
