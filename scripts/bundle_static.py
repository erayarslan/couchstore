#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile

def bundle(output_path, input_libs):
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".mri", delete=False) as f:
        mri_file = f.name
        f.write(f"create {output_path}\n")
        for lib in input_libs:
            lib_path = os.path.abspath(lib)
            if os.path.exists(lib_path):
                f.write(f"addlib {lib_path}\n")
            else:
                print(f"[bundle_static] Warning: static library not found: {lib_path}", file=sys.stderr)
        f.write("save\n")
        f.write("end\n")

    try:
        with open(mri_file, "r") as stdin:
            subprocess.check_call(["ar", "-M"], stdin=stdin)

        subprocess.run(["ar", "-d", output_path, "ExceptionTracerLib.cpp.o"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.run(["strip", "-g", output_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.run(["ranlib", output_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"[bundle_static] Successfully created static archive: {output_path} ({os.path.getsize(output_path)} bytes)")
    finally:
        if os.path.exists(mri_file):
            os.remove(mri_file)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <output.a> <input1.a> [input2.a ...]", file=sys.stderr)
        sys.exit(1)
    bundle(sys.argv[1], sys.argv[2:])
