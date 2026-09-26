import io, json, glob
import urllib.request, http.cookiejar

BASE = "http://127.0.0.1:5000"
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def form(url, fields):
    data = "&".join(f"{k}={v}" for k, v in fields.items()).encode()
    return op.open(urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}))


def upload(path):
    b = "----v"; fn = path.replace("\\", "/").split("/")[-1]
    body = io.BytesIO()
    body.write(f"--{b}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="audio"; filename="{fn}"\r\n'.encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    body.write(open(path, "rb").read()); body.write(f"\r\n--{b}--\r\n".encode())
    return json.loads(op.open(urllib.request.Request(f"{BASE}/api/classify-audio",
        data=body.getvalue(), headers={"Content-Type": f"multipart/form-data; boundary={b}"})).read())


form(f"{BASE}/login", {"email": "admin@sonicsentinel.ai", "password": "admin"})
print("login OK\n")
print(f"{'sample file':<32}{'predicted':<26}{'conf':>7}  severity")
print("-" * 75)
for f in sorted(glob.glob("sample_audio/*")):
    r = upload(f)
    name = f.split("\\")[-1].split("/")[-1]
    if r.get("error"):
        print(f"{name:<32}ERROR: {r['error']}")
    else:
        print(f"{name:<32}{r['final_class']:<26}{r['python']['confidence']:>6}%  {r['severity']}")
