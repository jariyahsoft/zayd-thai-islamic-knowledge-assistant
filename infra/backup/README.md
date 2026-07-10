# Backup automation

The scripts create and restore a single encrypted, checksummed recovery bundle. See
`docs/operations/backup-restore.md` for configuration and the mandatory isolated restore drill.
Install the example systemd unit and timer only after creating a dedicated `zayd-backup` user,
restricting `/etc/zayd/backup.env` to that user, and reviewing filesystem/network permissions.
