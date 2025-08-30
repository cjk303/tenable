from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import subprocess
import tempfile
import os
import shlex

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

PLAYBOOK_FILE = "deploy_nessus_agent.yml"

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@socketio.on("run_playbook")
def run_playbook(data):
    activation_key = data.get("activation_key", "").strip()
    groups = data.get("groups", "").strip()
    mode = data.get("mode", "cloud")
    manager_host = data.get("manager_host", "").strip()
    manager_port = data.get("manager_port", "8834").strip()
    escalate_method = data.get("escalate_method", "sudo")
    hosts_text = data.get("hosts", "").strip()

    # Build temporary inventory file
    tmp_inv = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".ini")
    tmp_inv.write("[agents]\n")
    for line in hosts_text.splitlines():
        if line.strip():
            tmp_inv.write(line.strip() + "\n")
    tmp_inv.close()

    # Build extra vars
    extra_vars = {
        "activation_key": activation_key,
        "groups": groups,
        "mode": mode,
        "manager_host": manager_host,
        "manager_port": manager_port,
        "escalate_method": escalate_method,
    }

    extra_vars_args = []
    for k, v in extra_vars.items():
        if v:
            extra_vars_args.extend(["-e", f"{k}={shlex.quote(v)}"])

    cmd = ["ansible-playbook", "-i", tmp_inv.name, PLAYBOOK_FILE] + extra_vars_args
    emit("log", {"line": f"▶ Running: {' '.join(cmd)}"})

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        for line in proc.stdout:
            emit("log", {"line": line.rstrip()})
            socketio.sleep(0.01)  # allow async flush

        proc.wait()
        if proc.returncode == 0:
            emit("status", {"ok": True, "msg": "✅ Deployment completed successfully"})
        else:
            emit("status", {"ok": False, "msg": f"❌ Deployment failed (exit code {proc.returncode})"})

    except Exception as e:
        emit("status", {"ok": False, "msg": f"Error: {e}"})
    finally:
        os.unlink(tmp_inv.name)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8443, debug=True)
