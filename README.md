# Live Auction Draft Analyzer

This is a separate Streamlit app for a 12-team, $200 auction with 17 roster spots per team:

- 1 QB, 1 RB, 2 WR, 1 TE
- 2 FLEX (RB/WR/TE)
- 1 DST, 1 K
- 8 bench spots

## Run on Windows

1. Put `app.py`, `requirements.txt`, and `2026_Auction_Value_vs_Rank.xlsx` in the same folder.
2. Open Terminal in that folder.
3. Install the requirements:

   `python -m pip install -r requirements.txt`

4. Start the app:

   `python -m streamlit run app.py`

You can also upload the workbook inside the app. Draft backups can be downloaded as JSON and restored later.

The **Auction Board** tab displays all 12 team rosters with money spent, money remaining,
open roster spots, and maximum bid. Use any team's **Add player** button to select that
team and record a winning bid directly from the board.

Positions are color-coded throughout the board: QB red, RB green, WR blue, TE orange,
DST purple, and K pink. Team headers, budget cards, and roster rows also use a brighter
visual design for faster scanning during a live draft.

The **Trade Center** supports one-for-one player trades with optional auction cash.
Player ownership changes immediately, while each original winning bid stays charged to
the team that made it. Cash transfers update money left, maximum bids, live inflation,
and the saved draft backup. Every completed trade is recorded in trade history.

Use **Load Demo Draft** in the sidebar to instantly populate all 12 teams with seven
sample players and realistic bids from the workbook. This fills the auction board,
budgets, live market, and Trade Center for presentations. **Clear Entire Draft** resets
all sample picks, trades, and cash adjustments when finished.

The app defaults to the league's 12 team nicknames. In **Team Names**, switch the
entire app between team nicknames and manager names, or enter custom names. Existing
picks, original budget charges, cash adjustments, and trade history follow the name change.

Every team card on the **Auction Board** includes color-coded QB, RB, WR, and TE
roster totals that update immediately after draft picks and trades.

For deployment, keep the included `.streamlit/config.toml` file inside a `.streamlit`
folder in the repository root. It locks the app to the light color theme so phone dark
mode cannot create white text on a white background.

## Live shared draft

When Supabase settings are added to Streamlit Community Cloud, the app loads one shared
draft for every visitor and refreshes it every five seconds. Visitors are view-only.
The commissioner unlocks editing with a private PIN, and every saved change is recorded
in the Live Activity Log. Copy `.streamlit/secrets.toml.example` only as a reference;
never commit a real service-role key or commissioner PIN to GitHub.

## Live-value calculation

The app preserves $1 for every open roster spot. It then compares all flexible auction dollars remaining across the league with the value premium remaining in the player pool. The resulting inflation factor is combined with current positional demand to update each available player's live value.
