# Extra trusted certificates

Any `.crt` file in this folder is added to the API container's list of trusted
certificate authorities when the image is built (see `api/Dockerfile`).

It exists for networks that inspect HTTPS traffic, such as a work laptop with a
security client installed. On those networks the connection to Claude is re-signed by
the inspector's own certificate. The container does not know that certificate, so
calls to Claude fail with "Connection error". The `.crt` files are not committed to git.

To add one on a Mac, find the inspector's root certificate in Keychain Access (System
keychain), then run this from the Moneypenny folder with its name, and rebuild:

    security find-certificate -c "NAME OF THE ROOT CERTIFICATE" -p /Library/Keychains/System.keychain > api/certs/inspector-root.crt
    docker compose up -d --build api

Trusting the certificate means your prompts, replies and API key pass through that
inspection. On a network with no inspection, leave the folder empty.
