import os
import json
from flask import Flask, request, jsonify
from google.cloud import accesscontextmanager_v1
from google.protobuf import field_mask_pb2

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


def update_access_level(cel_expression):
    client = accesscontextmanager_v1.AccessContextManagerClient()
    path = f"accessPolicies/{POLICY_ID}/accessLevels/{ACCESS_LEVEL_NAME}"

    access_level = accesscontextmanager_v1.AccessLevel(
        name=path,
        custom=accesscontextmanager_v1.CustomLevel(
            expr={"expression": cel_expression}
        ),
    )

    operation = client.update_access_level(
        accesscontextmanager_v1.UpdateAccessLevelRequest(
            access_level=access_level,
            update_mask=field_mask_pb2.FieldMask(paths=["custom.expr"]),
        )
    )
    result = operation.result(timeout=300)
    return result.name


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
        return jsonify({"status": "success", "ips": all_ips, "access_level": result})
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)