"""Authorized Lords Mobile observation tracker. Python 3.11+, standard library only."""
from __future__ import annotations
import json, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load_env():
    path = ROOT / ".env"
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1); os.environ.setdefault(key.strip(), value.strip())

load_env()
DB_PATH = ROOT / os.getenv("DATABASE_PATH", "lords_tracker.sqlite3")
UTC = timezone.utc

def now(): return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def compact(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) if value is not None else None
def comparable_snapshot(value):
    """Remove collection time when deciding whether an observation is new."""
    return compact({key: item for key, item in value.items() if key != "observed_at"})
def connect():
    db = sqlite3.connect(DB_PATH); db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS players (player_id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, observed_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, player_id TEXT NOT NULL, observed_at TEXT NOT NULL, snapshot TEXT NOT NULL, UNIQUE(player_id, observed_at, snapshot));
    CREATE TABLE IF NOT EXISTS changes (id INTEGER PRIMARY KEY, player_id TEXT NOT NULL, observed_at TEXT NOT NULL, field TEXT NOT NULL, old_value TEXT, new_value TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS changes_player_time ON changes(player_id, observed_at DESC);
    CREATE TABLE IF NOT EXISTS subscriptions (chat_id TEXT NOT NULL, player_id TEXT NOT NULL, PRIMARY KEY(chat_id, player_id));
    CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS public_snapshots (id INTEGER PRIMARY KEY, source TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL);
    """); return db

FIELDS = ("name", "kingdom", "guild", "x", "y", "might", "kills", "shield_until", "fury_until", "last_activity_at", "gear")
LABELS = {"name":"name", "kingdom":"kingdom", "guild":"guild", "x":"x coordinate", "y":"y coordinate", "might":"might", "kills":"kills", "shield_until":"shield", "fury_until":"fury", "last_activity_at":"activity", "gear":"gear"}

def valid_timestamp(value, field):
    if value is None: return None
    if not isinstance(value, str): raise ValueError(f"{field} must be an ISO-8601 string or null")
    try: datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{field} is not a valid ISO-8601 timestamp") from exc
    return value

def normalise(raw, fallback_time):
    if not isinstance(raw, dict): raise ValueError("each player must be an object")
    if not raw.get("player_id"): raise ValueError("player_id is required")
    p = {field: raw.get(field) for field in FIELDS}; p["player_id"] = str(raw["player_id"])
    for numeric in ("kingdom", "x", "y", "might", "kills"):
        if p[numeric] is not None: p[numeric] = int(p[numeric])
    p["observed_at"] = valid_timestamp(raw.get("observed_at") or fallback_time, "observed_at")
    for field in ("shield_until", "fury_until", "last_activity_at"):
        p[field] = valid_timestamp(p[field], field)
    if p["gear"] is not None and not isinstance(p["gear"], (dict, list, str)):
        raise ValueError("gear must be an object, list, string, or null")
    return p

def format_value(field, value):
    if value is None: return "none"
    if field in ("might", "kills"):
        n = int(value); return f"{n / 1_000_000_000:.2f}B" if n >= 1_000_000_000 else f"{n / 1_000_000:.1f}M"
    if field == "gear": return ", ".join(f"{k}: {v}" for k,v in value.items()) if isinstance(value, dict) else str(value)
    return str(value)

def ingest(document):
    fallback = document.get("observed_at", now()) if isinstance(document, dict) else now()
    rows = document.get("players", []) if isinstance(document, dict) else document
    if not isinstance(rows, list): raise ValueError("expected a player list or an object with players")
    db = connect(); all_changes = []
    for raw in rows:
        current = normalise(raw, fallback); oldrow = db.execute("SELECT snapshot FROM players WHERE player_id=?", (current["player_id"],)).fetchone()
        previous = json.loads(oldrow["snapshot"]) if oldrow else None
        changes = []
        if previous:
            for field in FIELDS:
                if previous.get(field) != current.get(field): changes.append((field, previous.get(field), current.get(field)))
        encoded = compact(current)
        # An unchanged static endpoint must not grow the history forever, even
        # when it omits observed_at and the worker supplies collection time.
        latest = db.execute("SELECT snapshot FROM observations WHERE player_id=? ORDER BY id DESC LIMIT 1", (current["player_id"],)).fetchone()
        if not latest or comparable_snapshot(json.loads(latest["snapshot"])) != comparable_snapshot(current):
            db.execute("INSERT INTO observations(player_id,observed_at,snapshot) VALUES(?,?,?)", (current["player_id"], current["observed_at"], encoded))
        db.execute("INSERT INTO players(player_id,snapshot,observed_at) VALUES(?,?,?) ON CONFLICT(player_id) DO UPDATE SET snapshot=excluded.snapshot,observed_at=excluded.observed_at", (current["player_id"], encoded, current["observed_at"]))
        for field, before, after in changes:
            db.execute("INSERT INTO changes(player_id,observed_at,field,old_value,new_value) VALUES(?,?,?,?,?)", (current["player_id"], current["observed_at"], field, compact(before), compact(after)))
        if changes: all_changes.append((current, changes))
    db.commit(); db.close(); return all_changes

def fetch_source():
    source_file, source_url = os.getenv("SOURCE_FILE"), os.getenv("SOURCE_URL")
    if bool(source_file) == bool(source_url):
        raise ValueError("configure exactly one of SOURCE_FILE or SOURCE_URL")
    if source_file: return json.loads(Path(source_file).read_text(encoding="utf-8"))
    if source_url:
        headers = {"Accept":"application/json"}; token = os.getenv("SOURCE_BEARER_TOKEN")
        if token: headers["Authorization"] = "Bearer " + token
        if not source_url.startswith(("https://", "http://")):
            raise ValueError("SOURCE_URL must start with http:// or https://")
        with urllib.request.urlopen(urllib.request.Request(source_url, headers=headers), timeout=30) as response:
            if "json" not in response.headers.get("Content-Type", "application/json").lower():
                raise ValueError("source response is not JSON")
            return json.loads(response.read().decode("utf-8"))
    return None

def telegram(method, payload=None):
    token = os.getenv("8700967275:AAE8UXQ22y7FTlLGM-ZwmF66_6MmjLx9Kh0")
    if not token: return None
    data = urllib.parse.urlencode(payload or {}).encode()
    url = f"https://api.telegram.org/bot{token}/{method}"
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=40) as r:
        body=json.loads(r.read())
        if not body.get("ok", False): raise RuntimeError(body.get("description", "Telegram rejected request"))
        return body

def subscribed_chats(player_id):
    db=connect(); result=[r[0] for r in db.execute("SELECT chat_id FROM subscriptions WHERE player_id=?",(player_id,))]; db.close(); return result

def alert_text(player, changes):
    title = f"🔔 {player.get('name') or player['player_id']} ({player['player_id']})"
    lines = [title]
    for field, before, after in changes:
        if field == "x" or field == "y": continue
        lines.append(f"• {LABELS[field]}: {format_value(field,before)} → {format_value(field,after)}")
    old_xy={f: before for f, before, after in changes if f in ('x','y')}
    new_xy={f: after for f, before, after in changes if f in ('x','y')}
    if old_xy or new_xy:
        lines.append(f"• location: {old_xy.get('x','?')}:{old_xy.get('y','?')} → {new_xy.get('x',player.get('x','?'))}:{new_xy.get('y',player.get('y','?'))}")
    return "\n".join(lines)[:4096]

def deliver_alerts(change_sets):
    for player, changes in change_sets:
        message=alert_text(player, changes)
        for chat in subscribed_chats(player["player_id"]):
            try: telegram("sendMessage", {"chat_id":chat,"text":message})
            except Exception as exc: print(f"alert failed for {chat}: {exc}", file=sys.stderr)

def player_text(player):
    if not player: return "No player found."
    loc = f"{player.get('x')}:{player.get('y')}" if player.get('x') is not None else "unknown"
    return "\n".join([f"👤 {player.get('name') or player['player_id']}", f"ID: {player['player_id']}", f"Kingdom: {player.get('kingdom') or 'unknown'} | Guild: {player.get('guild') or 'none'}", f"Location: {loc}", f"Might: {format_value('might',player.get('might'))} | Kills: {format_value('kills',player.get('kills'))}", f"Shield: {player.get('shield_until') or 'none'}", f"Fury: {player.get('fury_until') or 'none'}", f"Observed: {player.get('observed_at')}"])

def lookup(term):
    db=connect(); rows=db.execute("SELECT snapshot FROM players").fetchall(); db.close(); term=term.lower()
    return [json.loads(r[0]) for r in rows if term in json.loads(r[0]).get("player_id","").lower() or term in (json.loads(r[0]).get("name") or "").lower()]

def chat_authorized(chat):
    """Optionally limit commands and alerts to explicitly allowed Telegram chats."""
    allowed = {item.strip() for item in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if item.strip()}
    return not allowed or str(chat) in allowed

def command(chat, text):
    bits=text.strip().split(maxsplit=1); cmd=bits[0].split("@")[0].lower() if bits else ""; arg=bits[1].strip() if len(bits)>1 else ""
    if not chat_authorized(chat): return "This bot is not enabled for this chat."
    if cmd in ("/start","/help"): return "Lords Live Tracker\n/track ID — receive changes\n/untrack ID\n/tracks\n/find name-or-ID\n/fury\n/shielddrops\n/history ID\n/status"
    if cmd == "/track" and arg:
        db=connect(); db.execute("INSERT OR IGNORE INTO subscriptions(chat_id,player_id) VALUES(?,?)",(str(chat),arg)); db.commit(); db.close(); return f"Tracking {arg}. Alerts arrive after the next changed observation."
    if cmd == "/untrack" and arg:
        db=connect(); db.execute("DELETE FROM subscriptions WHERE chat_id=? AND player_id=?",(str(chat),arg)); db.commit(); db.close(); return f"Stopped tracking {arg}."
    if cmd == "/tracks":
        db=connect(); ids=[r[0] for r in db.execute("SELECT player_id FROM subscriptions WHERE chat_id=?",(str(chat),))]; db.close(); return "Tracked: " + (", ".join(ids) or "none")
    if cmd == "/find" and arg:
        matches=lookup(arg); return "\n\n".join(player_text(p) for p in matches[:5]) if matches else "No player found."
    if cmd in ("/fury","/shielddrops"):
        field = "fury_until" if cmd=="/fury" else "shield_until"; db=connect(); rows=db.execute("SELECT snapshot FROM players").fetchall(); db.close(); players=[json.loads(r[0]) for r in rows]; filtered=[p for p in players if p.get(field)]
        return ("Fury active:\n" if cmd=="/fury" else "Shielded players:\n") + ("\n".join(f"• {p.get('name') or p['player_id']}: {p[field]}" for p in filtered[:30]) or "none")
    if cmd == "/history" and arg:
        db=connect(); rows=db.execute("SELECT observed_at,field,old_value,new_value FROM changes WHERE player_id=? ORDER BY id DESC LIMIT 15",(arg,)).fetchall(); db.close()
        return "\n".join(f"• {r['observed_at']} {LABELS[r['field']]}: {format_value(r['field'],json.loads(r['old_value']))} → {format_value(r['field'],json.loads(r['new_value']))}" for r in rows) or "No changes recorded."
    if cmd == "/status":
        db=connect(); p=db.execute("SELECT count(*) FROM players").fetchone()[0]; c=db.execute("SELECT count(*) FROM changes").fetchone()[0]; db.close(); return f"Ready. {p} players, {c} recorded changes. Source: {'configured' if (os.getenv('SOURCE_FILE') or os.getenv('SOURCE_URL')) else 'not configured'}."
    return "Unknown command. Send /help."

def process_updates():
    if not os.getenv("TELEGRAM_BOT_TOKEN"): return
    db=connect(); row=db.execute("SELECT value FROM state WHERE key='telegram_offset'").fetchone(); offset=int(row[0]) if row else 0; db.close()
    result=telegram("getUpdates", {"offset":offset,"timeout":25}) or {}; updates=result.get("result", [])
    for update in updates:
        message=update.get("message") or {}; text=message.get("text"); chat=(message.get("chat") or {}).get("id")
        if text and chat is not None:
            try: telegram("sendMessage", {"chat_id":chat,"text":command(chat,text)})
            except Exception as exc: print(f"command failed: {exc}", file=sys.stderr)
        db=connect(); db.execute("INSERT INTO state(key,value) VALUES('telegram_offset',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(update['update_id']+1),)); db.commit(); db.close()

def cartograph_snapshot():
    url="https://www.lordsmobilecartograph.ru/"
    with urllib.request.urlopen(url, timeout=30) as r: html=r.read().decode("utf-8", "replace")
    fields={"total_castles":r"Total castles[\\s\\S]{0,300}?([0-9][0-9, ]{2,})", "active":r"Active[\\s\\S]{0,300}?([0-9][0-9, ]{2,})"}
    payload={key: re.search(pattern,html,re.I).group(1).replace(" ","") if re.search(pattern,html,re.I) else None for key,pattern in fields.items()}
    db=connect(); db.execute("INSERT INTO public_snapshots(source,observed_at,payload) VALUES(?,?,?)",("cartograph-public-home",now(),compact(payload))); db.commit(); db.close(); print(json.dumps(payload, indent=2))

def source_status():
    source_file, source_url = os.getenv("SOURCE_FILE"), os.getenv("SOURCE_URL")
    if bool(source_file) == bool(source_url): return "not configured (set exactly one SOURCE_FILE or SOURCE_URL)"
    return f"file: {source_file}" if source_file else f"URL: {source_url}"

def doctor():
    """Read-only configuration and source-contract check; never contacts Telegram."""
    print(f"Database: {DB_PATH}")
    print(f"Observation source: {source_status()}")
    if not (os.getenv("SOURCE_FILE") or os.getenv("SOURCE_URL")):
        print("Result: configuration needed")
        return 2
    try:
        document=fetch_source()
        rows=document.get("players", []) if isinstance(document, dict) else document
        if not isinstance(rows, list): raise ValueError("expected players array")
        for row in rows: normalise(row, document.get("observed_at", now()) if isinstance(document,dict) else now())
        print(f"Result: valid authorized-source payload with {len(rows)} player(s)")
        return 0
    except Exception as exc:
        print(f"Result: source check failed: {exc}", file=sys.stderr)
        return 1

def run():
    print(f"Worker running; database: {DB_PATH}")
    pause=max(5,int(os.getenv("POLL_SECONDS","15")))
    while True:
        try:
            document=fetch_source()
            deliver_alerts(ingest(document))
            db=connect(); db.execute("INSERT INTO state(key,value) VALUES('source_last_success',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(now(),)); db.commit(); db.close()
            if os.getenv("TELEGRAM_ENABLED","true").lower() == "true": process_updates()
        except Exception as exc: print(f"worker error: {exc}", file=sys.stderr)
        time.sleep(pause)

if __name__ == "__main__":
    action=sys.argv[1] if len(sys.argv)>1 else "run"
    if action == "run": run()
    elif action == "ingest" and len(sys.argv)==3: print(f"Recorded {len(ingest(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))))} changed players.")
    elif action == "status": print(command(0,"/status") + "\nSource detail: " + source_status())
    elif action == "cartograph": cartograph_snapshot()
    elif action == "doctor": sys.exit(doctor())
    else: print("Usage: python tracker.py [run|ingest FILE|status|doctor|cartograph]")
