Name:           sugoi-docker
Version:        %{?version}%{!?version:1.0.0}
Release:        1
Summary:        GTK interface for controlling the Docker service
License:        MIT
URL:            https://github.com/horizon/sugoi-docker
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3-gobject
Requires:       typelib-1_0-Gtk-3_0
Requires:       pkexec

%description
Sugoi! Docker — a graphical GTK3 interface for controlling the Docker
service. Button-click control for starting/stopping Docker on demand,
enabling or disabling auto-start on boot, and running common Docker
commands such as listing images/containers, viewing stats and logs, and
pruning unused data.

Privileged operations use a polkit (pkexec) password prompt; read-only
commands run as the current user. A terminal-style output panel renders
real ANSI colors, and the app follows the system light/dark theme.

The package bundles the sugoi-docker-cli command-line tool that drives
all operations.

%prep
%autosetup

%install
install -d %{buildroot}%{_bindir}
install -m 0755 sugoi-docker.py %{buildroot}%{_bindir}/sugoi-docker
install -m 0755 docker.sh %{buildroot}%{_bindir}/sugoi-docker-cli
install -d %{buildroot}%{_datadir}/applications
install -m 0644 sugoi-docker.desktop %{buildroot}%{_datadir}/applications/sugoi-docker.desktop
install -d %{buildroot}%{_datadir}/icons/hicolor
for s in 64 128 256 512; do
  install -d %{buildroot}%{_datadir}/icons/hicolor/${s}x${s}/apps
  install -m 0644 icons/sugoi-docker-${s}.png \
    %{buildroot}%{_datadir}/icons/hicolor/${s}x${s}/apps/sugoi-docker.png
done

install -d %{buildroot}%{_datadir}/sugoi-docker
install -m 0644 VSLogo_Black.png VSLogo_White.png github-mark.svg \
  %{buildroot}%{_datadir}/sugoi-docker/

%post
gtk-update-icon-cache %{_datadir}/icons/hicolor >/dev/null 2>&1 || :

%postun
gtk-update-icon-cache %{_datadir}/icons/hicolor >/dev/null 2>&1 || :

%files
%{_bindir}/sugoi-docker
%{_bindir}/sugoi-docker-cli
%{_datadir}/applications/sugoi-docker.desktop
%{_datadir}/icons/hicolor/64x64/apps/sugoi-docker.png
%{_datadir}/icons/hicolor/128x128/apps/sugoi-docker.png
%{_datadir}/icons/hicolor/256x256/apps/sugoi-docker.png
%{_datadir}/icons/hicolor/512x512/apps/sugoi-docker.png
%{_datadir}/sugoi-docker/VSLogo_Black.png
%{_datadir}/sugoi-docker/VSLogo_White.png
%{_datadir}/sugoi-docker/github-mark.svg
%doc README.md
%license LICENSE

%changelog
* Thu Aug 13 2026 Horizon <horizon@localhost>
- Renamed to Sugoi! Docker (sugoi-docker)
- GUI installed as /usr/bin/sugoi-docker, CLI as /usr/bin/sugoi-docker-cli
- Replaced SVG icon with the sugoidocker.png PNG icon (64/128/256/512)
- Added About dialog (studio logo, tagline, GitHub link) with single-source version
