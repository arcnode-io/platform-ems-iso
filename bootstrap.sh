#!/bin/sh
# arcnode appliance bootstrap — step 1 of the walking skeleton.
#
# Run on a plain Debian install (Hetzner installimage or stock d-i):
#
#   curl -fsSL https://arcnode-public.s3.amazonaws.com/appliance/bootstrap.sh | sh
#
# Today it does exactly one thing: the next login greets you with `arcnode`.
# Every future appliance capability layers onto this script in verifiable
# increments — no custom ISO mastering, no GRUB/d-i surgery.
set -eu

echo "arcnode" > /etc/motd

echo "done — log in again to see it"
