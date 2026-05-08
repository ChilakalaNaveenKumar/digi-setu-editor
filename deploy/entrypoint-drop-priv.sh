#!/bin/sh
# Backend container entrypoint — drops root → uid 1100 (`app`) while
# preserving CAP_SETUID + CAP_SETGID + CAP_CHOWN + CAP_FOWNER in the
# AMBIENT cap set so the FastAPI process can later spawn pi-coding-agent
# as uid 1000 (`sandbox`) via setpriv. Without ambient caps the kernel
# zeros effective+permitted on the uid-change and our nice
# `cap_add: [CHOWN, FOWNER, SETUID, SETGID]` from docker-compose ends up
# only populating the BOUNDING set (which doesn't grant caps to a
# non-root process).
#
# Why we can't just keep USER root in the Dockerfile and drop in Python:
# uvicorn would already be running with all root caps long enough to
# import every untrusted code path (PII libs, JSON parsers, sqlite, …).
# Doing the drop here, before exec'ing python, keeps the root window
# down to the ~10 ms tini takes.
#
# Why we can't use file capabilities on /usr/bin/setpriv: the container
# runs with `security_opt: no-new-privileges:true`, which disables file
# capabilities by design. Ambient caps are explicitly the workaround
# for that combination (kernel ≥ 4.3, util-linux ≥ 2.29).
#
# Threat note: if the entrypoint is overridden by an attacker who
# already has shell on the host, they own everything anyway; there's
# no defence-in-depth value to obscuring this script.

set -e

UID_APP=1100
GID_APP=1100
# Inherited+ambient caps: only the bare minimum we need for the dual-uid
# sandbox plumbing. Listed alphabetically to make `diff` review easier.
CAPS="+chown,+fowner,+setgid,+setuid"

# IMPORTANT: --init-groups (NOT --clear-groups). The Dockerfile creates
# `app` with `--groups sandbox`, so `app` is a SECONDARY member of the
# sandbox group (gid 1000). That's what lets the backend read+write
# per-session dirs (mode 2770, owner+group=1000) via group permission
# while the AI's bash runs as primary uid 1000 inside those dirs.
#
# `--clear-groups` here would strip that secondary membership and the
# backend would get EACCES on every workspace mkdir / chat write —
# defeating the entire dual-uid model from the wrong direction.
# `--init-groups` re-reads /etc/group for the new uid and re-applies
# its secondary groups (so we end up with primary=1100 + secondary=1000).
#
# In contrast, the OTHER setpriv call site (pi_session.py spawning pi)
# DOES use --clear-groups: pi must NOT inherit `app`'s secondary
# membership in any group, otherwise the AI's bash could read backend-
# private files via group permission. Different threat models, opposite
# flags — both are correct for their context.
exec /usr/bin/setpriv \
    --reuid="${UID_APP}" \
    --regid="${GID_APP}" \
    --init-groups \
    --inh-caps="${CAPS}" \
    --ambient-caps="${CAPS}" \
    -- "$@"
