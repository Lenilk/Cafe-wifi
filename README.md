# Cafe Wireless Internet Network Management System with National ID Authentication and Network Usage Logging Using Raspberry Pi

A Raspberry Pi prototype for managing public Wi-Fi access in cafes. It combines a staff administration panel, voucher-based captive portal, and connection and DNS logging on a single gateway.

The prototype has been tested in a laboratory and with real networking equipment, including routers, switches, and access points. It has not been deployed in an operating cafe.

## Background and Motivation

Public Wi-Fi services need to control access, retain records for retrospective investigation, and reduce risks between customers sharing a local network. This project's research background considers Section 26 of Thailand's Computer Crime Act B.E. 2550 (2007), as amended in B.E. 2560 (2017), and the associated traffic-data retention obligations.

Staff inspect a customer's ID card and register the national ID number as a reference for an issued voucher. The customer uses the voucher credentials to sign in through the captive portal. Connection and DNS records support subsequent searches, while national ID numbers are encrypted before storage.

National ID collection is a design choice of this prototype, rather than a general requirement for cafes. Checksum validation helps catch input errors; it does not establish that the person presenting a card is its rightful owner. Identity checks remain a staff procedure. Actual deployment requires assessment of applicable notifications and personal data protection obligations. The project's objectives should not be interpreted as certification of legal compliance.

## Project Objectives

1. Build a Raspberry Pi captive portal to control wireless internet access.
2. Provide a staff admin panel for registering customers using national ID numbers and issuing temporary credentials.
3. Develop network connection logging to support the project's traffic-data retention and traceability goals under the Thai Computer Crime Act.
4. Improve cafe LAN security and reduce exposure to attacks from other local network users.

## Features

- Staff admin panel with first-run administrator setup, customer registration, and voucher management.
- Automatically generated temporary usernames and passwords, with voucher expiration, device limits, and optional data quotas.
- Customer captive portal integrated with openNDS.
- Connection and DNS logging, log searches, and evidence exports.
- Encrypted national ID storage, masked display values, and hashed passwords.
- Administrative audit logs, log integrity verification, database backups, and retention cleanup tools.

## Scope and Limitations

- A Raspberry Pi 4B acts as the network gateway, captive portal server, and log server on one device.
- The two primary interfaces are the staff Admin Panel and the customer Captive Portal.
- A 13-digit Thai national ID number is used as a registration reference. Customers authenticate with generated voucher credentials.
- The prototype defaults to 180-day retention for connection and DNS logs. Cleanup has been tested using simulated data; that test does not establish complete record retention over a full 180-day operating period.
- DNS record completeness during database failures or log rotation has not yet been confirmed.
- LAN protection depends on the router and access point configuration, including client isolation and controls against bypassing the gateway.
- Docker tests cover the application services and database. They do not reproduce openNDS, DHCP, nftables, conntrack, access point isolation, or Raspberry Pi hardware behavior.

## Technology and Network Design

The application uses Python, Flask, Gunicorn, and MariaDB. The gateway installation integrates openNDS for captive portal access, nginx for web proxying, dnsmasq for DHCP/DNS, and nftables and conntrack for network control and logging. Docker tests use Caddy as the web proxy.

The gateway uses a single Ethernet cable connected to the upstream router or switch. A client-side macvlan interface separates the customer subnet from the uplink interface on the Pi. Customers must receive DHCP settings from the Pi and use it as their gateway.

Before gateway installation, configure the router and access points so that:

- Competing customer DHCP service is disabled.
- LAN IPv6 is disabled for the current prototype deployment.
- Client isolation blocks customer-to-customer traffic while preserving access to the Pi.
- Router access controls prevent customers from reaching the internet directly through the upstream router.

See the [router deployment runbook](docs/isp-router-runbook.md) for configuration and verification steps. Prepare local console access or an alternative management connection before changing gateway networking.

## Quick Start with Docker

Use Docker Engine and the Docker Compose plugin to try the application services with test data. Run these commands from the repository root:

```bash
git clone https://github.com/Lenilk/Cafe-wifi.git
cd Cafe-wifi
docker compose config --quiet
docker compose build admin fas tests jobs dns-collector
docker compose up -d db admin fas proxy
docker compose ps
```

Open `https://localhost:8443/setup` and use the test setup token `docker-test-setup-token` to create the first administrator account. The test HTTPS certificate uses a container-local certificate authority, so your browser will display a trust warning.

The customer portal is available at `http://127.0.0.1:8080/login`. This environment uses a simulated gateway in flow tests; opening the portal does not create a working Wi-Fi gateway.

Run the test suite:

```bash
docker compose run --rm tests
```

Stop the services while retaining test volumes:

```bash
docker compose down
```

The Compose environment uses public test credentials and keys from `docker/test.env`. Use only synthetic data. See the [Docker testing guide](docs/docker-test.md) for health checks, maintenance jobs, DNS collector tests, and test-volume cleanup.

## Gateway Installation

Use a dedicated Linux gateway with administrative access and internet connectivity for downloading dependencies. Raspberry Pi OS, Debian, or Ubuntu with systemd is the recommended starting point. The installer also includes package-manager detection for Fedora/RHEL/Rocky, Arch, openSUSE, and Alpine; this does not imply equivalent validation on every distribution. Non-systemd systems require manual service integration.

If you have not cloned the repository, use the clone commands above. Preview installation first:

```bash
./install.sh --dry-run
./install.sh --help
```

After reviewing the network settings and the router runbook, install:

```bash
sudo ./install.sh
```

The installer configures host networking and system services. Set interface names, subnets, and gateway addresses for your environment using the options shown by `--help`.

For application development on a VM or laptop, skip gateway network configuration and the openNDS build:

```bash
sudo ./install.sh -y --skip-network --skip-opennds
```

This mode still installs dependencies and application services on the host.

### First Administrator Setup

The installer prints the Admin Panel URL and a setup token.

1. From a staff device on the uplink network, open `https://<gateway-uplink-ip>:8443/setup` (or the configured admin port).
2. Enter the setup token. It can also be read on the gateway with `sudo cat /etc/cafe-wifi/setup.token`.
3. Create the first administrator username and password.

The gateway uses a self-signed HTTPS certificate by default. After the first account is created, the setup endpoint closes and the token file is removed. The customer subnet is blocked from accessing the Admin Panel.

### Reset an Administrator Password

On the gateway, load the installed environment before running the reset tool. Replace `admin` with the account username:

```bash
sudo bash -c '
  set -a
  . /etc/cafe-wifi/secrets.env
  set +a
  cd /opt/cafe-wifi
  PYTHONPATH=/opt/cafe-wifi:/opt/cafe-wifi/app venv/bin/python -m tools.reset_admin admin
'
```

### Uninstall

```bash
sudo ./install.sh --uninstall
```

The uninstaller removes application files and services. It preserves the database, logs, and `/etc/cafe-wifi/secrets.env`.

## Local Development and Testing

Python 3.12 is used by the Docker test environment. To run the Python tests locally from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r app/requirements.txt pytest==8.3.5
PYTHONPATH=app:. python -m pytest tests/ -v
```

The test configuration supplies synthetic encryption keys. Gateway integration and network behavior also require hardware testing; see the [test plan](docs/test-plan.md).

## Data Protection and Secrets

- Never commit real credentials, encryption keys, customer records, or production logs.
- Keep a secure backup of `/etc/cafe-wifi/secrets.env` outside the gateway. Losing its encryption key makes existing encrypted national ID records unrecoverable.
- Use synthetic national ID numbers starting with `0` and a valid checksum for testing.
- `.env.example` documents configuration options; its placeholder values are not production secrets. The installer generates the actual environment at `/etc/cafe-wifi/secrets.env`.
- Review the [privacy policy](docs/privacy-policy-th.md) and adapt data handling and retention to the requirements of the deployment.

## Documentation

Most supporting documents are currently written in Thai.

- [Project plan and design decisions](PROJECT_PLAN.md)
- [Docker testing guide](docs/docker-test.md)
- [System test plan](docs/test-plan.md)
- [Hardware test log](docs/hardware-test-log.md)
- [Router deployment runbook](docs/isp-router-runbook.md)
- [Gateway load test plan](docs/gateway-load-test-plan.md)
- [Privacy policy](docs/privacy-policy-th.md)

## Contributing

Issues and pull requests are welcome. For bug reports, include the environment, reproduction steps, expected behavior, and relevant sanitized logs. Remove customer information and secrets before sharing diagnostics.

For pull requests, explain the change and its validation. Run the relevant tests, and when changing `install.sh`, also run `bash -n install.sh` and `./install.sh --dry-run`. Clearly distinguish application tests from hardware and network validation.

## License

This repository does not currently include a `LICENSE` file. An open-source license has not yet been specified. Contact the repository owner for reuse and redistribution permissions until a license is added.
