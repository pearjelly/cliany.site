import ipaddress
import json
import os
import ssl
import subprocess
import sys
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@pytest.fixture
def local_https_download(tmp_home):
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "cliany isolated test CA")])
    ca_identifier = x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key())
    ca = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, None, None), critical=True)
        .add_extension(ca_identifier, critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    leaf = (
        x509.CertificateBuilder().subject_name(leaf_name).issuer_name(ca_name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, None, None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    ca_file = tmp_home / "ca.pem"
    cert_file = tmp_home / "server.pem"
    key_file = tmp_home / "server-key.pem"
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_file.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ))
    key_file.chmod(0o600)
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(404 if self.path.startswith("/missing") else 503)
            self.end_headers()
            self.wfile.write(b"PRIVATE_UPSTREAM_BODY_DO_NOT_ECHO")

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"https://127.0.0.1:{server.server_port}", ca_file, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("failure,status", [("missing", 404), ("unavailable", 503), ("untrusted", None)])
def test_real_https_child_keeps_safe_download_cause(tmp_home, local_https_download, failure, status):
    endpoint, ca_file, requests = local_https_download
    env = dict(os.environ, CLIANY_RUNTIME_HOME=str(tmp_home / "runtime"), CLIANY_QA_OFFLINE="1",
               NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    for key in ("PYTHONPATH", "PYTHONHOME", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        env.pop(key, None)
    if status is not None:
        # Trust only this test CA in the child; TLS verification stays enabled.
        env["SSL_CERT_FILE"] = str(ca_file)
    result = subprocess.run([
        sys.executable, "-m", "cliany_site", "--json", "market", "install",
        f"{endpoint}/{failure}?token=PRIVATE_QUERY_DO_NOT_ECHO", "--sha256", "0" * 64, "--dry-run",
    ], env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)

    assert result.returncode == 1, result.stdout
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "INSTALL_FAILED"
    if status is None:
        assert error["details"] == {"stage": "download", "reason": "tls_certificate_error"}
        assert requests == []
    else:
        assert error["details"] == {"stage": "download", "reason": "http_error", "status_code": status}
        assert len(requests) == 1
    assert "PRIVATE_" not in result.stdout
    assert "检查安装包格式" not in error["fix"]
    assert not list((tmp_home / "runtime").rglob("commands.py"))
