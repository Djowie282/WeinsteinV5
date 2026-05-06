"""
utils/db.py — Supabase integration for V5
==========================================
Tables needed (run once in Supabase SQL editor):

  create table users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null,
    pw_hash text not null,
    role text default 'user',
    created_at timestamptz default now()
  );

  create table portfolios (
    id uuid primary key default gen_random_uuid(),
    username text not null,
    ticker text not null,
    shares float default 1,
    avg_cost float default 0,
    notes text default '',
    created_at timestamptz default now(),
    unique(username, ticker)
  );

  create table watchlists (
    id uuid primary key default gen_random_uuid(),
    username text not null,
    ticker text not null,
    tag text default 'watch',
    notes text default '',
    created_at timestamptz default now(),
    unique(username, ticker)
  );

  create table invite_codes (
    code text primary key,
    used boolean default false,
    created_by text,
    used_by text,
    created_at timestamptz default now()
  );

  -- Disable RLS for simplicity (single-app access via service key)
  alter table users disable row level security;
  alter table portfolios disable row level security;
  alter table watchlists disable row level security;
  alter table invite_codes disable row level security;
"""

import os
import streamlit as st
import hashlib

# ── Supabase client (lazy init) ──────────────────────────────

@st.cache_resource
def get_supabase():
    """Return Supabase client. Set SUPABASE_URL and SUPABASE_KEY in Streamlit secrets."""
    try:
        from supabase import create_client
        url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY", "")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Fallback in-memory store (when Supabase not configured) ──

@st.cache_resource
def _mem_store():
    return {
        "users": {
            "joey":  {"pw": _hash("weinstein2026"), "role": "admin"},
            "roger": {"pw": _hash("roger123"),      "role": "user"},
        },
        "portfolios": {
            "joey": [
                {"ticker":"RIVN","shares":1,"avg_cost":0,"notes":"LEAPS 2027/2028"},
                {"ticker":"MU","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"ARM","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"RKLB","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"CRWV","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"BEPC","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"BMBL","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"SOFI","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"UBER","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"FOUR","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"RBRK","shares":1,"avg_cost":0,"notes":""},
                {"ticker":"EOSE","shares":1,"avg_cost":0,"notes":""},
            ],
            "roger": [],
        },
        "watchlists":    {},
        "invite_codes":  {},
    }


# ── Auth ─────────────────────────────────────────────────────

def check_login(username: str, password: str) -> bool:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("pw_hash").eq("username", username).execute()
            if res.data:
                return res.data[0]["pw_hash"] == _hash(password)
        except Exception:
            pass
    # Fallback
    u = _mem_store()["users"].get(username)
    return bool(u and u["pw"] == _hash(password))

def get_role(username: str) -> str:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("role").eq("username", username).execute()
            if res.data:
                return res.data[0]["role"]
        except Exception:
            pass
    return _mem_store()["users"].get(username, {}).get("role", "user")

def is_admin(username: str) -> bool:
    return get_role(username) == "admin"

def create_user(username: str, password: str, role: str = "user") -> bool:
    sb = get_supabase()
    if sb:
        try:
            sb.table("users").insert({
                "username": username,
                "pw_hash": _hash(password),
                "role": role
            }).execute()
            return True
        except Exception:
            pass
    # Fallback
    mem = _mem_store()
    if username in mem["users"]:
        return False
    mem["users"][username] = {"pw": _hash(password), "role": role}
    mem["portfolios"][username] = []
    mem["watchlists"][username] = []
    return True

def user_exists(username: str) -> bool:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("username").eq("username", username).execute()
            return bool(res.data)
        except Exception:
            pass
    return username in _mem_store()["users"]

def list_users() -> list:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("username,role,created_at").execute()
            return res.data or []
        except Exception:
            pass
    return [{"username": k, "role": v["role"]} for k, v in _mem_store()["users"].items()]


# ── Invite codes ─────────────────────────────────────────────

def gen_invite(created_by: str) -> str:
    import secrets
    code = secrets.token_urlsafe(8)
    sb = get_supabase()
    if sb:
        try:
            sb.table("invite_codes").insert({
                "code": code, "used": False, "created_by": created_by
            }).execute()
            return code
        except Exception:
            pass
    _mem_store()["invite_codes"][code] = {"used": False, "created_by": created_by}
    return code

def validate_invite(code: str) -> bool:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("invite_codes").select("used").eq("code", code).execute()
            return bool(res.data) and not res.data[0]["used"]
        except Exception:
            pass
    entry = _mem_store()["invite_codes"].get(code)
    return bool(entry and not entry["used"])

def use_invite(code: str, used_by: str):
    sb = get_supabase()
    if sb:
        try:
            sb.table("invite_codes").update({"used": True, "used_by": used_by}).eq("code", code).execute()
            return
        except Exception:
            pass
    entry = _mem_store()["invite_codes"].get(code)
    if entry:
        entry["used"] = True

def list_invites() -> list:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("invite_codes").select("*").execute()
            return res.data or []
        except Exception:
            pass
    return [{"code": k, **v} for k, v in _mem_store()["invite_codes"].items()]


# ── Portfolio ─────────────────────────────────────────────────

def get_portfolio(username: str) -> list:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("portfolios").select("*").eq("username", username).execute()
            return res.data or []
        except Exception:
            pass
    return _mem_store()["portfolios"].get(username, [])

def upsert_position(username: str, ticker: str, shares: float, avg_cost: float, notes: str = ""):
    """Add or merge position (weighted avg cost)."""
    sb = get_supabase()
    if sb:
        try:
            # Check existing
            res = sb.table("portfolios").select("*").eq("username", username).eq("ticker", ticker).execute()
            if res.data:
                existing = res.data[0]
                old_sh = existing["shares"]; old_cost = existing["avg_cost"]
                new_sh = old_sh + shares
                if avg_cost > 0 and old_cost > 0:
                    new_avg = (old_sh * old_cost + shares * avg_cost) / new_sh
                elif avg_cost > 0:
                    new_avg = avg_cost
                else:
                    new_avg = old_cost
                sb.table("portfolios").update({
                    "shares": new_sh, "avg_cost": round(new_avg, 4),
                    "notes": notes or existing["notes"]
                }).eq("username", username).eq("ticker", ticker).execute()
            else:
                sb.table("portfolios").insert({
                    "username": username, "ticker": ticker,
                    "shares": shares, "avg_cost": avg_cost, "notes": notes
                }).execute()
            return
        except Exception:
            pass
    # Fallback
    port = _mem_store()["portfolios"].setdefault(username, [])
    existing = next((p for p in port if p["ticker"] == ticker), None)
    if existing:
        old_sh = existing["shares"]; old_cost = existing["avg_cost"]
        new_sh = old_sh + shares
        if avg_cost > 0 and old_cost > 0:
            new_avg = (old_sh * old_cost + shares * avg_cost) / new_sh
        elif avg_cost > 0:
            new_avg = avg_cost
        else:
            new_avg = old_cost
        existing["shares"] = new_sh
        existing["avg_cost"] = round(new_avg, 4)
        if notes: existing["notes"] = notes
    else:
        port.append({"ticker": ticker, "shares": shares, "avg_cost": avg_cost, "notes": notes})

def sell_shares(username: str, ticker: str, shares: float):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("portfolios").select("shares").eq("username", username).eq("ticker", ticker).execute()
            if res.data:
                remaining = res.data[0]["shares"] - shares
                if remaining <= 0.001:
                    sb.table("portfolios").delete().eq("username", username).eq("ticker", ticker).execute()
                else:
                    sb.table("portfolios").update({"shares": round(remaining, 4)}).eq("username", username).eq("ticker", ticker).execute()
            return
        except Exception:
            pass
    port = _mem_store()["portfolios"].get(username, [])
    existing = next((p for p in port if p["ticker"] == ticker), None)
    if existing:
        remaining = existing["shares"] - shares
        if remaining <= 0.001:
            port.remove(existing)
        else:
            existing["shares"] = round(remaining, 4)

def delete_position(username: str, ticker: str):
    sb = get_supabase()
    if sb:
        try:
            sb.table("portfolios").delete().eq("username", username).eq("ticker", ticker).execute()
            return
        except Exception:
            pass
    port = _mem_store()["portfolios"].get(username, [])
    _mem_store()["portfolios"][username] = [p for p in port if p["ticker"] != ticker]


# ── Watchlist ─────────────────────────────────────────────────

def get_watchlist(username: str) -> list:
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("watchlists").select("*").eq("username", username).execute()
            return res.data or []
        except Exception:
            pass
    return _mem_store()["watchlists"].get(username, [])

def add_to_watchlist(username: str, ticker: str, tag: str = "watch", notes: str = ""):
    sb = get_supabase()
    if sb:
        try:
            sb.table("watchlists").upsert({
                "username": username, "ticker": ticker, "tag": tag, "notes": notes
            }).execute()
            return
        except Exception:
            pass
    wl = _mem_store()["watchlists"].setdefault(username, [])
    if not any(w["ticker"] == ticker for w in wl):
        wl.append({"ticker": ticker, "tag": tag, "notes": notes})

def remove_from_watchlist(username: str, ticker: str):
    sb = get_supabase()
    if sb:
        try:
            sb.table("watchlists").delete().eq("username", username).eq("ticker", ticker).execute()
            return
        except Exception:
            pass
    wl = _mem_store()["watchlists"].get(username, [])
    _mem_store()["watchlists"][username] = [w for w in wl if w["ticker"] != ticker]
