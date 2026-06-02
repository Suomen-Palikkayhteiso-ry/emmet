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
uv run emmet list-emails example.xlsx
uv run emmet sync example.xlsx --dry-run
```

Or with devenv:

```bash
devenv shell -- emmet -v dump-excel example.xlsx
```

### Commands

**`emmet dump-excel <excel_file>`**

Parse and display user data from Excel file.

**`emmet list-emails <excel_file> [--without-current-year-payment | --with-current-year-payment]`**

Print one email address per line for active members from the Excel file. Use
`--without-current-year-payment` to list active members who have not paid during
the ongoing year, or `--with-current-year-payment` to list only active members
who have paid during the ongoing year.

**`emmet sync <excel_file> [--dry-run]`**

Synchronize active members to Keycloak. Creates new users with UUID4 usernames, updates existing users by email, and disables users not in the active member set.

The tool automatically:
- Prefers known membership sheet headers (Finnish) and falls back to heuristics when needed
- Skips rows marked as resigned (`Eronnut` is true) or containing `eronnut`
- Skips special-case emails: `palikkaharrastajatry@outlook.com` and `palikkaharrastajatry+...@outlook.com`
- Maps `Liittymispäivä` to `registrationDate` and `Jäsenmaksu` to `paymentDate`
- Provisions only active members based on `Jäsenmaksu`:
  - Membership paid in year `Y` is valid through `Y+1-12-31`
  - Example: payment `2024-04-30` is valid until `2025-12-31`
- Columns `Ei äänioikeutta` and `Puhelin` are currently parsed but not synchronized to Keycloak attributes

Expected spreadsheet columns:
- `Nimi`
- `Kotikaupunki`
- `Discord`
- `Bricklink`
- `Brickowl`
- `Liittymispäivä`
- `Jäsenmaksu`
- `Ei äänioikeutta` (boolean)
- `Eronnut` (boolean)
- `Sähköposti`
- `Puhelin`

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
    "suomenpalikkayhteisory@outlook.com",
    "suomenpalikkayhteisory+dummy@outlook.com",
    "palikkaharrastajatry@outlook.com",
]
```

**Note:** The username `"admin"` is always protected regardless of email address.  
Emails matching `palikkaharrastajatry+...@outlook.com` are also always skipped.
