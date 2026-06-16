import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

POLICY_ID = os.environ["POLICY_ID"]
ACCESS_LEVEL_NAME = os.environ.get("ACCESS_LEVEL_NAME", "vertex_ip_whitelist")


def build_cel(ips):
    ip_list = ", ".join(f"'{ip}/32'" for ip in ips)
    return f"inIpRange(origin.ip, [{ip_list}])"


def get_all_ips(config):
    ips = set()
    for ip in config.get("allowed_ips", {}).keys():
        ips.add(ip)
    for ip in config.get("admin_ips", {}).keys():
        ips.add(ip)
    return sorted(ips)


def get_access_token():
    response = requests.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def update_access_level(cel_expression):
    access_token = get_access_token()
    access_level_name = f"accessPolicies/{POLICY_ID}/accessLevels/{ACCESS_LEVEL_NAME}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Submit the PATCH — returns a long-running operation, not the final result
    patch_url = (
        f"https://accesscontextmanager.googleapis.com/v1/"
        f"{access_level_name}?updateMask=custom.expr"
    )
    payload = {
        "name": access_level_name,
        "title": ACCESS_LEVEL_NAME,
        "custom": {"expr": {"expression": cel_expression}},
    }

    print(f"Submitting PATCH to Access Context Manager...")
    response = requests.patch(patch_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    operation = response.json()

    op_name = operation.get("name")
    print(f"Operation submitted: {op_name}")

    # If GCP returned done:true immediately (rare but possible), return early
    if operation.get("done"):
        if "error" in operation:
            raise Exception(f"Operation failed immediately: {operation['error']}")
        print("Operation completed immediately")
        return operation.get("response", operation)

    # Poll until the operation completes
    op_url = f"https://accesscontextmanager.googleapis.com/v1/{op_name}"
    max_attempts = 30  # 30 x 2s = 60s max wait

    for attempt in range(1, max_attempts + 1):
        time.sleep(2)
        print(f"Polling operation status (attempt {attempt}/{max_attempts})...")

        op_response = requests.get(op_url, headers=headers, timeout=30)
        op_response.raise_for_status()
        op = op_response.json()

        if op.get("done"):
            if "error" in op:
                raise Exception(f"Operation failed: {op['error']}")
            print(f"Operation completed after {attempt * 2}s")
            return op.get("response", op)

    raise Exception(f"Operation timed out after {max_attempts * 2}s — check GCP console")


@app.route("/update", methods=["POST"])
def handle_update():
    data = request.get_json(silent=True)

    if not data or "config" not in data:
        return jsonify({"error": "Missing config"}), 400

    all_ips = get_all_ips(data["config"])

    if not all_ips:
        return jsonify({"error": "Empty IP list, refusing to update"}), 400

    cel = build_cel(all_ips)
    print(f"Updating access level with {len(all_ips)} IPs: {all_ips}")
    print(f"CEL: {cel}")

    try:
        result = update_access_level(cel)
        return jsonify({
            "status": "success",
            "ips_applied": all_ips,
            "cel": cel,
            "result": result,
        })
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)