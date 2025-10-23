# Emmet CLI

A CLI tool for synchronizing user data from an Excel file to Keycloak.

## Installation

Navigate to the project directory and install the dependencies:

```bash
pip install -e .
```

## Usage

### Excel File Format

Your Excel file should have a header row with the following columns (case-sensitive):

*   `username` (required)
*   `email` (optional)
*   `firstName` (optional)
*   `lastName` (optional)

### Keycloak Environment Variables

The `sync` command requires Keycloak connection details to be provided via environment variables:

*   `KEYCLOAK_SERVER`: The base URL of your Keycloak server (e.g., `http://localhost:8080/auth/`)
*   `KEYCLOAK_REALM`: The name of the Keycloak realm you are managing (e.g., `myrealm`)
*   `KEYCLOAK_CLIENT_ID`: The client ID of a Keycloak client with administrative access to the realm.
*   `KEYCLOAK_CLIENT_SECRET`: The client secret for the above client ID.

Set these in your shell before running the `sync` command:

```bash
export KEYCLOAK_SERVER="your_keycloak_server_url"
export KEYCLOAK_REALM="your_keycloak_realm"
export KEYCLOAK_CLIENT_ID="your_keycloak_client_id"
export KEYCLOAK_CLIENT_SECRET="your_keycloak_client_secret"
```

### Commands

#### `emmet dump-excel <excel_file>`

Parses the specified Excel file and prints the extracted user data to the console. Use this to visually confirm that your Excel file is being parsed correctly.

```bash
emmet dump-excel "path/to/your/excel_file.xlsx"
```

#### `emmet sync <excel_file>`

Synchronizes users from the specified Excel file to Keycloak. This command will create new users, update existing users, and disable users in Keycloak that are no longer present in the Excel file.

*   **Dry Run:** To see what actions would be taken without actually modifying Keycloak, use the `--dry-run` option:

    ```bash
    emmet sync "path/to/your/excel_file.xlsx" --dry-run
    ```

*   **Live Synchronization:** To perform the actual synchronization:

    ```bash
    emmet sync "path/to/your/excel_file.xlsx"
    ```

## Recommended Approach for Keycloak Client ID and Secret

To ensure proper and secure synchronization with Keycloak, it is recommended to create a dedicated client with appropriate permissions. Follow these steps in your Keycloak admin console:

1.  **Log in to Keycloak Admin Console:** Access your Keycloak instance and log in as an administrator.

2.  **Select Your Realm:** In the top-left corner, select the realm where you want to synchronize users.

3.  **Create a New Client:**
    *   Navigate to `Clients` in the left-hand menu.
    *   Click the `Create client` button.
    *   Set `Client ID` to something descriptive, e.g., `emmet-cli-client`.
    *   Set `Client authentication` to `On`.
    *   Set `Authorization` to `Off`.
    *   Click `Save`.

4.  **Configure Client Credentials:**
    *   After saving, go to the `Credentials` tab for your newly created client.
    *   Note down the `Client secret`. This will be your `KEYCLOAK_CLIENT_SECRET` environment variable.

5.  **Assign Realm Roles to the Client:**
    *   Go to the `Service account roles` tab for your client.
    *   Click on `Assign role`.
    *   Filter by `Filter by realm roles` and search for `admin`.
    *   Select the `admin` role and click `Assign`.
    *   This grants the client the necessary permissions to manage users in the realm.

By following these steps, you create a client specifically for the `emmet` CLI with the minimum required permissions, enhancing the security of your Keycloak integration.
