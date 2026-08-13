#!/usr/bin/env bash
set -euo pipefail

SERVICE="docker"

usage() {
  cat <<EOF
docker.sh — control the Docker service

USAGE:
  docker.sh <command>

COMMANDS:
  start       Start Docker now (does NOT auto-start on boot)
  stop        Stop Docker now
  restart     Restart Docker now
  status      Show Docker service status (active/running/enabled)
  enable      Enable Docker to auto-start on every boot
  disable     Disable Docker auto-start on boot
  info        Show system-wide Docker info
  version     Show Docker version
  images      List downloaded images
  ps          List running containers
  psall       List all containers (including stopped)
  prune       Remove unused data (containers, images, networks, build cache)
  prunevol    Remove ALL unused volumes (WARNING: deletes data)
  stats       Show live resource usage of running containers
  logs        Show logs (usage: docker.sh logs [container])
  help        Show this help

NOTE:
  Start/stop only affects the current session. Docker will NOT start on
  boot unless you run 'docker.sh enable' first.

EOF
}

elevate() {
  if [ "$(id -u)" -ne 0 ]; then
    exec sudo "$0" "$@"
  fi
}

case "${1:-help}" in
  start)
    elevate "$@"
    systemctl start "$SERVICE"
    echo "Docker started (will NOT auto-start on next boot unless enabled)."
    ;;
  stop)
    elevate "$@"
    systemctl stop "$SERVICE"
    echo "Docker stopped."
    ;;
  restart)
    elevate "$@"
    systemctl restart "$SERVICE"
    echo "Docker restarted."
    ;;
  status)
    systemctl status "$SERVICE" --no-pager || true
    printf '\nEnabled on boot: %s\n' "$(systemctl is-enabled "$SERVICE" 2>/dev/null || echo unknown)"
    ;;
  enable)
    elevate "$@"
    systemctl enable --now "$SERVICE"
    echo "Docker enabled: it will now auto-start on every boot."
    ;;
  disable)
    elevate "$@"
    systemctl disable "$SERVICE"
    echo "Docker disabled: it will no longer auto-start on boot."
    ;;
  info)
    docker info
    ;;
  version)
    docker version
    ;;
  images)
    docker images
    ;;
  ps)
    docker ps
    ;;
  psall)
    docker ps -a
    ;;
  prune)
    elevate "$@"
    docker system prune -a --volumes=false
    ;;
  prunevol)
    elevate "$@"
    echo "WARNING: this removes ALL unused volumes (your data is gone!)."
    read -r -p "Are you sure? Type 'yes' to continue: " ans
    [ "$ans" = "yes" ] && docker system prune -a --volumes || echo "Aborted."
    ;;
  stats)
    docker stats "${@:2}"
    ;;
  logs)
    docker logs "${2:-}"
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "Unknown command: ${1}" >&2
    usage
    exit 1
    ;;
esac
