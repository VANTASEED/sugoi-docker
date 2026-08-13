#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

NAME="sugoi-docker"
VERSION="$(sed -n 's/.*__version__ = "\([^"]*\)".*/\1/p' gtk/sugoi-docker.py | head -1)"
RPMBUILD="${HOME}/rpmbuild"

GPG_NAME="${SUGOI_GPG_NAME:-}"
GPG_EMAIL="${SUGOI_GPG_EMAIL:-sugoi@localhost}"
GPG_UID="${SUGOI_GPG_UID:-Sugoi Docker Maintainers}"

if ! command -v rpmbuild >/dev/null 2>&1; then
  echo "==> installing rpmbuild (needs your password once)"
  sudo zypper --non-interactive install rpmbuild
fi

# ---------- signing key ----------
ensure_key() {
  if [ -z "$GPG_NAME" ]; then
    GPG_NAME="$GPG_UID <$GPG_EMAIL>"
  fi
  if gpg --list-secret-keys "$GPG_NAME" >/dev/null 2>&1; then
    echo "==> using existing GPG signing key: $GPG_NAME"
  else
    echo "==> generating a new GPG signing key: $GPG_NAME"
    gpg --batch --pinentry-mode loopback --passphrase '' \
      --quick-generate-key "$GPG_NAME" rsa2048 sign 0
  fi
  mkdir -p "$RPMBUILD"
  echo "%_gpg_name $GPG_NAME" > "$HOME/.rpmmacros"
}

mkdir -p "$RPMBUILD"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

echo "==> staging sources"
stage="$RPMBUILD/BUILD/${NAME}-${VERSION}"
rm -rf "$stage"
mkdir -p "$stage"
cp ../docker.sh gtk/sugoi-docker.py gtk/sugoi-docker.desktop \
   README.md LICENSE VSLogo_Black.png VSLogo_White.png gtk/github-mark.svg \
   "$stage/"
cp -r gtk/icons "$stage/icons"
tar -czf "$RPMBUILD/SOURCES/${NAME}-${VERSION}.tar.gz" -C "$RPMBUILD/BUILD" "${NAME}-${VERSION}"
cp "${NAME}.spec" "$RPMBUILD/SPECS/"

echo "==> building RPM"
rpmbuild -ba --define "version $VERSION" "$RPMBUILD/SPECS/${NAME}.spec" >/dev/null

RPM_PATH="$RPMBUILD/RPMS/noarch/${NAME}-${VERSION}-1.noarch.rpm"

echo "==> signing RPM"
ensure_key
rpmsign --addsign "$RPM_PATH" >/dev/null

echo "==> exporting public key"
gpg --armor --export "$GPG_NAME" > sugoi-docker-pubkey.asc

echo
echo "Built and signed:"
ls -l "$RPM_PATH"
echo "Public key exported: packaging/sugoi-docker-pubkey.asc"

read -r -p "Install it now? [y/N] " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
  rpm --import sugoi-docker-pubkey.asc
  sudo zypper --non-interactive install "$RPM_PATH"
  echo
  echo "Installed. Launch with: sugoi-docker   (or 'Sugoi! Docker' in the app menu)"
fi
