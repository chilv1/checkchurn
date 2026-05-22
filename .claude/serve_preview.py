import http.server, socketserver, os
os.chdir(os.path.join(os.path.dirname(__file__), "..", "output"))
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/dashboard.html"
        return super().do_GET()
PORT = 8787
with socketserver.TCPServer(("127.0.0.1", PORT), H) as httpd:
    print(f"serving dashboard on http://127.0.0.1:{PORT}")
    httpd.serve_forever()
