#!/bin/bash
# Runs inside the freshly-installed Debian chroot at the end of installimage.
# Step 1 of the appliance, in full: greet 'arcnode' on login — nothing else.
#
# Debian's sshd sets `PrintMotd no` and delegates to pam_motd, which prints a
# dynamic part (/etc/update-motd.d, e.g. the kernel uname line) then the static
# /etc/motd. Drop the dynamic part so the login banner is exactly 'arcnode'.
rm -f /etc/update-motd.d/*
printf 'arcnode\n' > /etc/motd
