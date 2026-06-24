"""
install_hda.py

Builds the two Solaris LOP HDAs in this repo:

    gegenschuss::husk_deadline_submitter::1.0
    gegenschuss::usd_deadline_submitter::1.0

Each HDA embeds its own backing Python module (submitter_husk.py /
submitter_usd_export.py) as a section so the .hda is fully
self-contained -- copy it anywhere, drop into Houdini, and it works.
The Gegenschuss logo is embedded as the icon section.

Usage (from a terminal):

    hython install_hda.py /path/to/output_dir

    # produces:
    #   /path/to/output_dir/gegenschuss_husk_deadline_submitter.hda
    #   /path/to/output_dir/gegenschuss_usd_deadline_submitter.hda

Or call from inside Houdini's Python source editor:

    exec(open("/path/to/install_hda.py").read())
    install_hda("/path/to/output_dir")
"""

import os


# ----- HDA constants -----

HUSK_HDA_TYPE  = "gegenschuss::husk_deadline_submitter::1.0"
HUSK_HDA_LABEL = "Gegenschuss Husk -> Deadline"
HUSK_HDA_DESC  = (
    "Submits a USD scene to Deadline via the HuskStandalone plugin. "
    "Karma renders only; per-frame output, pool/group routing, optional "
    "pre-submit farm wake."
)
HUSK_MODULE_NAME    = "submitter_husk"
HUSK_MODULE_FILE    = "submitter_husk.py"
HUSK_OUT_FILENAME   = "gegenschuss_husk_deadline_submitter.hda"

USD_EXPORT_HDA_TYPE  = "gegenschuss::usd_deadline_submitter::1.0"
USD_EXPORT_HDA_LABEL = "Gegenschuss USD Export -> Deadline"
USD_EXPORT_HDA_DESC  = (
    "Submits a hython USD-export job to Deadline. Cooks a target LOP node "
    "on the farm and writes the resulting USD file."
)
USD_EXPORT_MODULE_NAME  = "submitter_usd_export"
USD_EXPORT_MODULE_FILE  = "submitter_usd_export.py"
USD_EXPORT_OUT_FILENAME = "gegenschuss_usd_deadline_submitter.hda"


# ----- PythonModule wrappers -----
#
# Each HDA's PythonModule resolves the embedded section, exec's it into
# a fresh module, and exposes thin wrappers that the button callbacks
# call via hou.phm().<wrapper>(kwargs).  Pattern matches the AE Export
# HDA -- self-contained by default, override via `module_path` parm
# during development.

PYTHON_MODULE_HEADER = '''\
"""HDA backing module -- delegates to {MODULE_NAME}.

The submitter source is embedded in this HDA as a section ({MODULE_FILE}),
so the HDA is fully self-contained.  Pass an explicit path via the
`module_path` parameter to override with a live disk copy during
development.
"""

import os
import sys
import types
import importlib

MODULE_NAME = "{MODULE_NAME}"
MODULE_SECTION = "{MODULE_FILE}"


def _module_from_string(name, source):
    mod = types.ModuleType(name)
    mod.__file__ = "<embedded:%s>" % name
    exec(compile(source, mod.__file__, "exec"), mod.__dict__)
    return mod


def _resolve_module(node):
    # 1. Live disk override.
    explicit = node.parm("module_path").evalAsString().strip() if node.parm("module_path") else ""
    if explicit:
        path = os.path.normpath(explicit)
        if not os.path.isfile(path):
            raise RuntimeError("module_path is not a file: " + path)
        d = os.path.dirname(path)
        if d not in sys.path:
            sys.path.insert(0, d)
        if MODULE_NAME in sys.modules:
            importlib.reload(sys.modules[MODULE_NAME])
        return importlib.import_module(MODULE_NAME)

    # 2. Embedded section -- the default.
    defn = node.type().definition()
    if defn is not None:
        section = defn.sections().get(MODULE_SECTION)
        if section is not None:
            return _module_from_string(MODULE_NAME, section.contents())

    raise RuntimeError(
        MODULE_SECTION + " section is missing from this HDA.  Re-run "
        "install_hda.py to rebuild with the embedded module."
    )

'''

PYTHON_MODULE_HUSK = PYTHON_MODULE_HEADER.format(
    MODULE_NAME=HUSK_MODULE_NAME,
    MODULE_FILE=HUSK_MODULE_FILE,
) + '''

def submit_to_deadline(kwargs):
    """Button callback: kwargs['node'].hdaModule().submit_to_deadline(kwargs)."""
    mod = _resolve_module(kwargs["node"])
    return mod.submit_to_deadline(kwargs)
'''

PYTHON_MODULE_USD_EXPORT = PYTHON_MODULE_HEADER.format(
    MODULE_NAME=USD_EXPORT_MODULE_NAME,
    MODULE_FILE=USD_EXPORT_MODULE_FILE,
) + '''

def submit_usd_export_to_deadline(kwargs):
    """Button callback: hou.phm().submit_usd_export_to_deadline(kwargs)."""
    mod = _resolve_module(kwargs["node"])
    return mod.submit_usd_export_to_deadline(kwargs)


def set_target_from_selection(kwargs):
    """Button callback: hou.phm().set_target_from_selection(kwargs)."""
    mod = _resolve_module(kwargs["node"])
    return mod.set_target_from_selection(kwargs)
'''


# ----- Parameter template builders -----
#
# Mirrors the user's hand-built HDAs.  Parm names match what the
# submitter scripts expect (see the comment block at the top of each
# submitter for the contract).

def _build_husk_param_template_group():
    import hou
    g = hou.ParmTemplateGroup()

    g.append(hou.StringParmTemplate(
        "usd_file", "USD File", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Any,
        tags={"filechooser_pattern": "*.usd *.usda *.usdc *.usdz"},
        help="USD scene to render.  Often `chs(\"../usd_rop/lopoutput\")` "
             "to read from a sibling USD ROP.",
    ))

    g.append(hou.ToggleParmTemplate(
        "sequence_single_job", "Submit Sequence as Single Job",
        default_value=True,
    ))

    g.append(hou.IntParmTemplate(
        "f", "Frame Range", 2, default_value=(1, 100),
    ))

    g.append(hou.IntParmTemplate(
        "chunk_size", "Frames per Task", 1, default_value=(10,), min=1,
    ))

    g.append(hou.StringParmTemplate(
        "batch_name", "Batch Name", 1, default_value=("$HIPNAME.$OS",),
    ))

    g.append(hou.SeparatorParmTemplate("sep_render"))

    g.append(hou.MenuParmTemplate(
        "renderer", "Renderer",
        menu_items=("xpu", "cpu"),
        menu_labels=("Karma XPU", "Karma CPU"),
        default_value=0,
    ))

    g.append(hou.StringParmTemplate(
        "camera", "Camera Override", 1, default_value=("",),
        help="Optional. USD camera prim path override (e.g. /world/cam).",
    ))

    g.append(hou.SeparatorParmTemplate("sep_farm"))

    g.append(hou.StringParmTemplate(
        "group", "Group", 1, default_value=("houdini",),
    ))
    g.append(hou.StringParmTemplate(
        "deadline_machine_list", "Machine List", 1, default_value=("",),
    ))
    g.append(hou.ToggleParmTemplate(
        "sanity_check", "Sanity Check (Requires existing files)",
        default_value=False,
    ))
    g.append(hou.ToggleParmTemplate(
        "wake_farm_command", "Trigger Script on Submit",
        default_value=False,
    ))
    g.append(hou.StringParmTemplate(
        "wake_farm_script", "Path to Script", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        disable_when="{ wake_farm_command == 0 }",
    ))
    g.append(hou.ToggleParmTemplate(
        "submit_suspended", "Submit Suspended", default_value=False,
    ))

    g.append(hou.SeparatorParmTemplate("sep_submit"))
    g.append(hou.ButtonParmTemplate(
        "execute", "Submit to Deadline",
        script_callback="hou.phm().submit_to_deadline(kwargs)",
        script_callback_language=hou.scriptLanguage.Python,
    ))

    return g


def _build_usd_export_param_template_group():
    import hou
    g = hou.ParmTemplateGroup()

    g.append(hou.StringParmTemplate(
        "target_lop_path", "USD ROP", 1, default_value=("",),
        string_type=hou.stringParmType.NodeReference,
        tags={"oprelative": ".", "opfilter": "!!LOP!!"},
        help="LOP node to cook on the farm.  Or wire it into the input "
             "of this HDA -- the submitter checks both.",
    ))
    g.append(hou.ButtonParmTemplate(
        "pick_target", "Pick Target",
        script_callback="hou.phm().set_target_from_selection(kwargs)",
        script_callback_language=hou.scriptLanguage.Python,
    ))

    g.append(hou.IntParmTemplate(
        "f1", "Start Frame", 1, default_value=(1,),
    ))
    g.append(hou.IntParmTemplate(
        "f2", "End Frame", 1, default_value=(100,),
    ))
    g.append(hou.IntParmTemplate(
        "chunk_size", "Chunk Size", 1, default_value=(100,), min=1,
    ))

    g.append(hou.SeparatorParmTemplate("sep_job"))

    g.append(hou.StringParmTemplate(
        "batch_name", "Batch Name", 1, default_value=("$HIPNAME.$OS",),
    ))
    g.append(hou.StringParmTemplate(
        "worker", "Worker", 1, default_value=("",),
        help="Optional. Specific Deadline worker to pin to.",
    ))
    g.append(hou.StringParmTemplate(
        "machine_list", "Machine List", 1, default_value=("",),
    ))
    g.append(hou.StringParmTemplate(
        "group", "Group", 1, default_value=("",),
    ))
    g.append(hou.IntParmTemplate(
        "priority", "Priority", 1, default_value=(50,), min=0, max=100,
    ))
    g.append(hou.IntParmTemplate(
        "machine_limit", "Machine Limit", 1, default_value=(0,), min=0,
        help="0 = no limit.",
    ))
    g.append(hou.StringParmTemplate(
        "comment", "Comment", 1, default_value=("",),
    ))

    g.append(hou.SeparatorParmTemplate("sep_farm"))

    g.append(hou.ToggleParmTemplate(
        "sanity_check", "Sanity Check", default_value=False,
    ))
    g.append(hou.ToggleParmTemplate(
        "wake_farm_command", "Trigger Script on Submit",
        default_value=False,
    ))
    g.append(hou.StringParmTemplate(
        "wake_farm_script", "Path to Script", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        disable_when="{ wake_farm_command == 0 }",
    ))
    g.append(hou.ToggleParmTemplate(
        "submit_suspended", "Submit Suspended", default_value=False,
    ))

    g.append(hou.SeparatorParmTemplate("sep_submit"))
    g.append(hou.ButtonParmTemplate(
        "submit_deadline", "Submit",
        script_callback="hou.phm().submit_usd_export_to_deadline(kwargs)",
        script_callback_language=hou.scriptLanguage.Python,
    ))

    return g


# ----- Per-HDA build helper -----

def _install_one_hda(hda_type, hda_label, hda_desc, parm_template_builder,
                     python_module_text, embed_module_path, embed_module_section,
                     out_hda_path, icon_path):
    """Single HDA build.  Caller runs this twice -- once per submitter."""
    import hou

    out_hda_path = os.path.abspath(out_hda_path)
    out_dir = os.path.dirname(out_hda_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    stage_root = hou.node("/stage")
    if stage_root is None:
        raise RuntimeError("/stage network not present.  Open a Houdini scene with Solaris support.")

    seed = stage_root.createNode("pythonscript", "_dl_seed")
    try:
        hda_node = seed.createDigitalAsset(
            name=hda_type,
            hda_file_name=out_hda_path,
            description=hda_label,
            min_num_inputs=0,
            max_num_inputs=1,
            ignore_external_references=True,
            change_node_type=True,
            create_backup=False,
        )
        defn = hda_node.type().definition()
        defn.setParmTemplateGroup(parm_template_builder())
        defn.addSection("PythonModule", python_module_text)
        defn.setExtraInfo(hda_desc)

        # Embed the icon.
        if icon_path and os.path.isfile(icon_path):
            ext = os.path.splitext(icon_path)[1].lower()
            section_name = "icon" + ext
            with open(icon_path, "rb") as f:
                defn.addSection(section_name, f.read())
            defn.setIcon("opdef:.?" + section_name)

        # Embed the submitter module.
        if embed_module_path and os.path.isfile(embed_module_path):
            with open(embed_module_path, "r", encoding="utf-8") as f:
                defn.addSection(embed_module_section, f.read())

        opts = defn.options()
        opts.setSaveCachedCode(False)
        defn.setOptions(opts)
        defn.save(out_hda_path, hda_node, opts)
    finally:
        try: hda_node.destroy()
        except Exception: pass
        try: seed.destroy()
        except Exception: pass

    hou.hda.installFile(out_hda_path)
    return out_hda_path


# ----- Entry point -----

def install_hda(out_dir):
    """Build both HDAs into `out_dir`.  Returns the two output paths."""
    out_dir = os.path.abspath(out_dir)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        here = os.getcwd()

    icon_path = os.path.join(here, "Gegenschuss.png")
    icon_path = icon_path if os.path.isfile(icon_path) else None

    husk_module    = os.path.join(here, HUSK_MODULE_FILE)
    usd_export_mod = os.path.join(here, USD_EXPORT_MODULE_FILE)

    husk_out = _install_one_hda(
        HUSK_HDA_TYPE, HUSK_HDA_LABEL, HUSK_HDA_DESC,
        _build_husk_param_template_group, PYTHON_MODULE_HUSK,
        husk_module, HUSK_MODULE_FILE,
        os.path.join(out_dir, HUSK_OUT_FILENAME), icon_path,
    )

    usd_export_out = _install_one_hda(
        USD_EXPORT_HDA_TYPE, USD_EXPORT_HDA_LABEL, USD_EXPORT_HDA_DESC,
        _build_usd_export_param_template_group, PYTHON_MODULE_USD_EXPORT,
        usd_export_mod, USD_EXPORT_MODULE_FILE,
        os.path.join(out_dir, USD_EXPORT_OUT_FILENAME), icon_path,
    )

    return [husk_out, usd_export_out]


if __name__ == "__main__":
    # `hython install_hda.py /path/to/output_dir` -- safe in scripts; never
    # sys.exit() because that terminates Houdini when this is exec()'d
    # from inside Houdini's Python console.
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] not in ("-h", "--help"):
        paths = install_hda(sys.argv[1])
        for p in paths:
            print("Installed HDA: {}".format(p))
    else:
        print("install_hda.py loaded.  Call install_hda('/path/to/output_dir') "
              "to build both HDAs.")
