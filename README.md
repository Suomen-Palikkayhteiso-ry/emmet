# Emmet

CLI tool for synchronizing user data from Excel to Keycloak using automatic column detection.

## Installation

```bash
uv sync
```

## Usage

Run commands using `uv run`:

```bash
uv run emmet -v dump-excel example.xlsx
uv run emmet sync example.xlsx --dry-run
```

Or with devenv:

```bash
devenv shell -- emmet -v dump-excel example.xlsx
```

### Commands

**`emmet dump-excel <excel_file>`**

Parse and display user data from Excel file. Automatically detects email and name columns.

**`emmet sync <excel_file> [--dry-run]`**

Synchronize users to Keycloak. Creates new users with UUID4 usernames, updates existing users by email, and disables users not in Excel.

The tool automatically:
- Detects email column by scanning for valid email addresses
- Detects name column by finding cells with two words (first_name last_name)
- Skips rows containing "eronnut" (case-insensitive)

### Keycloak Configuration

Set environment variables:

```bash
export KEYCLOAK_SERVER="http://localhost:8080/auth/"
export KEYCLOAK_REALM="myrealm"
export KEYCLOAK_CLIENT_ID="emmet-cli-client"
export KEYCLOAK_CLIENT_SECRET="your-secret"
```

### Keycloak Client Setup

1. In Keycloak Admin Console, navigate to **Clients** → **Create client**
2. Set `Client ID` to `emmet-cli-client`
3. Enable `Client authentication`
4. Go to **Credentials** tab and copy the `Client secret`
5. Go to **Service account roles** tab → **Assign role**
6. Select `admin` role from realm roles

### Protected Users

Edit `src/emmet/constants.py` to configure protected email addresses that won't be disabled:

```python
PROTECTED_USERS = [
    "admin",
    "suomenpalikkayhteisory@outlook.com",
    "suomenpalikkayhteisory+dummy@outlook.com",
]
```

**Note:** The username `"admin"` is always protected regardless of email address.
