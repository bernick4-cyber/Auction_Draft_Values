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

## Live-value calculation

The app preserves $1 for every open roster spot. It then compares all flexible auction dollars remaining across the league with the value premium remaining in the player pool. The resulting inflation factor is combined with current positional demand to update each available player's live value.
