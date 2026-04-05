"""Simple webhook proxy: receives Alertmanager payloads, forwards to Discord."""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        alerts = body.get("alerts", [])
        for alert in alerts:
            status = alert.get("status", "unknown")
            name = alert.get("labels", {}).get("alertname", "Unknown")
            instance = alert.get("labels", {}).get("instance", "")
            summary = alert.get("annotations", {}).get("summary", "")
            severity = alert.get("labels", {}).get("severity", "")

            if status == "firing":
                emoji = "🚨"
                text = f"{emoji} **FIRING: {name}** [{severity}]\n{summary}\nInstance: `{instance}`"
            else:
                emoji = "✅"
                text = f"{emoji} **RESOLVED: {name}**\n{summary}\nInstance: `{instance}`"

            payload = json.dumps({"content": text}).encode()
            req = urllib.request.Request(
                DISCORD_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(req)
            except Exception as e:
                print(f"Discord send failed: {e}")

        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[webhook-proxy] {args[0]}")


if __name__ == "__main__":
    print("Discord webhook proxy listening on :9094")
    HTTPServer(("0.0.0.0", 9094), Handler).serve_forever()
