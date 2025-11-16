import os
import subprocess


# Executes a Python script in a specific virtual environment.
# abs_repo_path: str - absolute path to the repository
# wd: str - working directory for execution
# venv: str - name or path of the virtual environment folder
# script_path: str - path to the Python script to execute
# *args: str - additional arguments to pass to the script
def exec_python_script_from_venv(
    abs_repo_path: str, wd: str, venv: str, script_path: str, *args: str
):
    cwd = os.getcwd()
    interpreter = "%s/%s/bin/python" % (abs_repo_path, venv)
    command = [interpreter, script_path] + list(args)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=wd,
        env={**os.environ, "MPLBACKEND": "agg"},
    )
    if len(result.stdout) > 0:
        print("stdout:", result.stdout)
    if len(result.stderr) > 0:
        print("stderr:", result.stderr)
    os.chdir(cwd)
