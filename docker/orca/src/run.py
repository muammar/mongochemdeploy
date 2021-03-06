import os
import subprocess
import jinja2
import json

import openchemistry as oc


def run_calculation(geometry_file, output_file, params, scratch_dir):
    # Read in the geometry from the geometry file
    # This container expects the geometry file to be in .xyz format
    with open(geometry_file) as f:
        xyz_structure = f.read()
        # remove the first two lines in the xyz file
        # (i.e. number of atom and optional comment)
        xyz_structure = xyz_structure.split("\n")[2:]
        xyz_structure = "\n  ".join(xyz_structure)

    # Read the input parameters
    theory = params.get("theory", "hf")
    task = params.get("task", "energy")
    basis = params.get("basis", "cc-pvdz")
    functional = params.get("functional", "b3lyp")
    charge = params.get("charge", 0)
    multiplicity = params.get("multiplicity", 1)

    theory = theory.lower()
    if theory == "hf":
        _theory = "hf"
    else:
        _theory = functional

    task = task.lower()

    if task == "freq":
        _task = "{} {}".format("Opt", "Freq")
    elif task == "optimize":
        _task = "{}".format("Opt")
    else:  # single point energy
        _task = ""

    context = {
        "task": _task,
        "theory": _theory,
        "functional": functional,
        "charge": charge,
        "multiplicity": multiplicity,
        "basis": basis,
    }

    if theory == "hf":
        del context["functional"]

    # Combine the input parameters and geometry into a concrete input file
    # that can be executed by the simulation code
    template_path = os.path.dirname(__file__)
    jinja2_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path), trim_blocks=True
    )

    os.makedirs(scratch_dir, exist_ok=True)
    os.chdir(scratch_dir)
    raw_input_file = os.path.join(scratch_dir, "raw.in")
    raw_output_file = os.path.join(scratch_dir, "raw.out")

    with open(raw_input_file, "wb") as f:
        jinja2_env.get_template("orca.in.j2").stream(
            **context, xyz_structure=xyz_structure
        ).dump(f, encoding="utf8")

    # Execute the code and write to output
    with open(raw_output_file, "wb") as output:
        subprocess.run(["orca", raw_input_file], stdout=output)

    # Convert the raw output file generated by the code execution, into the
    # output format declared in the container description (cjson)

    cjson = oc.OrcaReader(raw_output_file).read()

    cjson["inputParameters"] = params

    with open(output_file, "w") as f:
        json.dump(cjson, f)
