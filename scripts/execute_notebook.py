"""Execute the notebook with the active Python environment, using a temporary kernel."""

import json
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks" / "report.ipynb"
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    with tempfile.TemporaryDirectory(prefix="retailpulse-kernel-") as temporary:
        kernel_dir = Path(temporary) / "retailpulse-local"
        kernel_dir.mkdir()
        spec = {
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "RetailPulse local Python", "language": "python",
            "env": {"PYTHONIOENCODING": "utf-8"},
        }
        (kernel_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
        manager = KernelManager(kernel_name="retailpulse-local", kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporary]))
        client = NotebookClient(nb, km=manager, timeout=180, resources={"metadata": {"path": str(root / "notebooks")}})
        client.execute()
    # Restore a portable kernel name and remove host-specific environment paths.
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.validate(nb)
    nbformat.write(nb, path)
    errors = [output for cell in nb.cells if cell.cell_type == "code" for output in cell.outputs if output.output_type == "error"]
    if errors:
        raise RuntimeError(f"Notebook contains {len(errors)} error outputs")
    print(f"Executed {sum(c.cell_type == 'code' for c in nb.cells)} code cells with zero errors: {path.name}")


if __name__ == "__main__":
    main()
