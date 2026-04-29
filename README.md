```
       _____                          __
      / ___/__ ___ ____ ___  ___ ____/ /  __ _____ ___
     / (_ / -_) _ `/ -_) _ \(_-</ __/ _ \/ // (_-<(_-<
     \___/\__/\_, /\__/_//_/___/\__/_//_/\_,_/___/___/
             /___/
```

# Houdini Deadline Toolbox

> Houdini-side Deadline submitters for **Karma USD render** (via Husk
> Standalone) and **USD export to disk**.  Both are designed to drop
> into a Houdini HDA so the user-facing entry point is a button on a
> tool node.

For the rest of our farm management — wake-on-LAN, dual-boot nodes,
shutdown jobs, autowake event plugin — see the companion repo
[`render-farm-control`](https://github.com/Gegenschuss/render-farm-control).

## What's in here

- **`submitter_husk.py`** — Submits a USD scene to the
  [HuskStandalone](https://github.com/pixel-ninja/HuskStandaloneSubmitter)
  Deadline plugin.  Karma renders only; per-frame output paths,
  pool/group/priority routing, optional pre-submit farm wake, optional
  Karma path-traced-samples / OptiX-denoiser overrides.
- **`submitter_usd_export.py`** — Submits a USD-export job to Deadline
  that runs `hython` on the farm to cook a LOP graph and write the
  resulting USD file.  Same path-mapping and farm-wake plumbing as the
  Husk submitter.
- **`secrets.example.py`** — Template for `secrets.py`, the
  per-workstation `PATH_MAP` that translates local Mac/Windows paths to
  the farm's Linux mount points.

Both submitters are pure Python and import only `hou` plus the standard
library — no other repo dependencies.

## Install

1. Clone the repo.
2. Run the installer from a terminal:

   - **macOS / Linux**: `./install.sh`
   - **Windows**: `install.bat`

   The installer locates Houdini's `hython`, runs `install_hda.py`, and
   writes both HDAs into `otls/`:
   `gegenschuss_husk_deadline_submitter.hda` and
   `gegenschuss_usd_deadline_submitter.hda`.  Override `hython` detection
   by setting `HYTHON` (or `set HYTHON=...` on Windows).

   The installer prompts for the install directory (defaults to the
   repo's `otls/`).  If the .hda files already exist, it asks before
   overwriting.

   **Optional: `install_secrets`** -- copy `install_secrets.example` to
   `install_secrets` and put your preferred install directory on a single
   line.  The installer will use it as the default (no need to type the
   path each time).  `install_secrets` is gitignored.

3. Load the HDAs into Houdini however you usually do.

4. For path remapping (workstation -> farm), copy `secrets.example.py`
   to `secrets.py` and fill in your `PATH_MAP`.  Place `secrets.py`
   anywhere on Houdini's `sys.path` (e.g. `$HOUDINI_USER_PREF_DIR/python3.x/`).
   Without it, paths pass through unchanged — fine if your workstation
   and farm share filesystem layout.

Each HDA embeds its backing `submitter_*.py` as a section, so the
`.hda` files are fully self-contained — copy them anywhere.  After
editing a submitter, re-run the installer to rebuild.

## Path mapping

Both submitters apply `PATH_MAP` to remap workstation paths to farm
paths before writing the Deadline job file.  Example:

```python
PATH_MAP = {
    "/Users/you/MyProject/": "/mnt/",
}
```

A USD path of `/Users/you/MyProject/scenes/foo.usd` becomes
`/mnt/scenes/foo.usd` on the farm.  Passthrough on Windows hosts.

## Recommended HDA parameters

Both submitters look for these parm names (with sensible fallbacks):

| Parm                       | Purpose                                                 |
|----------------------------|---------------------------------------------------------|
| `usd_file` (Husk)          | USD scene to render                                     |
| `target_lop_path` (export) | LOP node to cook (or wire to input 0)                   |
| `f1`, `f2`                 | Frame range start / end                                 |
| `batch_name`               | Deadline batch name                                     |
| `pool`                     | Deadline pool                                           |
| `deadline_group`           | Deadline group                                          |
| `priority`                 | Deadline priority                                       |
| `machine_limit`            | Concurrent worker cap                                   |
| `deadline_machine_list`    | Whitelist or blacklist (`machine_list_blacklist` flips) |
| `worker`                   | Specific worker name (overrides list)                   |
| `submit_suspended`         | Submit job in suspended state                           |
| `sanity_check` (Husk)      | Pre-flight assertions before submit                     |
| `wake_farm_on_submit`      | Run a wake script before submitting                     |
| `wake_farm_script[_args]`  | Path / args of the wake script                          |

The Husk submitter also exposes Karma overrides:

| Parm                              | Purpose                                  |
|-----------------------------------|------------------------------------------|
| `update_karma_render_settings`    | Apply per-job overrides                  |
| `pathtracedsamples_override`      | Override Karma path-traced samples       |
| `karma_denoiser`                  | `none` or `optix` (NVIDIA OptiX)         |

See the comment block at the top of each `.py` for the authoritative
list -- it stays in sync with the code.

## Licence

MIT for the Gegenschuss code in this repo.

`submitter_husk.py` targets the third-party
[HuskStandalone](https://github.com/pixel-ninja/HuskStandaloneSubmitter)
Deadline plugin by pixel-ninja, licensed under GPL-3.0 -- it is *not*
bundled here; the submitter only writes job files for it.
