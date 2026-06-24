# CLAUDE.md

Guidance for Claude (and contributors) working on this repo.

## What this is

Two Python submitters that live inside Houdini HDAs and submit jobs to
Thinkbox Deadline 10:

- `submitter_husk.py` -- Karma USD render via the third-party
  HuskStandalone Deadline plugin.
- `submitter_usd_export.py` -- USD-export-to-disk job that runs `hython`
  on the farm and cooks a LOP node.

Both were extracted from `render-farm-control/houdini/` on 2026-04-29
when the umbrella repo was split per concern.  If a wake-on-LAN /
power / autowake event question comes up, redirect to
`render-farm-control` -- this one stays focused on Houdini-side
submission.

## Repo orientation

- `submitter_husk.py` -- entry point `submit_to_deadline(kwargs)`.
  Reads parms off the calling HDA node, builds the Husk job file in
  a temp dir, calls `deadlinecommand` to submit.  ~830 lines.
- `submitter_usd_export.py` -- entry point
  `submit_usd_export_to_deadline(kwargs)`.  Same pattern but the job
  command is `hython -c "<cook the LOP and write USD>"`.  ~530 lines.
- `secrets.example.py` -- template for `PATH_MAP`, the local->farm
  path remap.  `secrets.py` (the filled-in copy) is gitignored.

The HDAs themselves are NOT versioned here -- each studio wires its
own UI.  The script comment blocks at the top of each `.py` document
the parameter contract the HDA must provide.

## Conventions carried over from render-farm-control

- "ship" = `git commit && git push`, no amend, no force.
- Both git commit and git push are user-call only -- auto mode does
  NOT authorise either.
- When renaming/moving files, update `.gitignore` if the moved file
  was ignored.  `secrets.py` was at `houdini/secrets.py` in the source
  repo and is at the root here; the .gitignore was updated on the
  move.
- Update the README alongside any code change that affects user-
  facing behaviour (parm contract, callback names).  Don't wait to be
  asked.

## How to dive in fresh

1. `git log --oneline -30` for recent context.
2. Read the comment block at the top of each submitter -- it lists
   the HDA parameter contract.
3. The submitters are long but linear: read the entry-point function,
   then walk the helpers it calls top-down.

## Pending

- HDA itself isn't here.  If we ever ship one (so users don't have to
  hand-wire parms), it'd live in `otls/` and use the same setup-script
  pattern as `houdini-to-aftereffects-usd-exporter`.
- Husk vs full USD export -- two separate submitters because the job
  shapes differ (Husk = renderer; export = hython).  If a third
  Houdini-side Deadline submitter shows up, factor the shared parts
  (path mapping, parm reading, deadlinecommand wrapper) into a
  `_common.py` module.
