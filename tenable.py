from flask import Flask, render_template, request, Response
import subprocess
import tempfile
import os

app = Flask(__name__)

PLAYBOOK_FILE = "deploy_nessus_agent.yml"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        hosts_input = request.form["hosts"].strip()
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        activation_key = request.form["activation_key"].strip()
        groups = request.form["groups"].strip()
        mode = request.form["mode"]
        manager_host = request.form["manager_host"].strip()
        manager_port = request.form["manager_port"].strip()
        escalate_method = request.form["escalate_method"]

        # Create ephemeral inventory
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp_inv:
            tmp_inv.write("[agents]\n")
            for line in hosts_input.splitlines():
                line = line.strip()
                if line:
                    tmp_inv.write(f"{line} ansible_user={username}\n")
            tmp_inv_name = tmp_inv.name

        # Build ansible-playbook command
        cmd = [
            "ansible-playbook",
            "-i", tmp_inv_name,
            PLAYBOOK_FILE,
            "-e", f"activation_key={activation_key}",
            "-e", f"groups={groups}",
            "-e", f"mode={mode}",
            "-e", f"manager_host={manager_host}",
            "-e", f"manager_port={manager_port}",
            "-e", f"escalate_method={escalate_method}",
            "-e", f"ansible_user={username}",
            "-e", f"ansible_password={password}",
            "-e", f"ansible_become_password={password}"
        ]

        def generate():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )
                for line in iter(process.stdout.readline, ""):
                    yield line
                process.stdout.close()
                process.wait()
            finally:
                if os.path.exists(tmp_inv_name):
                    os.unlink(tmp_inv_name)

        return Response(generate(), mimetype="text/plain")

    return render_template("index.html")


if __name__ == "__main__":
    # Runs on all interfaces at port 8443
    app.run(host="0.0.0.0", port=8443, debug=True)
