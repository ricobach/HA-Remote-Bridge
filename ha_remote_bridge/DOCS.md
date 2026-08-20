# HA Remote Bridge App documentation

## Install

1. In Home Assistant, go to **Settings > Apps > App store**.
2. Open the repository menu and add:

   `https://github.com/ricobach/HA-Remote-Bridge`

3. Install **HA Remote Bridge**.
4. Start the App.
5. Select **Open Web UI**.

## Add a resource

Enter a friendly name and a local HTTP or HTTPS URL, for example:

- `Kitchen ESPHome` → `http://192.168.1.51`
- `Proxmox` → `https://192.168.1.10:8006`

Disable **Verify SSL** only when the local service uses a certificate that cannot be verified by the App.

## How access works

The browser connects to Home Assistant. Home Assistant authenticates the user and forwards the request through Ingress to HA Remote Bridge. The App then makes the outbound connection to the configured local target.

No TCP port is published by HA Remote Bridge to the LAN or Internet.

## Compatibility

Simple web interfaces should work directly. HA Remote Bridge also rewrites common root-relative HTML/CSS paths and bridges WebSockets. Some complex applications may still fail when they assume they are hosted at `/`, rely on hard-coded external origins, or require cookie behavior that cannot safely be shared through the Home Assistant origin.

## Security

HA Remote Bridge is intended for trusted local resources. Only configure targets you trust. Home Assistant Ingress is the external authentication boundary for the App. The App itself rejects requests that are not delivered by the Ingress proxy.

This is an early release; avoid using it as the sole protection for highly sensitive administrative interfaces until the project has had broader testing.
