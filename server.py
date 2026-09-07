from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecoder, dumps
from os import environ
from re import DOTALL, search
from time import time
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


PROJECTS = [
    ("Aegis", "aegis"), ("AuXio", "auxio"), ("Bus Factor HQ", "bus-factor-hq"),
    ("complAI", "cumplia"), ("deley.com", "deleycom"), ("dipia", "dipia"),
    ("Helius", "helius"), ("Hippocamp", "hippocamp"), ("HIVE", "simulador-de-cumplimiento-de-poltica-pblica"),
    ("Moirai", "moirai"), ("NeuroEcho", "neuroecho"), ("Pa'lante", "palante"),
    ("Parallax", "parallax"), ("Peaje", "peaje"), ("PLUMB", "plumb"),
    ("Provenance Firewall", "memory-firewall-for-ai-agents"), ("PULSE", "pulse"),
    ("PULSO", "pulso"), ("Replica", "replica"), ("Roxy", "roxy"),
    ("Stegora", "stegora"), ("TEMIS", "temis"), ("Vity", "vity"), ("WOKI", "woki"),
]
RANKING_CACHE = None
RANKING_CACHE_AT = 0


def project_votes(project):
    name, slug = project
    request = Request(
        f"https://hack.platan.us/26-co/vote/{slug}",
        headers={"User-Agent": "PLUMB vote board/1.0"},
    )
    try:
        with urlopen(request, timeout=2) as response:
            page = response.read().decode("utf-8", "ignore")
        payload = search(r'data-page="app"[^>]*>(.*)', page, flags=DOTALL)
        if not payload:
            return {"name": name, "votes": None}
        data, _ = JSONDecoder().raw_decode(payload.group(1))
        project = data["props"]["project"]
        return {"name": name, "votes": int(project["voteCount"]), "track": project["trackName"]}
    except Exception:
        return {"name": name, "votes": None}


def ranking_data():
    global RANKING_CACHE, RANKING_CACHE_AT
    now = time()
    if RANKING_CACHE and now - RANKING_CACHE_AT < 10:
        return {**RANKING_CACHE, "stale": False}
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(project_votes, PROJECTS))
    if any(item["votes"] is None for item in results):
        return {**RANKING_CACHE, "stale": True} if RANKING_CACHE else None
    current = results
    current.sort(key=lambda item: item["votes"], reverse=True)
    RANKING_CACHE = {"updated": int(now), "projects": current}
    RANKING_CACHE_AT = now
    return {**RANKING_CACHE, "stale": False}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path == "/api/ranking":
            ranking = ranking_data()
            payload = dumps(ranking or {"error": "official ranking unavailable"}).encode("utf-8")
            self.send_response(200 if ranking else 503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()


port = int(environ.get("PORT", "8000"))
server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
print(f"PLUMB server listening on :{port}", flush=True)
server.serve_forever()
