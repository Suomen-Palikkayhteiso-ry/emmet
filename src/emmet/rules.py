from emmet.types import Ruleset


def get_ruleset() -> Ruleset:
    return Ruleset(
        user_rules=[
            {
                "first_name": "First Name",
                "last_name": "Last Name",
                "email": "Email",
            }
        ]
    )
