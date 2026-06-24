#!/usr/bin/env bash
#
# install.sh -- macOS / Linux installer for the Husk + USD-Export
# Deadline submitter HDAs.
#
# Locates Houdini's hython, runs install_hda.py, and writes two .hda
# files to the chosen output directory.
#
# Override hython detection by exporting HYTHON before running.
#
set -euo pipefail

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_PY="$HERE/install_hda.py"
DEFAULT_OUT_DIR="$HERE/otls"
DEFAULT_LABEL="inside repo"
SECRETS_AUTHORIZED=0

# Filenames produced by install_hda.py -- kept in sync.
HDA_FILES=(
    "gegenschuss_husk_deadline_submitter.hda"
    "gegenschuss_usd_deadline_submitter.hda"
)

if [[ ! -f "$INSTALL_PY" ]]; then
    echo "install_hda.py not found next to this script ($HERE)." >&2
    exit 1
fi

# Optional install_secrets override: first non-comment, non-blank line
# is a local default directory.  Gitignored, never published.
if [[ -f "$HERE/install_secrets" ]]; then
    SECRET_PATH=$(awk '!/^[[:space:]]*#/ && !/^[[:space:]]*$/ {print; exit}' "$HERE/install_secrets" | tr -d '\r')
    if [[ -n "$SECRET_PATH" ]]; then
        SECRET_PATH="${SECRET_PATH/#\~/$HOME}"
        DEFAULT_OUT_DIR="${SECRET_PATH%/}"
        DEFAULT_LABEL="from install_secrets"
        SECRETS_AUTHORIZED=1
    fi
fi

# ----- Choose install location -------------------------------------------
echo "Where should the HDAs install?"
echo
echo "  [1] $DEFAULT_OUT_DIR/   (default, $DEFAULT_LABEL)"
echo "  [2] Custom directory"
echo
read -r -p "Choice [1]: " CHOICE
CHOICE="${CHOICE:-1}"

case "$CHOICE" in
    1) OUT_DIR="$DEFAULT_OUT_DIR" ;;
    2)
        read -r -p "Directory: " CUSTOM
        if [[ -z "$CUSTOM" ]]; then
            echo "Empty path; cancelled." >&2
            exit 1
        fi
        CUSTOM="${CUSTOM/#\~/$HOME}"
        [[ "$CUSTOM" != /* ]] && CUSTOM="$PWD/$CUSTOM"
        OUT_DIR="${CUSTOM%/}"
        ;;
    *)
        echo "Invalid choice." >&2
        exit 1
        ;;
esac

# ----- Outside-repo confirm ----------------------------------------------
# Skipped when the user is taking the install_secrets default -- they
# pre-authorized that path by writing it into install_secrets.
case "$OUT_DIR" in
    "$HERE"/*) ;;
    *)
        if [[ "$SECRETS_AUTHORIZED" == "1" && "$CHOICE" == "1" ]]; then
            : # secrets-authorized default
        else
            echo
            echo "This will create files OUTSIDE the repo:"
            echo "  $OUT_DIR/"
            read -r -p "Proceed? [y/N]: " YN
            case "$YN" in
                [Yy]|[Yy][Ee][Ss]) ;;
                *) echo "Cancelled."; exit 0 ;;
            esac
        fi
        ;;
esac

# ----- Replace-existing check --------------------------------------------
EXISTING=()
for fn in "${HDA_FILES[@]}"; do
    [[ -f "$OUT_DIR/$fn" ]] && EXISTING+=("$OUT_DIR/$fn")
done
if (( ${#EXISTING[@]} > 0 )); then
    echo
    echo "These files already exist:"
    printf '  %s\n' "${EXISTING[@]}"
    read -r -p "Replace? [Y/n]: " YN
    case "$YN" in
        [Nn]|[Nn][Oo]) echo "Cancelled."; exit 0 ;;
        *) ;;
    esac
fi

# ----- Find hython -------------------------------------------------------
find_hython() {
    if [[ -n "${HYTHON:-}" ]]; then
        echo "$HYTHON"; return 0
    fi
    if command -v hython >/dev/null 2>&1; then
        command -v hython; return 0
    fi
    local found
    case "$(uname -s)" in
        Darwin)
            found=$(find /Applications/Houdini -maxdepth 9 -type f -name hython 2>/dev/null \
                    | sort -V | tail -1)
            ;;
        Linux)
            found=$(find /opt /usr/local -maxdepth 4 -type f -name hython 2>/dev/null \
                    | sort -V | tail -1)
            ;;
    esac
    [[ -n "$found" ]] && { echo "$found"; return 0; }
    return 1
}

HYTHON_BIN=$(find_hython) || {
    cat >&2 <<EOF
Could not find hython.

Set HYTHON to your hython path and re-run, e.g.:
  macOS:   HYTHON=/Applications/Houdini/Houdini21.0.671/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython ./install.sh
  Linux:   HYTHON=/opt/hfs21.0/bin/hython ./install.sh
EOF
    exit 1
}

mkdir -p "$OUT_DIR"

echo
echo "hython:    $HYTHON_BIN"
echo "script:    $INSTALL_PY"
echo "out dir:   $OUT_DIR"
echo

"$HYTHON_BIN" "$INSTALL_PY" "$OUT_DIR"
