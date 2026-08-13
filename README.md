<p align="center">
  <img src="sugoidocker.png" alt="Sugoi! Docker" width="160">
</p>

<h1 align="center">Sugoi! Docker</h1>

<p align="center">
  A Linux GTK3 app and CLI tool to control the Docker service on demand.
</p>

Docker is **not** auto-started on boot by default. Sugoi! Docker lets you start
and stop it when you need it, and only `enable` it if you want it running all
the time.

## Features

- Start, stop, restart, enable, and disable the Docker service
- Run common Docker commands (images, containers, stats, logs, prune)
- Color terminal-style output panel with real ANSI rendering
- Follows the system light/dark theme
- Privileged operations use a polkit (pkexec) password prompt
- Bundled `sugoi-docker-cli` command-line tool

## Install

Download the package for your distribution from the
[Releases](https://github.com/VANTASEED/sugoi-docker/releases) page.

| Format | File |
| --- | --- |
| AppImage | `sugoi-docker-1.0.0-x86_64.AppImage` |
| Debian / Ubuntu | `sugoi-docker_1.0.0-1_all.deb` |
| RPM (openSUSE / Fedora) | `sugoi-docker-1.0.0-1.noarch.rpm` |
| Source | `sugoi-docker-1.0.0.tar.gz` |

## Requirements

- **Docker** installed and running on the system (the app controls it, it does
  not install it)
- **systemd** and **polkit** (pkexec) for service control and privilege
  elevation

The packages resolve their own GUI dependencies automatically:

| Format | GUI dependencies (auto-resolved) |
| --- | --- |
| `.deb` | `python3-gi`, `gir1.2-gtk-3.0`, `pkexec` |
| `.rpm` | `python3-gobject`, GTK 3 typelib, `pkexec` |
| `.AppImage` | self-contained (bundles Python, GTK 3, and the CLI) |

### AppImage

Runs on most Linux distributions with no install step. It bundles its own
Python, GTK 3, and `sugoi-docker-cli`, so nothing needs to be installed apart
from Docker itself. Note that the AppImage is built on a recent base and
requires a reasonably modern glibc.

```bash
chmod +x sugoi-docker-1.0.0-x86_64.AppImage
./sugoi-docker-1.0.0-x86_64.AppImage
```

### Debian / Ubuntu

```bash
sudo apt install ./sugoi-docker_1.0.0-1_all.deb
```

Dependencies (`python3-gi`, `gir1.2-gtk-3.0`, `pkexec`) are resolved
automatically by apt.

### RPM (openSUSE / Fedora)

```bash
# openSUSE
sudo rpm --import sugoi-docker-pubkey.asc
sudo zypper install ./sugoi-docker-1.0.0-1.noarch.rpm

# Fedora
sudo rpm --import sugoi-docker-pubkey.asc
sudo dnf install ./sugoi-docker-1.0.0-1.noarch.rpm
```

Dependencies are resolved automatically (`python3-gobject`, GTK 3 typelib,
`pkexec`).

### Source

```bash
tar xzf sugoi-docker-1.0.0.tar.gz
cd sugoi-docker-1.0.0
sudo ./build.sh
```

## The CLI

Installed as `sugoi-docker-cli`, or run from this repo as `./docker.sh`.

| Command | Description |
| --- | --- |
| `start` | Start Docker now (won't auto-start on boot) |
| `stop` | Stop Docker now |
| `restart` | Restart Docker now |
| `status` | Show service status and whether it's enabled on boot |
| `enable` | Auto-start Docker on every boot |
| `disable` | Cancel auto-start on boot |
| `info` | System-wide Docker info |
| `version` | Docker version |
| `images` | List downloaded images |
| `ps` | List running containers |
| `psall` | List all containers (including stopped) |
| `prune` | Remove unused containers/images/networks/build cache |
| `prunevol` | Remove ALL unused volumes (asks for confirmation) |
| `stats` | Live resource usage of running containers |
| `logs [container]` | Show container logs |
| `help` | Show this help |

## Build from source

```bash
./build.sh
```

This builds a signed RPM and asks whether to install it.

## License

[MIT](LICENSE)

---

<p align="center">
  <img src="VSLogo_White.png" alt="VANTASEED Studio" width="220">
  <br>
  Powered by copious amounts of instant noodles, questionable caffeine
  tolerance, and a stubborn refusal to go touch grass.
</p>
