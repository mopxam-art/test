#!/usr/bin/env python3
"""
Nginx Safe Control Dashboard
Lightweight, zero-dependency, safe visual controller for system Nginx and OpenClaw.
"""
import os
import sys
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 18790))
AUTH_TOKEN = os.environ.get("DASHBOARD_TOKEN", "openclaw123")
SITES_AVAILABLE = "/etc/nginx/sites-available"
SITES_ENABLED = "/etc/nginx/sites-enabled"

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def get_nginx_status():
    code, out, _ = run_cmd("systemctl is-active nginx")
    active = (out == "active")
    
    pid = ""
    if os.path.exists("/run/nginx.pid"):
        try:
            with open("/run/nginx.pid") as f:
                pid = f.read().strip()
        except:
            pass
            
    code, test_out, test_err = run_cmd("nginx -t 2>&1")
    syntax_ok = (code == 0)
    
    code, docker_status, _ = run_cmd("docker inspect openclaw_gateway --format '{{.State.Status}}' 2>/dev/null")
    if code != 0 or not docker_status:
        docker_status = "not-found"
        
    sites = []
    if os.path.exists(SITES_AVAILABLE):
        for fname in sorted(os.listdir(SITES_AVAILABLE)):
            fpath = os.path.join(SITES_AVAILABLE, fname)
            if not os.path.isfile(fpath):
                continue
            is_enabled = os.path.exists(os.path.join(SITES_ENABLED, fname))
            
            # Parse server_name and proxy_pass
            server_names = []
            proxy_passes = []
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("server_name ") and not line.startswith("#"):
                            names = line.replace("server_name", "").replace(";", "").split()
                            server_names.extend(names)
                        elif line.startswith("proxy_pass ") and not line.startswith("#"):
                            target = line.replace("proxy_pass", "").replace(";", "").strip()
                            if target not in proxy_passes:
                                proxy_passes.append(target)
            except:
                pass
                
            server_names = [n for n in server_names if n != "_" and not n.startswith("$")]
            
            # Identify site description/type
            name_lower = fname.lower()
            if "openclaw" in name_lower or "oc." in " ".join(server_names):
                category = "OpenClaw AI Gateway"
                can_toggle = True
            elif "n8n" in name_lower:
                category = "n8n Automation"
                can_toggle = False
            elif "pena" in name_lower:
                category = "Pena Club"
                can_toggle = False
            elif "oaudit" in name_lower or "oa." in " ".join(server_names):
                category = "Omni Auditor"
                can_toggle = False
            elif "dbord" in name_lower:
                category = "CRM Dashboard"
                can_toggle = False
            else:
                category = "Web Service"
                can_toggle = False
                
            sites.append({
                "id": fname,
                "category": category,
                "server_names": list(dict.fromkeys(server_names)),
                "proxy_passes": proxy_passes,
                "is_enabled": is_enabled,
                "can_toggle": can_toggle
            })
            
    return {
        "nginx_active": active,
        "nginx_pid": pid,
        "syntax_ok": syntax_ok,
        "syntax_message": test_out or test_err,
        "openclaw_container": docker_status,
        "openclaw_nginx_enabled": os.path.exists(os.path.join(SITES_ENABLED, "openclaw")),
        "sites": sites
    }

class RequestHandler(BaseHTTPRequestHandler):
    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def check_auth(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            if token == AUTH_TOKEN:
                return True
        query = parse_qs(urlparse(self.path).query)
        if query.get("token", [""])[0] == AUTH_TOKEN:
            return True
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json(get_nginx_status())
            return

        if path in ("/", "/index.html"):
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            html_file = os.path.join(cur_dir, "index.html")
            if os.path.exists(html_file):
                with open(html_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "index.html not found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if not self.check_auth():
            self.send_json({"error": "Unauthorized. Invalid or missing token."}, code=401)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = {}
        if content_length > 0:
            try:
                post_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except:
                pass

        if path == "/api/openclaw/toggle":
            action = post_data.get("action", "toggle")
            openclaw_avail = os.path.join(SITES_AVAILABLE, "openclaw")
            openclaw_enab = os.path.join(SITES_ENABLED, "openclaw")

            if not os.path.exists(openclaw_avail):
                self.send_json({"error": "Config /etc/nginx/sites-available/openclaw does not exist"}, code=400)
                return

            currently_enabled = os.path.exists(openclaw_enab)
            target_state = not currently_enabled if action == "toggle" else (action == "enable")

            if target_state:
                # Enable: create symlink
                run_cmd(f"ln -sf {openclaw_avail} {openclaw_enab}")
                # Test config!
                code, out, err = run_cmd("nginx -t 2>&1")
                if code != 0:
                    # REVERT immediately for safety!
                    run_cmd(f"rm -f {openclaw_enab}")
                    self.send_json({"error": f"Nginx test failed: {out or err}. Reverted back."}, code=400)
                    return
                run_cmd("systemctl reload nginx")
                self.send_json({"success": True, "enabled": True, "message": "OpenClaw включен в NGINX"})
            else:
                # Disable: remove symlink
                run_cmd(f"rm -f {openclaw_enab}")
                run_cmd("systemctl reload nginx")
                self.send_json({"success": True, "enabled": False, "message": "OpenClaw отключен в NGINX"})
            return

        if path == "/api/openclaw/container":
            action = post_data.get("action", "")
            if action == "start":
                code, out, err = run_cmd("docker start openclaw_gateway")
                self.send_json({"success": code == 0, "output": out or err})
            elif action == "stop":
                code, out, err = run_cmd("docker stop openclaw_gateway")
                self.send_json({"success": code == 0, "output": out or err})
            elif action == "restart":
                code, out, err = run_cmd("docker restart openclaw_gateway")
                self.send_json({"success": code == 0, "output": out or err})
            else:
                self.send_json({"error": "Unknown container action"}, code=400)
            return

        if path == "/api/nginx/reload":
            code, out, err = run_cmd("nginx -t 2>&1")
            if code != 0:
                self.send_json({"error": f"Syntax error: {out or err}"}, code=400)
                return
            code, out, err = run_cmd("systemctl reload nginx")
            self.send_json({"success": code == 0, "message": "NGINX успешно перезагружен"})
            return

        if path == "/api/nginx/test":
            code, out, err = run_cmd("nginx -t 2>&1")
            self.send_json({"success": code == 0, "output": out or err})
            return

        self.send_error(404, "Not Found")

def main():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Nginx Control Dashboard running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    main()
