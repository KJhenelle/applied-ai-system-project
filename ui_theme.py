"""Shared look for the Streamlit app: one stylesheet, plus small HTML helpers."""
from __future__ import annotations

from html import escape

CSS = """
<style>
:root{--coral:#ff6b6b;--peach:#ffa07a;--cream:#fff8f1;--ink:#3b2f36;--muted:#8a7a83;--card:#ffffff;
  --line:rgba(80,40,60,.10);--shadow:0 6px 22px rgba(120,60,80,.10);--ok:#2fb67c;--warn:#f5a524;--err:#e5484d}
html,body,[class*="css"]{font-family:ui-rounded,"SF Pro Rounded","Nunito","Segoe UI",system-ui,sans-serif}
.stApp{background:radial-gradient(1200px 500px at 85% -10%,#ffe3d1 0%,transparent 60%),radial-gradient(900px 500px at -10% 10%,#ffe9f0 0%,transparent 55%),var(--cream)}
.block-container{max-width:1020px;padding-top:1.4rem;padding-bottom:4rem}
header[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4{color:var(--ink);letter-spacing:-.01em}
h4{margin-top:1.4rem}

/* hero */
.hero{position:relative;overflow:hidden;color:#fff;border-radius:28px;padding:1.7rem 2rem 1.5rem;margin-bottom:1.2rem;
  background:linear-gradient(120deg,#ff8a65 0%,#ff6b8a 55%,#c86bff 120%);box-shadow:0 14px 34px rgba(255,107,107,.30)}
.hero:before,.hero:after{content:"";position:absolute;border-radius:50%;background:rgba(255,255,255,.13)}
.hero:before{width:260px;height:260px;right:-70px;top:-110px}.hero:after{width:150px;height:150px;right:120px;bottom:-90px}
.hero h1{margin:0;font-size:2.15rem;color:#fff;font-weight:800}
.hero p{margin:.25rem 0 1rem;opacity:.95;font-size:1.02rem}
.pills{display:flex;gap:.55rem;flex-wrap:wrap;position:relative;z-index:1}
.pill{background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.35);padding:.3rem .85rem;border-radius:999px;font-weight:700;font-size:.88rem;backdrop-filter:blur(4px)}

/* tabs */
[data-testid="stTabs"] [role="tablist"]{gap:.35rem;border-bottom:none;background:rgba(255,255,255,.65);padding:.35rem;border-radius:18px;box-shadow:var(--shadow);overflow-x:auto}
[data-testid="stTabs"] button[role="tab"]{border-radius:13px;padding:.5rem 1rem;font-weight:700;color:var(--muted);height:auto}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{background:linear-gradient(120deg,#ff8a65,#ff6b8a);color:#fff}
[data-testid="stTabs"] button[role="tab"] p{font-weight:700;font-size:.95rem}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],[data-testid="stTabs"] [data-baseweb="tab-border"]{display:none}

/* buttons & inputs */
.stButton>button,.stFormSubmitButton>button{border-radius:14px;font-weight:700;border:1px solid var(--line);background:#fff;color:var(--ink);box-shadow:0 2px 8px rgba(120,60,80,.07);transition:transform .08s,box-shadow .15s}
.stButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(120,60,80,.14);border-color:var(--coral);color:var(--coral)}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:linear-gradient(120deg,#ff8a65,#ff6b8a);color:#fff;border:none}
.stButton>button[kind="primary"]:hover{color:#fff;filter:brightness(1.05)}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="base-input"]{border-radius:13px!important}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);padding:1.1rem 1.2rem}
[data-testid="stExpander"]{background:#fff;border-radius:18px;border:1px solid var(--line);box-shadow:var(--shadow)}
[data-testid="stDataFrame"],[data-testid="stTable"]{border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}
[data-testid="stMetric"]{background:#fff;border-radius:18px;padding:.7rem 1rem;box-shadow:var(--shadow);border:1px solid var(--line)}
iframe{border-radius:26px;border:none!important}
[data-testid="stSegmentedControl"] button{border-radius:12px;font-weight:700}

/* cards */
.card{background:#fff;border:1px solid var(--line);border-radius:20px;padding:.9rem 1.1rem;margin-bottom:.7rem;box-shadow:var(--shadow)}
.card .title{font-weight:800;font-size:1.04rem;color:var(--ink)}
.card .meta{color:var(--muted);font-size:.88rem;margin-top:.1rem}
.badge{display:inline-block;padding:.1rem .6rem;border-radius:999px;font-size:.73rem;font-weight:800;color:#fff;margin-left:.45rem;vertical-align:middle}
.slot{display:flex;gap:.9rem;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:20px;padding:.8rem 1rem;margin-bottom:.6rem;box-shadow:var(--shadow)}
.slot .time{min-width:96px;text-align:center;background:linear-gradient(120deg,#fff0e6,#ffe4ee);color:#c2453f;border-radius:13px;padding:.4rem .5rem;font-weight:800;font-variant-numeric:tabular-nums;font-size:.9rem}
.slot .title{font-weight:800}.slot .why{color:var(--muted);font-size:.85rem;margin-top:.15rem}
.slot .tip{margin-top:.4rem;background:#f6fbf6;border-left:4px solid #6cc28a;border-radius:8px;padding:.35rem .6rem;font-size:.83rem;color:#35553f}
.slot .tip small{color:#6f8a76}

/* companion status card */
.status h3{margin:0;font-size:1.5rem;font-weight:800}
.mood{display:inline-block;margin-left:.5rem;padding:.12rem .7rem;border-radius:999px;font-size:.78rem;font-weight:800;vertical-align:middle;color:#fff}
.mood-happy{background:var(--ok)}.mood-okay{background:var(--warn)}.mood-needy{background:var(--err)}
.status .sub{color:var(--muted);font-size:.86rem;margin:.2rem 0 .8rem}
.status .foot{margin-top:.6rem;font-size:.75rem;color:var(--muted)}
.quote{font-style:italic;color:#7a3550;background:#fff0f4;border-radius:14px;padding:.5rem .8rem;margin:.2rem 0 .6rem;font-size:.9rem}
.need{margin:.55rem 0}.need .row{display:flex;justify-content:space-between;font-weight:800;font-size:.9rem}
.need .row span:last-child{font-variant-numeric:tabular-nums}
.track{position:relative;height:13px;border-radius:99px;background:#f1e7e2;overflow:visible;margin-top:.25rem}
.fill{height:100%;border-radius:99px;transition:width .6s}
.fill.hi{background:linear-gradient(90deg,#43d49a,#2fb67c)}.fill.mid{background:linear-gradient(90deg,#ffd166,#f5a524)}.fill.lo{background:linear-gradient(90deg,#ff8f8f,#e5484d)}
.tick{position:absolute;top:-4px;width:3px;height:21px;border-radius:2px;background:#3b2f36;opacity:.65}
.need .cap{font-size:.74rem;color:var(--muted);margin-top:.15rem}
.sync{margin-top:.8rem;padding:.6rem .8rem;border-radius:14px;background:#fff4e0;border:1px solid #ffe0a8;color:#8a5a00;font-size:.85rem}
.sync.ok{background:#eafaf2;border-color:#bfead3;color:#1f7a52}

/* banners */
.banner{display:flex;gap:.6rem;align-items:flex-start;padding:.65rem .9rem;border-radius:16px;margin-bottom:.5rem;font-size:.92rem;border:1px solid transparent}
.banner.hello{background:linear-gradient(120deg,#fff0e6,#ffe4ee);color:#7a3550;font-weight:700;border-color:#ffd6e2}
.banner.warn{background:#fff6e0;color:#8a5a00;border-color:#ffe3a3}.banner.err{background:#ffeceb;color:#a3262b;border-color:#ffc9c7}
.banner.ok{background:#eafaf2;color:#1f7a52;border-color:#c4ebd7}.banner.info{background:#eef4ff;color:#36508f;border-color:#d3e1ff}
.src{display:inline-block;background:#f4ecf8;color:#6b3f86;border-radius:999px;padding:.1rem .6rem;font-size:.75rem;font-weight:700;margin:.25rem .3rem 0 0}
.section-sub{color:var(--muted);font-size:.9rem;margin:-.4rem 0 .8rem}
.empty{text-align:center;background:#fff;border:2px dashed #ffc7b0;border-radius:26px;padding:2.2rem 1rem;box-shadow:var(--shadow)}
.empty .big{font-size:3.2rem}.empty h3{margin:.3rem 0}
</style>
"""


def banner(kind: str, text: str, icon: str = "") -> str:
    """kind: hello | warn | err | ok | info. Text is escaped, so user-entered names are safe."""
    return f'<div class="banner {kind}">{icon + " " if icon else ""}<div>{escape(text)}</div></div>'
