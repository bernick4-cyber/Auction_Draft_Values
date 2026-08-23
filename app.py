from __future__ import annotations

import io
import json
import html
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Live Auction Draft Analyzer", page_icon="🏈", layout="wide")

TEAM_COUNT = 12
STARTING_BUDGET = 200
ROSTER_SIZE = 17
STARTER_LIMITS = {"QB": 1, "RB": 1, "WR": 2, "TE": 1, "FLEX": 2, "DST": 1, "K": 1}
POSITION_LIMITS = {"QB": 4, "RB": 9, "WR": 10, "TE": 5, "DST": 3, "K": 3}
ELIGIBLE_FLEX = {"RB", "WR", "TE"}
DEFAULT_FILE = "2026_Auction_Value_vs_Rank.xlsx"
POSITION_COLORS = {
    "QB": ("#ef4444", "#fee2e2", "🟥"),
    "RB": ("#22c55e", "#dcfce7", "🟩"),
    "WR": ("#3b82f6", "#dbeafe", "🟦"),
    "TE": ("#f59e0b", "#fef3c7", "🟧"),
    "DST": ("#8b5cf6", "#ede9fe", "🟪"),
    "K": ("#ec4899", "#fce7f3", "🩷"),
}
TEAM_COLORS = ["#2563eb", "#7c3aed", "#db2777", "#dc2626", "#ea580c", "#ca8a04",
               "#16a34a", "#0d9488", "#0891b2", "#4f46e5", "#9333ea", "#475569"]
DEFAULT_NICKNAMES = [
    "Wacky Waving Arms", "Team Fluff", "The Ants Marching", "McANUS",
    "Fu¢ked Again", "Phony Handshakes", "Ricky Kicks", "The Storm",
    "Blockhead", "Mr. Girth", "Spaces Dogs", "Big Butler Bids",
]
DEFAULT_MANAGERS = [
    "Mark", "Mike T", "Craig", "Frankie", "Ed", "Josh",
    "Rick", "Bruce", "Ryan", "Dave", "Paul", "Michael",
]

st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #f8fbff 0%, #ffffff 42%); }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff, #eef5ff);
        border: 1px solid #dbeafe; border-radius: 14px; padding: 12px;
        box-shadow: 0 3px 10px rgba(30, 64, 175, .08);
    }
    .team-title { color: white; padding: 9px 12px; border-radius: 12px;
        font-size: 1.05rem; font-weight: 800; margin: 3px 0 10px 0; }
    .player-row { display: flex; align-items: center; justify-content: space-between;
        background: white; border: 1px solid #e5e7eb; border-radius: 9px;
        padding: 6px 8px; margin: 5px 0; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
    .pos-badge { color: white; font-size: .72rem; font-weight: 900; border-radius: 999px;
        padding: 3px 7px; margin-right: 6px; min-width: 31px; text-align: center; display: inline-block; }
    .player-name { color: #172033; font-size: .85rem; font-weight: 650; }
    .player-price { color: #0f766e; font-weight: 900; font-size: .86rem; }
    .position-legend { display:flex; flex-wrap:wrap; gap:7px; margin: 8px 0 16px 0; }
    .legend-item { border-radius:999px; padding:5px 10px; font-size:.8rem; font-weight:800; }
    .roster-counts { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; margin:8px 0 10px 0; }
    .roster-count { text-align:center; border-radius:8px; padding:5px 2px; font-size:.73rem;
        font-weight:900; border:1px solid; }
</style>
""", unsafe_allow_html=True)


def position_badge(position: str) -> str:
    color = POSITION_COLORS.get(position, ("#64748b", "#f1f5f9", "⬜"))[0]
    return f'<span class="pos-badge" style="background:{color}">{html.escape(position)}</span>'


def position_legend() -> str:
    items = []
    for pos, (color, pale, _) in POSITION_COLORS.items():
        items.append(f'<span class="legend-item" style="background:{pale};color:{color};border:1px solid {color}55">{pos}</span>')
    return '<div class="position-legend">' + ''.join(items) + '</div>'


def clean_players(raw: pd.DataFrame) -> pd.DataFrame:
    aliases = {str(c).strip().lower(): c for c in raw.columns}

    def find(*names):
        for name in names:
            if name in aliases:
                return aliases[name]
        return None

    player_col = find("player", "player name", "name")
    pos_col = find("position", "pos")
    if not player_col or not pos_col:
        raise ValueError("The selected sheet needs Player and Position columns.")

    out = pd.DataFrame({
        "Player": raw[player_col].astype(str).str.strip(),
        "Position": raw[pos_col].astype(str).str.upper().str.strip(),
    })
    mappings = {
        "POS Rank": find("pos rank", "position rank"),
        "Overall Rank": find("overall rank", "rank"),
        "Auction $": find("auction $", "auction value", "value", "price"),
        "Regression Price": find("regression price", "projected price"),
        "Value Label": find("value label", "verdict"),
    }
    for target, source in mappings.items():
        out[target] = raw[source] if source else np.nan

    out = out[(out["Player"] != "") & (out["Player"].str.lower() != "nan")]
    out = out[out["Position"].isin(["QB", "RB", "WR", "TE", "DST", "K"])]
    for col in ["Overall Rank", "Auction $", "Regression Price"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["Overall Rank"] = out["Overall Rank"].fillna(9999).astype(int)
    out["Base Value"] = out["Auction $"].fillna(0).clip(lower=0)
    # Every draftable player has a $1 floor in a standard auction.
    out["Base Value"] = out["Base Value"].where(out["Base Value"] > 0, 1.0)
    out["Player Key"] = out["Player"].str.casefold()
    out = out.drop_duplicates("Player Key", keep="first").sort_values("Overall Rank")
    return out.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def read_workbook(data: bytes, sheet: str) -> pd.DataFrame:
    return clean_players(pd.read_excel(io.BytesIO(data), sheet_name=sheet))


def default_teams() -> pd.DataFrame:
    return pd.DataFrame({"Team": DEFAULT_NICKNAMES})


def ensure_state():
    if "picks" not in st.session_state:
        st.session_state.picks = pd.DataFrame(columns=["Pick", "Player", "Position", "Team", "Budget Team", "Price"])
    elif "Budget Team" not in st.session_state.picks.columns:
        st.session_state.picks["Budget Team"] = st.session_state.picks["Team"]
    if "teams" not in st.session_state:
        st.session_state.teams = default_teams()
    if "next_pick" not in st.session_state:
        st.session_state.next_pick = 1
    if "board_team" not in st.session_state:
        st.session_state.board_team = "Team 1"
    if "cash_adjustments" not in st.session_state:
        st.session_state.cash_adjustments = {team: 0 for team in st.session_state.teams["Team"]}
    if "trades" not in st.session_state:
        st.session_state.trades = pd.DataFrame(columns=["Trade", "Team A", "Sent A", "Team B", "Sent B", "Cash Detail"])


def team_summary(picks: pd.DataFrame, teams: pd.DataFrame, cash_adjustments: dict | None = None) -> pd.DataFrame:
    cash_adjustments = cash_adjustments or {}
    rows = []
    for team in teams["Team"]:
        tp = picks[picks["Team"] == team]
        budget_team_col = "Budget Team" if "Budget Team" in picks.columns else "Team"
        spent_picks = picks[picks[budget_team_col] == team]
        spent = float(spent_picks["Price"].sum()) if not spent_picks.empty else 0.0
        filled = len(tp)
        cash_adjustment = float(cash_adjustments.get(team, 0))
        left = STARTING_BUDGET - spent + cash_adjustment
        open_spots = ROSTER_SIZE - filled
        max_bid = max(0, left - max(0, open_spots - 1)) if open_spots else 0
        counts = tp["Position"].value_counts().to_dict()
        starter_core = min(counts.get("QB", 0), 1) + min(counts.get("RB", 0), 1)
        starter_core += min(counts.get("WR", 0), 2) + min(counts.get("TE", 0), 1)
        flex_owned = sum(counts.get(p, 0) for p in ELIGIBLE_FLEX)
        flex_used = max(0, flex_owned - min(counts.get("RB", 0), 1) - min(counts.get("WR", 0), 2) - min(counts.get("TE", 0), 1))
        starters = starter_core + min(flex_used, 2) + min(counts.get("DST", 0), 1) + min(counts.get("K", 0), 1)
        needs = []
        for pos, minimum in [("QB", 1), ("RB", 1), ("WR", 2), ("TE", 1), ("DST", 1), ("K", 1)]:
            missing = max(0, minimum - counts.get(pos, 0))
            if missing:
                needs.append(f"{pos}×{missing}")
        if flex_used < 2:
            needs.append(f"FLEX×{2-flex_used}")
        rows.append({
            "Team": team, "Spent": spent, "Trade Cash": cash_adjustment, "Left": left, "Players": filled,
            "Open": open_spots, "Max Bid": max_bid, "Starters Filled": starters,
            "Needs": ", ".join(needs) if needs else "Bench/depth",
            **{p: counts.get(p, 0) for p in ["QB", "RB", "WR", "TE", "DST", "K"]},
        })
    return pd.DataFrame(rows)


def live_values(players: pd.DataFrame, picks: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    drafted = set(picks["Player"].astype(str).str.casefold())
    avail = players[~players["Player Key"].isin(drafted)].copy()

    # Flexible dollars are dollars that can be spent beyond the mandatory $1 per open slot.
    flexible_dollars = float((summary["Left"] - summary["Open"]).clip(lower=0).sum())
    base_premium = float((avail["Base Value"] - 1).clip(lower=0).sum())
    inflation = flexible_dollars / base_premium if base_premium > 0 else 1.0
    inflation = float(np.clip(inflation, 0.25, 4.0))

    need_weights = {}
    for pos in ["QB", "RB", "WR", "TE", "DST", "K"]:
        if pos == "QB": required = (summary["QB"] < 1).sum()
        elif pos == "RB": required = (summary["RB"] < 1).sum() + 0.45 * (summary["Starters Filled"] < 7).sum()
        elif pos == "WR": required = (summary["WR"] < 2).sum() + 0.45 * (summary["Starters Filled"] < 7).sum()
        elif pos == "TE": required = (summary["TE"] < 1).sum() + 0.10 * (summary["Starters Filled"] < 7).sum()
        else: required = (summary[pos] < 1).sum()
        available_count = max(1, (avail["Position"] == pos).sum())
        scarcity = required / available_count
        need_weights[pos] = float(np.clip(1 + scarcity * 0.35, 0.85, 1.35))

    avail["Market Inflation"] = inflation
    avail["Position Demand"] = avail["Position"].map(need_weights).fillna(1.0)
    premium = (avail["Base Value"] - 1).clip(lower=0)
    avail["Live Value"] = (1 + premium * inflation * avail["Position Demand"]).round()
    league_max = int(summary["Max Bid"].max()) if not summary.empty else STARTING_BUDGET
    avail["Live Value"] = avail["Live Value"].clip(lower=1, upper=max(1, league_max)).astype(int)
    avail["Change"] = (avail["Live Value"] - avail["Base Value"]).round().astype(int)
    avail["Market"] = np.select(
        [avail["Change"] >= 4, avail["Change"] <= -4],
        ["Rising", "Falling"], default="Stable"
    )
    return avail.sort_values(["Live Value", "Overall Rank"], ascending=[False, True])


def add_pick(player: str, team: str, price: int, players: pd.DataFrame, summary: pd.DataFrame):
    row = players[players["Player"] == player].iloc[0]
    team_row = summary[summary["Team"] == team].iloc[0]
    if team_row["Open"] <= 0:
        st.error(f"{team} has no open roster spots.")
        return
    if price < 1 or price > team_row["Max Bid"]:
        st.error(f"Valid bid for {team}: $1–${int(team_row['Max Bid'])}.")
        return
    pos = row["Position"]
    if int(team_row[pos]) >= POSITION_LIMITS[pos]:
        st.error(f"{team} has reached the app's {pos} safety limit ({POSITION_LIMITS[pos]}).")
        return
    new = pd.DataFrame([{"Pick": st.session_state.next_pick, "Player": player, "Position": pos, "Team": team, "Budget Team": team, "Price": int(price)}])
    st.session_state.picks = pd.concat([st.session_state.picks, new], ignore_index=True)
    st.session_state.next_pick += 1
    st.success(f"Added {player} to {team} for ${price}.")


def add_unlisted_pick(player: str, position: str, team: str, price: int, summary: pd.DataFrame):
    player = player.strip()
    if not player:
        st.error("Enter the player's name.")
        return
    existing = set(st.session_state.picks["Player"].astype(str).str.casefold())
    if player.casefold() in existing:
        st.error(f"{player} has already been drafted.")
        return
    team_row = summary[summary["Team"] == team].iloc[0]
    if team_row["Open"] <= 0 or price < 1 or price > team_row["Max Bid"]:
        st.error(f"Valid bid for {team}: $1–${int(team_row['Max Bid'])}.")
        return
    if int(team_row[position]) >= POSITION_LIMITS[position]:
        st.error(f"{team} has reached the {position} safety limit.")
        return
    new = pd.DataFrame([{"Pick": st.session_state.next_pick, "Player": player, "Position": position, "Team": team, "Budget Team": team, "Price": int(price)}])
    st.session_state.picks = pd.concat([st.session_state.picks, new], ignore_index=True)
    st.session_state.next_pick += 1


def execute_trade(team_a: str, player_a: str, team_b: str, player_b: str,
                  cash_payer: str, cash_amount: int, summary: pd.DataFrame):
    if team_a == team_b:
        st.error("Choose two different teams.")
        return False
    owned_a = st.session_state.picks[
        (st.session_state.picks["Team"] == team_a) & (st.session_state.picks["Player"] == player_a)
    ]
    owned_b = st.session_state.picks[
        (st.session_state.picks["Team"] == team_b) & (st.session_state.picks["Player"] == player_b)
    ]
    if owned_a.empty or owned_b.empty:
        st.error("A selected player is no longer owned by that team.")
        return False

    cash_receiver = team_b if cash_payer == team_a else team_a
    payer_row = summary[summary["Team"] == cash_payer].iloc[0]
    transferable = max(0, int(payer_row["Left"] - payer_row["Open"]))
    if cash_amount > transferable:
        st.error(f"{cash_payer} can trade at most ${transferable} while keeping $1 for every open roster spot.")
        return False

    mask_a = (st.session_state.picks["Team"] == team_a) & (st.session_state.picks["Player"] == player_a)
    mask_b = (st.session_state.picks["Team"] == team_b) & (st.session_state.picks["Player"] == player_b)
    st.session_state.picks.loc[mask_a, "Team"] = team_b
    st.session_state.picks.loc[mask_b, "Team"] = team_a
    if cash_amount:
        st.session_state.cash_adjustments[cash_payer] = st.session_state.cash_adjustments.get(cash_payer, 0) - cash_amount
        st.session_state.cash_adjustments[cash_receiver] = st.session_state.cash_adjustments.get(cash_receiver, 0) + cash_amount
    cash_detail = f"{cash_payer} → {cash_receiver}: ${cash_amount}" if cash_amount else "No cash"
    trade_row = pd.DataFrame([{
        "Trade": len(st.session_state.trades) + 1,
        "Team A": team_a, "Sent A": player_a,
        "Team B": team_b, "Sent B": player_b,
        "Cash Detail": cash_detail,
    }])
    st.session_state.trades = pd.concat([st.session_state.trades, trade_row], ignore_index=True)
    return True


def generate_demo_draft(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Create a balanced, deterministic seven-player sample roster for every team."""
    team_names = teams["Team"].tolist()
    pools = {
        pos: players[players["Position"] == pos].sort_values("Overall Rank").to_dict("records")
        for pos in ["QB", "RB", "WR", "TE"]
    }
    pool_index = {pos: 0 for pos in pools}
    budget_left = {team: STARTING_BUDGET for team in team_names}
    open_spots = {team: ROSTER_SIZE for team in team_names}
    rows, pick_no = [], 1
    demo_rounds = ["RB", "WR", "WR", "QB", "RB", "TE", "WR"]

    for round_no, pos in enumerate(demo_rounds):
        order = team_names if round_no % 2 == 0 else list(reversed(team_names))
        for team_idx, team in enumerate(order):
            if pool_index[pos] >= len(pools[pos]):
                continue
            player = pools[pos][pool_index[pos]]
            pool_index[pos] += 1
            variation = ((pick_no * 7) % 9 - 4) / 100  # repeatable -4% to +4%
            suggested = max(1, round(float(player["Base Value"]) * (0.88 + variation)))
            max_bid = max(1, int(budget_left[team] - (open_spots[team] - 1)))
            price = min(suggested, max_bid)
            rows.append({
                "Pick": pick_no, "Player": player["Player"], "Position": pos,
                "Team": team, "Budget Team": team, "Price": int(price),
            })
            budget_left[team] -= price
            open_spots[team] -= 1
            pick_no += 1
    return pd.DataFrame(rows, columns=["Pick", "Player", "Position", "Team", "Budget Team", "Price"])


def clear_draft_state():
    st.session_state.picks = pd.DataFrame(columns=["Pick", "Player", "Position", "Team", "Budget Team", "Price"])
    st.session_state.cash_adjustments = {team: 0 for team in st.session_state.teams["Team"]}
    st.session_state.trades = pd.DataFrame(columns=["Trade", "Team A", "Sent A", "Team B", "Sent B", "Cash Detail"])
    st.session_state.next_pick = 1


def apply_team_name_set(new_names: list[str]):
    old_names = st.session_state.teams["Team"].astype(str).tolist()
    mapping = dict(zip(old_names, new_names))
    st.session_state.teams = pd.DataFrame({"Team": new_names})
    if not st.session_state.picks.empty:
        st.session_state.picks["Team"] = st.session_state.picks["Team"].map(mapping).fillna(st.session_state.picks["Team"])
        st.session_state.picks["Budget Team"] = st.session_state.picks["Budget Team"].map(mapping).fillna(st.session_state.picks["Budget Team"])
    st.session_state.cash_adjustments = {
        mapping.get(team, team): amount for team, amount in st.session_state.cash_adjustments.items()
    }
    if not st.session_state.trades.empty:
        for col in ["Team A", "Team B"]:
            st.session_state.trades[col] = st.session_state.trades[col].map(mapping).fillna(st.session_state.trades[col])
        def rename_cash_detail(detail):
            detail = str(detail)
            if detail == "No cash" or " → " not in detail:
                return detail
            payer, rest = detail.split(" → ", 1)
            receiver, amount = rest.rsplit(": ", 1)
            return f"{mapping.get(payer, payer)} → {mapping.get(receiver, receiver)}: {amount}"
        st.session_state.trades["Cash Detail"] = st.session_state.trades["Cash Detail"].map(rename_cash_detail)
    st.session_state.board_team = mapping.get(st.session_state.get("board_team"), new_names[0])


def export_state() -> bytes:
    payload = {
        "teams": st.session_state.teams["Team"].tolist(),
        "next_pick": st.session_state.next_pick,
        "picks": st.session_state.picks.to_dict("records"),
        "cash_adjustments": st.session_state.cash_adjustments,
        "trades": st.session_state.trades.to_dict("records"),
    }
    return json.dumps(payload, indent=2).encode()


ensure_state()

st.title("🏈 Live Auction Draft Analyzer")
st.caption("12 teams · $200 budget · 17-player rosters · live inflation and positional-demand pricing")

with st.sidebar:
    st.header("Draft data")
    default_path = Path(DEFAULT_FILE)
    uploaded = st.file_uploader("Auction-value workbook", type=["xlsx"])
    if uploaded:
        workbook_bytes = uploaded.getvalue()
    elif default_path.exists():
        workbook_bytes = default_path.read_bytes()
        st.success(f"Loaded {DEFAULT_FILE}")
    else:
        workbook_bytes = None

    if workbook_bytes:
        sheet_names = pd.ExcelFile(io.BytesIO(workbook_bytes)).sheet_names
        default_idx = sheet_names.index("Auction vs Rank") if "Auction vs Rank" in sheet_names else 0
        sheet = st.selectbox("Player sheet", sheet_names, index=default_idx)
    else:
        sheet = None

    st.divider()
    st.header("Save / restore")
    st.download_button("Download draft backup", export_state(), "auction_draft_backup.json", "application/json", use_container_width=True)
    backup = st.file_uploader("Restore backup", type=["json"], key="backup")
    if backup and st.button("Restore draft", use_container_width=True):
        try:
            payload = json.loads(backup.getvalue())
            st.session_state.teams = pd.DataFrame({"Team": payload["teams"]})
            st.session_state.picks = pd.DataFrame(payload["picks"])
            if "Budget Team" not in st.session_state.picks.columns:
                st.session_state.picks["Budget Team"] = st.session_state.picks["Team"]
            st.session_state.picks = st.session_state.picks[["Pick", "Player", "Position", "Team", "Budget Team", "Price"]]
            st.session_state.next_pick = int(payload.get("next_pick", len(st.session_state.picks) + 1))
            st.session_state.cash_adjustments = payload.get("cash_adjustments", {team: 0 for team in payload["teams"]})
            st.session_state.trades = pd.DataFrame(payload.get("trades", []), columns=["Trade", "Team A", "Sent A", "Team B", "Sent B", "Cash Detail"])
            st.rerun()
        except Exception as exc:
            st.error(f"Could not restore backup: {exc}")

if not workbook_bytes or not sheet:
    st.info(f"Upload your workbook, or place it beside app.py as {DEFAULT_FILE}.")
    st.stop()

try:
    players = read_workbook(workbook_bytes, sheet)
except Exception as exc:
    st.error(f"Could not read player data: {exc}")
    st.stop()

with st.sidebar:
    st.divider()
    st.header("🎬 Demo mode")
    st.caption("Fill every team with sample picks for a quick presentation.")
    if st.button("Load Demo Draft", type="primary", use_container_width=True):
        st.session_state.picks = generate_demo_draft(players, st.session_state.teams)
        st.session_state.cash_adjustments = {team: 0 for team in st.session_state.teams["Team"]}
        st.session_state.trades = pd.DataFrame(columns=["Trade", "Team A", "Sent A", "Team B", "Sent B", "Cash Detail"])
        st.session_state.next_pick = len(st.session_state.picks) + 1
        st.rerun()
    if st.button("Clear Entire Draft", use_container_width=True):
        clear_draft_state()
        st.rerun()

summary = team_summary(st.session_state.picks, st.session_state.teams, st.session_state.cash_adjustments)
live = live_values(players, st.session_state.picks, summary)

top1, top2, top3, top4 = st.columns(4)
top1.metric("Players Drafted", len(st.session_state.picks), f"of {TEAM_COUNT * ROSTER_SIZE}")
top2.metric("League Money Left", f"${summary['Left'].sum():,.0f}")
top3.metric("Live Inflation", f"{live['Market Inflation'].iloc[0]:.2f}×" if len(live) else "—")
top4.metric("Highest Max Bid", f"${summary['Max Bid'].max():,.0f}")

draft_tab, board_tab, trade_tab, market_tab, teams_tab, log_tab, settings_tab = st.tabs([
    "Draft Player", "Auction Board", "Trade Center", "Live Player Values", "Team Budgets", "Draft Log", "Team Names"
])

with draft_tab:
    left, right = st.columns([1, 1.25])
    with left:
        st.subheader("Record a winning bid")
        team_choice = st.selectbox("Winning team", summary[summary["Open"] > 0]["Team"].tolist())
        selected_max = int(summary.loc[summary["Team"] == team_choice, "Max Bid"].iloc[0]) if team_choice else 1
        unlisted = st.checkbox("Player is not in the workbook (use for DST/K)")
        if not unlisted:
            search = st.text_input("Search player")
            choices = live
            if search:
                choices = choices[choices["Player"].str.contains(search, case=False, regex=False)]
            player_choice = st.selectbox("Player", choices["Player"].tolist() if len(choices) else [])
            suggested = int(live.loc[live["Player"] == player_choice, "Live Value"].iloc[0]) if player_choice else 1
            bid = st.number_input("Winning bid", min_value=1, max_value=max(1, selected_max), value=min(max(1, suggested), max(1, selected_max)), step=1)
            if st.button("Add drafted player", type="primary", use_container_width=True, disabled=not player_choice or not team_choice):
                add_pick(player_choice, team_choice, int(bid), players, summary)
                st.rerun()
        else:
            manual_name = st.text_input("Player / unit name", placeholder="Example: Eagles DST")
            manual_pos = st.selectbox("Position", ["DST", "K", "QB", "RB", "WR", "TE"])
            bid = st.number_input("Winning bid", min_value=1, max_value=max(1, selected_max), value=1, step=1, key="manual_bid")
            player_choice = None
            if st.button("Add unlisted player", type="primary", use_container_width=True, disabled=not team_choice):
                add_unlisted_pick(manual_name, manual_pos, team_choice, int(bid), summary)
                st.rerun()
    with right:
        st.subheader("Selected player")
        if player_choice:
            pr = live[live["Player"] == player_choice].iloc[0]
            a, b, c, d = st.columns(4)
            a.metric("Original Value", f"${pr['Base Value']:.0f}")
            b.metric("Live Value", f"${pr['Live Value']:.0f}", f"{pr['Change']:+.0f}")
            c.metric("Position", pr["Position"])
            d.metric("Overall Rank", int(pr["Overall Rank"]))
            st.write(f"Market: **{pr['Market']}** · Position-demand factor: **{pr['Position Demand']:.2f}×**")
        if team_choice:
            tr = summary[summary["Team"] == team_choice].iloc[0]
            st.info(f"{team_choice}: ${tr['Left']:.0f} left · {int(tr['Open'])} spots open · maximum bid ${tr['Max Bid']:.0f} · needs {tr['Needs']}")

with board_tab:
    st.subheader("Live Auction Board")
    st.caption("Each team shows its roster, amount spent, money remaining, and maximum possible next bid.")
    st.markdown(position_legend(), unsafe_allow_html=True)

    # Team buttons set the destination for the board's quick-add form.
    for row_start in range(0, len(summary), 4):
        board_cols = st.columns(4)
        for offset, col in enumerate(board_cols):
            idx = row_start + offset
            if idx >= len(summary):
                continue
            tr = summary.iloc[idx]
            team = tr["Team"]
            tp = st.session_state.picks[st.session_state.picks["Team"] == team].sort_values("Pick")
            with col:
                team_color = TEAM_COLORS[idx % len(TEAM_COLORS)]
                st.markdown(f'<div class="team-title" style="background:linear-gradient(135deg,{team_color},{team_color}bb)">{html.escape(str(team))}</div>', unsafe_allow_html=True)
                a, b = st.columns(2)
                a.metric("Money Left", f"${tr['Left']:.0f}")
                b.metric("Max Bid", f"${tr['Max Bid']:.0f}")
                st.caption(f"Spent ${tr['Spent']:.0f} · {int(tr['Open'])} spots open")
                count_html = '<div class="roster-counts">'
                for count_pos in ["QB", "RB", "WR", "TE"]:
                    count_color, count_pale, _ = POSITION_COLORS[count_pos]
                    count_html += (
                        f'<span class="roster-count" style="background:{count_pale};color:{count_color};'
                        f'border-color:{count_color}66">{count_pos} {int(tr[count_pos])}</span>'
                    )
                count_html += '</div>'
                st.markdown(count_html, unsafe_allow_html=True)
                if tp.empty:
                    st.write("_No players drafted_")
                else:
                    for _, pick in tp.iterrows():
                        safe_player = html.escape(str(pick["Player"]))
                        player_html = (
                            f'<div class="player-row"><span>{position_badge(str(pick["Position"]))}'
                            f'<span class="player-name">{safe_player}</span></span>'
                            f'<span class="player-price">${int(pick["Price"])}</span></div>'
                        )
                        st.markdown(player_html, unsafe_allow_html=True)
                if st.button("➕ Add player", key=f"board_add_{idx}", use_container_width=True, disabled=tr["Open"] <= 0):
                    st.session_state.board_team = team
                    st.session_state.board_team_select = team
                    st.rerun()
        st.divider()

    st.markdown("### Add a player from the board")
    active_teams = summary[summary["Open"] > 0]["Team"].tolist()
    if active_teams:
        if st.session_state.board_team not in active_teams:
            st.session_state.board_team = active_teams[0]
        # A name-set change happens later in the prior run, after this widget exists.
        # Clear its stale value here, before recreating the widget on the new run.
        if "board_team_select" in st.session_state and st.session_state.board_team_select not in active_teams:
            del st.session_state["board_team_select"]
        board_team = st.selectbox(
            "Add to team",
            active_teams,
            index=active_teams.index(st.session_state.board_team),
            key="board_team_select",
        )
        st.session_state.board_team = board_team
        board_team_row = summary[summary["Team"] == board_team].iloc[0]
        board_max = max(1, int(board_team_row["Max Bid"]))
        manual_board = st.checkbox("Player is not in the workbook (DST/K)", key="board_manual")
        form_left, form_mid, form_right = st.columns([2, 1, 1])
        if not manual_board:
            board_player = form_left.selectbox("Player", live["Player"].tolist(), key="board_player")
            board_suggested = int(live.loc[live["Player"] == board_player, "Live Value"].iloc[0]) if board_player else 1
            board_bid = form_mid.number_input("Winning bid", min_value=1, max_value=board_max,
                                              value=min(max(1, board_suggested), board_max), step=1, key="board_bid")
            form_right.metric("Money after pick", f"${board_team_row['Left'] - board_bid:.0f}")
            if st.button(f"Add {board_player} to {board_team}", type="primary", use_container_width=True, disabled=not board_player):
                add_pick(board_player, board_team, int(board_bid), players, summary)
                st.rerun()
        else:
            board_name = form_left.text_input("Player / unit name", placeholder="Example: Eagles DST", key="board_name")
            board_pos = form_mid.selectbox("Position", ["DST", "K", "QB", "RB", "WR", "TE"], key="board_pos")
            board_bid = form_right.number_input("Winning bid", min_value=1, max_value=board_max, value=1, step=1, key="board_manual_bid")
            st.metric("Money after pick", f"${board_team_row['Left'] - board_bid:.0f}")
            if st.button(f"Add unlisted player to {board_team}", type="primary", use_container_width=True):
                add_unlisted_pick(board_name, board_pos, board_team, int(board_bid), summary)
                st.rerun()
        st.info(f"{board_team} currently has ${board_team_row['Left']:.0f} left and needs: {board_team_row['Needs']}")
    else:
        st.success("Every roster is full.")

with trade_tab:
    st.subheader("🔄 Trade Center")
    st.caption("Swap one player from each team and optionally include auction cash. Original winning bids stay charged to the teams that made them.")
    teams_with_players = [team for team in summary["Team"] if not st.session_state.picks[st.session_state.picks["Team"] == team].empty]
    if len(teams_with_players) < 2:
        st.info("At least two teams need drafted players before a trade can be entered.")
    else:
        ta_col, arrow_col, tb_col = st.columns([1, .18, 1])
        with ta_col:
            team_a = st.selectbox("Team A", teams_with_players, key="trade_team_a")
            players_a = st.session_state.picks[st.session_state.picks["Team"] == team_a].sort_values("Player")
            player_a = st.selectbox("Team A sends", players_a["Player"].tolist(), key="trade_player_a")
        with arrow_col:
            st.markdown("<div style='font-size:2rem;text-align:center;padding-top:65px'>⇄</div>", unsafe_allow_html=True)
        with tb_col:
            team_b_options = [team for team in teams_with_players if team != team_a]
            team_b = st.selectbox("Team B", team_b_options, key="trade_team_b")
            players_b = st.session_state.picks[st.session_state.picks["Team"] == team_b].sort_values("Player")
            player_b = st.selectbox("Team B sends", players_b["Player"].tolist(), key="trade_player_b")

        st.markdown("#### Optional auction cash")
        cash_col1, cash_col2, cash_col3 = st.columns(3)
        cash_payer = cash_col1.selectbox("Team sending cash", [team_a, team_b], key="cash_payer")
        cash_receiver = team_b if cash_payer == team_a else team_a
        payer_row = summary[summary["Team"] == cash_payer].iloc[0]
        max_trade_cash = max(0, int(payer_row["Left"] - payer_row["Open"]))
        cash_amount = cash_col2.number_input("Cash included", min_value=0, max_value=max_trade_cash,
                                             value=min(20, max_trade_cash), step=1, key="trade_cash")
        cash_col3.metric("Cash receiver", cash_receiver, f"+${cash_amount}")

        before_a = summary[summary["Team"] == team_a].iloc[0]
        before_b = summary[summary["Team"] == team_b].iloc[0]
        after_a = before_a["Left"] + (cash_amount if cash_receiver == team_a else -cash_amount)
        after_b = before_b["Left"] + (cash_amount if cash_receiver == team_b else -cash_amount)
        preview_a, preview_b = st.columns(2)
        preview_a.info(f"**{team_a} receives:** {player_b}" + (f" + ${cash_amount}" if cash_receiver == team_a and cash_amount else "") + f"  \nMoney after trade: **${after_a:.0f}**")
        preview_b.info(f"**{team_b} receives:** {player_a}" + (f" + ${cash_amount}" if cash_receiver == team_b and cash_amount else "") + f"  \nMoney after trade: **${after_b:.0f}**")

        if st.button("Complete trade", type="primary", use_container_width=True):
            if execute_trade(team_a, player_a, team_b, player_b, cash_payer, int(cash_amount), summary):
                st.success("Trade completed. Rosters, budgets, max bids, and live values have been updated.")
                st.rerun()

    if not st.session_state.trades.empty:
        st.divider()
        st.markdown("### Trade history")
        st.dataframe(st.session_state.trades, hide_index=True, use_container_width=True)

with market_tab:
    st.subheader("Recalculated available-player values")
    st.markdown(position_legend(), unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    pos_filter = c1.multiselect("Position", ["QB", "RB", "WR", "TE", "DST", "K"], default=["QB", "RB", "WR", "TE"])
    min_value = c2.number_input("Minimum live value", min_value=1, value=1)
    market_filter = c3.multiselect("Movement", ["Rising", "Stable", "Falling"], default=["Rising", "Stable", "Falling"])
    shown = live[live["Position"].isin(pos_filter) & (live["Live Value"] >= min_value) & live["Market"].isin(market_filter)]
    cols = ["Player", "Position", "POS Rank", "Overall Rank", "Base Value", "Live Value", "Change", "Market", "Position Demand"]
    colorful_shown = shown[cols].copy()
    colorful_shown["Position"] = colorful_shown["Position"].map(
        lambda p: f"{POSITION_COLORS.get(p, ('', '', '⬜'))[2]} {p}"
    )
    st.dataframe(colorful_shown, hide_index=True, use_container_width=True, height=650,
                 column_config={"Base Value": st.column_config.NumberColumn(format="$%.0f"), "Live Value": st.column_config.NumberColumn(format="$%d"), "Change": st.column_config.NumberColumn(format="%+d"), "Position Demand": st.column_config.NumberColumn(format="%.2fx")})
    st.download_button("Download current live values", shown[cols].to_csv(index=False), "live_auction_values.csv", "text/csv")

with teams_tab:
    st.subheader("Money, roster space, and needs")
    st.dataframe(summary, hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="$%.0f") for c in ["Spent", "Left", "Max Bid"]})

with log_tab:
    st.subheader("Draft history")
    if st.session_state.picks.empty:
        st.info("No players have been drafted yet.")
    else:
        edited = st.data_editor(st.session_state.picks.sort_values("Pick"), hide_index=True, use_container_width=True,
                                disabled=["Pick", "Player", "Position", "Budget Team"], num_rows="fixed",
                                column_config={"Team": st.column_config.SelectboxColumn(options=st.session_state.teams["Team"].tolist(), required=True), "Price": st.column_config.NumberColumn(min_value=1, step=1, format="$%d")})
        col1, col2 = st.columns(2)
        if col1.button("Save log edits", use_container_width=True):
            st.session_state.picks = edited.copy()
            st.rerun()
        undo_options = st.session_state.picks.sort_values("Pick", ascending=False)
        undo_label = col2.selectbox("Remove a pick", [f"#{int(r.Pick)} {r.Player} — {r.Team} ${int(r.Price)}" for _, r in undo_options.iterrows()], label_visibility="collapsed")
        if col2.button("Remove selected pick", use_container_width=True):
            pick_no = int(undo_label.split()[0][1:])
            st.session_state.picks = st.session_state.picks[st.session_state.picks["Pick"] != pick_no].reset_index(drop=True)
            st.rerun()

with settings_tab:
    st.subheader("Team display names")
    name_style = st.radio("Show teams by", ["Team nicknames", "Manager names"], horizontal=True)
    selected_names = DEFAULT_NICKNAMES if name_style == "Team nicknames" else DEFAULT_MANAGERS
    if st.button(f"Apply {name_style.lower()}", type="primary", use_container_width=True):
        apply_team_name_set(selected_names)
        st.rerun()
    name_reference = pd.DataFrame({"Team #": range(1, 13), "Nickname": DEFAULT_NICKNAMES, "Manager": DEFAULT_MANAGERS})
    st.dataframe(name_reference, hide_index=True, use_container_width=True)
    st.divider()
    st.subheader("Or enter custom names")
    edited_teams = st.data_editor(st.session_state.teams, hide_index=True, use_container_width=True, num_rows="fixed")
    if st.button("Save team names"):
        names = edited_teams["Team"].astype(str).str.strip()
        if names.eq("").any() or names.duplicated().any():
            st.error("Every team name must be filled in and unique.")
        else:
            apply_team_name_set(names.tolist())
            st.rerun()

st.caption("Live value = $1 floor + remaining value premium × league inflation × positional demand. Inflation compares flexible dollars remaining with the remaining player-value pool.")
