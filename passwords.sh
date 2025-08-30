#!/bin/bash
# =========================================================
# Bash script to add predefined accounts to predefined_accounts.json
# Passwords are encrypted using Python Fernet for security.
# Can also generate and store a Fernet key locally.
# =========================================================

JSON_FILE="predefined_accounts.json"
KEY_FILE="fernet.key"

echo "--------------------------------------------------"
echo "This script will add a predefined account for Nessus deployment."
echo

# Generate Fernet key if needed
if [ ! -f "$KEY_FILE" ]; then
    read -p "No Fernet key found. Generate a new key and store it in $KEY_FILE? (y/n): " GEN_KEY
    if [[ "$GEN_KEY" =~ ^[Yy]$ ]]; then
        KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        echo "$KEY" > "$KEY_FILE"
        echo "Fernet key generated and saved to $KEY_FILE."
        echo "Keep this file secure. It will be needed to decrypt passwords."
    else
        echo "Fernet key is required to encrypt passwords. Exiting."
        exit 1
    fi
fi

ENCRYPTION_KEY=$(cat "$KEY_FILE")

echo "--------------------------------------------------"
echo "Using Fernet key from $KEY_FILE."

while true; do
    read -p "Enter account name (e.g., account3): " ACCOUNT_NAME
    read -p "Enter username: " USERNAME
    read -s -p "Enter password: " PASSWORD
    echo
    read -s -p "Enter sudo password: " SUDO_PASSWORD
    echo
    read -p "Enter activation key: " ACTIVATION_KEY

    # Encrypt passwords using Python Fernet
    ENC_PASSWORD=$(python3 - <<END
from cryptography.fernet import Fernet
cipher = Fernet("$ENCRYPTION_KEY".encode())
print(cipher.encrypt("$PASSWORD".encode()).decode())
END
)

    ENC_SUDO=$(python3 - <<END
from cryptography.fernet import Fernet
cipher = Fernet("$ENCRYPTION_KEY".encode())
print(cipher.encrypt("$SUDO_PASSWORD".encode()).decode())
END
)

    # Ensure JSON file exists
    if [ ! -f "$JSON_FILE" ]; then
        echo "{}" > "$JSON_FILE"
    fi

    # Add new account to JSON
    python3 - <<END
import json

json_file = "$JSON_FILE"
account_name = "$ACCOUNT_NAME"
username = "$USERNAME"
enc_password = "$ENC_PASSWORD"
enc_sudo = "$ENC_SUDO"
activation_key = "$ACTIVATION_KEY"

with open(json_file, "r") as f:
    try:
        data = json.load(f)
    except:
        data = {}

if account_name in data:
    print(f"WARNING: Account '{account_name}' already exists and will be overwritten.")

data[account_name] = {
    "username": username,
    "password": enc_password,
    "sudo_password": enc_sudo,
    "activation_key": activation_key
}

with open(json_file, "w") as f:
    json.dump(data, f, indent=4)

print(f"Account '{account_name}' added successfully!")
END

    # Ask if user wants to add another account
    read -p "Add another account? (y/n): " ADD_MORE
    if [[ ! "$ADD_MORE" =~ ^[Yy]$ ]]; then
        break
    fi
done

echo "--------------------------------------------------"
echo "All accounts updated in $JSON_FILE."
echo "Fernet key used: $KEY_FILE"
echo "Keep this key safe; it is required to decrypt passwords in the Flask app."
echo "--------------------------------------------------"
