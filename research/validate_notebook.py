"""Run the notebook in two fresh Jupyter kernels and check rendered exports.

The default uses Jupyter in-process message channels in separate Python processes.
Use --transport tcp to test a standalone ZeroMQ kernel on a compatible host.

Run from the project root with python -m research.validate_notebook.
The current Python interpreter supplies the kernel; no global registration is needed.
"""
import base64
import hashlib
import json
import platform
import argparse
from contextlib import chdir
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

from ipykernel.inprocess.manager import InProcessKernelManager
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager
import nbformat
from nbclient import NotebookClient
import pandas as pd
from PIL import Image

from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT = Path(__file__).resolve().parents[1]


def execute_inprocess(notebook):
    """Execute Jupyter messages in a new kernel, retaining rich output MIME data."""
    manager = InProcessKernelManager()
    manager.start_kernel()
    client = manager.client()
    client.start_channels()
    manager.kernel.shell.enable_matplotlib("inline")
    try:
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            message_id = client.execute(cell.source, store_history=True)
            reply = client.get_shell_msg()["content"]
            if reply["status"] != "ok":
                raise RuntimeError(f"Kernel execution failed: {reply}")
            cell.execution_count = reply["execution_count"]
            while client.iopub_channel.msg_ready():
                message = client.get_iopub_msg()
                if message["parent_header"].get("msg_id") != message_id:
                    continue
                kind, content = message["header"]["msg_type"], message["content"]
                if kind in ("stream", "display_data", "execute_result", "error"):
                    cell.outputs.append(nbformat.v4.output_from_msg(message))
                elif kind == "clear_output":
                    cell.outputs = []
        return notebook
    finally:
        client.stop_channels()
        manager.shutdown_kernel()


def validate_case(destination, edited=False, transport="inprocess"):
    """Execute a cleared notebook with isolated inputs and verify every artifact."""
    with tempfile.TemporaryDirectory(prefix='secondorder-kernel-') as directory:
        project = Path(directory)
        for path in ROOT.glob('*.py'):
            shutil.copy2(path, project / path.name)
        shutil.copytree(ROOT / 'data', project / 'data')
        if edited:
            source = project / 'data/scenarios.json'
            payload = json.loads(source.read_text(encoding='utf-8'))
            payload['scenarios'][1].update(ubi=750, tax=15)
            source.write_text(json.dumps(payload), encoding='utf-8')
        kernel_dir = project / 'kernels' / 'validation'
        kernel_dir.mkdir(parents=True)
        (kernel_dir / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'SecondOrder validation', 'language': 'python',
            'env': {'MPLBACKEND': 'module://matplotlib_inline.backend_inline'},
        }), encoding='utf-8')
        manager = AsyncKernelManager(kernel_name='validation',
            kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(project / 'kernels')]))
        notebook = nbformat.read(ROOT / 'main.ipynb', as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                cell.outputs = []
                cell.execution_count = None
        if transport == 'tcp':
            # Close the externally supplied manager before deleting its working directory.
            client = NotebookClient(notebook, timeout=120, km=manager,
                resources={'metadata': {'path': str(project)}})
            client.execute(cleanup_kc=True)
        else:
            with chdir(project):
                execute_inprocess(notebook)
        cells = [cell for cell in notebook.cells if cell.cell_type == 'code']
        if [cell.execution_count for cell in cells] != list(range(1, len(cells) + 1)):
            raise ValueError('Notebook cells did not execute in order')
        images = [output['data']['image/png'] for cell in cells for output in cell.outputs
                  if 'image/png' in output.get('data', {})]
        if not images:
            raise ValueError('Notebook produced no inline PNG display')
        output = project / 'outputs'
        config = json.loads((output / 'ubi_500.config.json').read_text(encoding='utf-8'))
        expected_ubi, expected_tax = (750, 15) if edited else (500, 0)
        if (config['scenario']['ubi'], config['scenario']['tax']) != (expected_ubi, expected_tax):
            raise ValueError('Notebook ignored the edited JSON input')
        simulator = ScenarioSimulator(EconomicScenario(**config['scenario']),
            ModelAssumptions(**config['assumptions']), config['years'])
        pd.testing.assert_frame_equal(pd.read_csv(output / 'ubi_500.csv'),
                                      simulator.run(), check_dtype=False)
        with Image.open(output / 'policy_comparison.png') as image:
            if image.size != (1540, 560):
                raise ValueError('Unexpected comparison plot dimensions')
            image.verify()
        destination.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, destination / 'executed.ipynb')
        for name in ('policy_comparison.png', 'ubi_500.csv', 'ubi_500.config.json'):
            shutil.copy2(output / name, destination / name)
        (destination / 'inline.png').write_bytes(base64.b64decode(images[0]))
        return {'status': 'passed', 'code_cells': len(cells),
                'execution_counts': [cell.execution_count for cell in cells],
                'inline_pngs': len(images), 'ubi': expected_ubi, 'tax': expected_tax,
                'csv_rows': len(simulator.run()), 'csv_sidecar_reconstruction': 'passed'}


def validate_notebook(transport="inprocess"):
    """Save evidence only after both clean-kernel executions succeed."""
    destination = ROOT / 'outputs/notebook_validation'
    results = {}
    for name, edited in [('default', False), ('edited', True)]:
        command = [sys.executable, '-m', 'research.validate_notebook', '--worker',
                   '--case', name, '--transport', transport]
        subprocess.run(command, cwd=ROOT, check=True, timeout=180)
        results[name] = json.loads((destination / name / 'result.json').read_text())
    paths = ['main.ipynb', 'scenario.py', 'simulator.py', 'analysis.py',
             'io_utils.py', 'visualization.py', 'data/scenarios.json',
             'research/validate_notebook.py']
    report = {'status': 'passed', 'transport': transport, 'isolation': 'fresh Python child process for each case', 'platform': platform.platform(),
              'python': platform.python_version(), 'cases': results,
              'source_hashes': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                for path in paths}}
    report['output_hashes'] = {path.relative_to(destination).as_posix():
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(destination.rglob('*'))
        if path.is_file() and path.name != 'validation.json'}
    (destination / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=['inprocess', 'tcp'], default='inprocess')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--case', choices=['default', 'edited'])
    args = parser.parse_args()
    if args.worker:
        destination = ROOT / 'outputs/notebook_validation' / args.case
        result = validate_case(destination, args.case == 'edited', args.transport)
        (destination / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    else:
        print(json.dumps(validate_notebook(args.transport), indent=2))
