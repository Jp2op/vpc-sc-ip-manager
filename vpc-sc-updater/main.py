import os
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
    metadata_url = (
        "http://metadata.google.internal/computeMetadata/v1/"
        "instance/service-accounts/default/token"
    )

    response = requests.get(
        metadata_url,
        headers={"Metadata-Flavor": "Google"},
        timeout=30,
    )

    response.raise_for_status()
    return response.json()["access_token"]


def update_access_level(cel_expression):
    access_token = get_access_token()

    access_level_name = (
        f"accessPolicies/{POLICY_ID}/accessLevels/{ACCESS_LEVEL_NAME}"
    )

    url = (
        f"https://accesscontextmanager.googleapis.com/v1/"
        f"{access_level_name}"
        f"?updateMask=custom.expr"
    )

    payload = {
        "name": access_level_name,
        "title": ACCESS_LEVEL_NAME,
        "custom": {
            "expr": {
                "expression": cel_expression
            }
        }
    }

    response = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


@app.route("/update", methods=["POST"])
def handle_update():
    data = request.get_json(silent=True)

    if not data or "config" not in data:
        return jsonify({"error": "Missing config"}), 400

    all_ips = get_all_ips(data["config"])

    if not all_ips:
        return jsonify({"error": "Empty IP list, refusing"}), 400

    cel = build_cel(all_ips)

    print(f"Updating with {len(all_ips)} IPs: {all_ips}")
    print(f"CEL: {cel}")

    try:
        result = update_access_level(cel)

        return jsonify({
            "status": "success",
            "ips": all_ips,
            "result": result
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