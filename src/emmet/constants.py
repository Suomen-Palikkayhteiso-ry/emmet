# List of email addresses that should never be disabled or deleted from Keycloak.
# These users are typically administrative accounts or system users.
# Note: The username "admin" is also hardcoded as protected regardless of email.
PROTECTED_USERS = [
    "suomenpalikkayhteisory@outlook.com",
    "suomenpalikkayhteisory+dummy@outlook.com",
]

# List of required user actions for newly created Keycloak users.
REQUIRED_USER_ACTIONS = [
    "webauthn-register-passwordless",
]
