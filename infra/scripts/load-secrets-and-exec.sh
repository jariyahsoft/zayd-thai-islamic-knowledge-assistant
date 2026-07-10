#!/usr/bin/env sh
set -eu

for name in $(env | sed -n 's/^\([A-Z0-9_]*_FILE\)=.*/\1/p'); do
  file=$(printenv "$name")
  target=${name%_FILE}
  if [ -z "$file" ] || [ ! -r "$file" ]; then
    printf 'secret_loader_error code=secret_unavailable name=%s\n' "$target" >&2
    exit 1
  fi
  value=$(cat "$file")
  if [ -z "$value" ]; then
    printf 'secret_loader_error code=secret_empty name=%s\n' "$target" >&2
    exit 1
  fi
  export "$target=$value"
  unset "$name"
done

exec "$@"
