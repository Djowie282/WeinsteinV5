# Weinstein Screener V5 — Setup Guide

## Folder Structure
```
weinstein-v5/
├── app.py                  ← Main entry (home + auth)
├── requirements.txt
├── .streamlit/
│   └── secrets.toml        ← Supabase keys (never commit!)
├── pages/
│   ├── 1_Sectors.py        ← Sector screener + Stage 1 watchlist
│   ├── 2_Industries.py     ← Industry screener + drill-down
│   ├── 3_All_Stocks.py     ← Full market scan
│   └── 4_Dashboard.py      ← Private portfolio dashboard
└── utils/
    ├── theme.py            ← Colors + CSS
    ├── screener.py         ← All Weinstein logic
    └── db.py               ← Supabase + fallback storage
```

## Step 1: Supabase Setup (free tier, 5 min)

1. Go to https://supabase.com → New project
2. Copy your Project URL and anon/service key
3. Open the SQL Editor and run:

```sql
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

alter table users disable row level security;
alter table portfolios disable row level security;
alter table watchlists disable row level security;
alter table invite_codes disable row level security;

-- Seed admin accounts
insert into users (username, pw_hash, role) values
  ('joey',  encode(sha256('weinstein2026'), 'hex'), 'admin'),
  ('roger', encode(sha256('roger123'),      'hex'), 'user');
```

## Step 2: Configure secrets

Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

On Streamlit Cloud: go to App Settings → Secrets → paste the same content.

## Step 3: Deploy to Streamlit Cloud

1. Push all files to GitHub
2. Go to share.streamlit.io → New app
3. Set Main file path: `app.py`
4. Add secrets in App Settings
5. Deploy

## Step 4: Migrate existing portfolio data

If you have positions in V4, add them via the Dashboard → Manage positions.
Or run this SQL in Supabase to bulk-insert:

```sql
insert into portfolios (username, ticker, shares, avg_cost, notes) values
  ('joey', 'RIVN', 1, 0, 'LEAPS 2027/2028'),
  ('joey', 'MU',   1, 0, ''),
  ('joey', 'ARM',  1, 0, '');
  -- etc.
```

## Notes

- Without Supabase configured, the app falls back to in-memory storage
  (data resets on server restart, same as V4)
- With Supabase, all data persists permanently
- The service role key bypasses RLS — keep it secret, never expose in client code
- Free tier: 500MB storage, unlimited auth, 50k monthly active users
