#!/usr/bin/env python3
"""
cases/_dcf_gold_mcd.py — compute the eval-#3 GOLD DCF for the McDonald's FY2025 anchor case,
closed-form, so the case YAML carries verifiable numbers (no hand arithmetic).

Base lines are REAL FY2025 10-K figures (accession 0000063908-26-000035, $M):
  revenue 26,885 | operating income (EBIT) 12,393 | tax provision 2,334 | net income 8,563
  D&A 2,199 | capex 3,365 | cash 774 | total debt 39,973 (single balance-sheet 'Long-term debt'
  line = footnote 'Total debt obligations'; the 725 'current maturities' is a footnote SUBSET, NOT
  additive) | equity-method investments 2,820 | diluted wtd-avg shares 716.4M | diluted EPS 11.95
The FORECAST + WACC + terminal are the ORACLE layer (illustrative, labeled). Convention: year-end.
Run: python cases/_dcf_gold_mcd.py
"""

# ---------------- REAL FY2025 base (filed, $M) ----------------
REV0      = 26_885.0
EBIT0     = 12_393.0
DA0       = 2_199.0
CAPEX0    = 3_365.0
CASH      = 774.0
TOTAL_DEBT= 39_973.0                    # the single balance-sheet 'Long-term debt' line (= footnote
                                        # 'Total debt obligations'); 725 'current maturities' is a
                                        # footnote SUBSET of this, NOT an additive face line
NET_DEBT  = TOTAL_DEBT - CASH           # 39,199
NONOP     = 2_820.0                     # equity-method investments (added in bridge)
MINORITY  = 0.0
PREFERRED = 0.0
SHARES    = 716.4                       # diluted weighted-average, millions

# ---------------- ORACLE forecast (illustrative) ----------------
H            = 5                        # explicit horizon (FY2026-2030)
REV_GROWTH   = 0.04                     # +4%/yr systemwide
EBIT_MARGIN  = EBIT0 / REV0             # hold the FY2025 operating margin (~46.1%)
CASH_TAX     = 0.215                    # marginal/operating cash tax on EBIT (oracle; ~ the 21.4% effective)
DA_PCT       = DA0 / REV0              # D&A as % of revenue, held
CAPEX_PCT    = CAPEX0 / REV0           # capex as % of revenue, held
DNWC         = 100.0                    # modest working-capital USE per year ($M); franchisor WC is small

# ---------------- ORACLE WACC components ----------------
RF      = 0.043
BETA    = 0.70
ERP     = 0.050
KD_PRE  = 0.048
W_D     = 0.16                          # target market debt weight
W_E     = 1.0 - W_D
KE      = RF + BETA * ERP
KD_AFT  = KD_PRE * (1 - CASH_TAX)
WACC    = W_E * KE + W_D * KD_AFT

# ---------------- ORACLE terminal ----------------
G = 0.025                               # Gordon perpetuity growth (< long-run nominal GDP ~4%, << WACC)

def fcff_path():
    rows = []
    rev, da, capex = REV0, DA0, CAPEX0
    for t in range(1, H + 1):
        rev   = rev * (1 + REV_GROWTH)
        ebit  = rev * EBIT_MARGIN
        nopat = ebit * (1 - CASH_TAX)
        da    = rev * DA_PCT
        capex = rev * CAPEX_PCT
        fcff  = nopat + da - capex - DNWC
        rows.append(dict(t=t, rev=rev, ebit=ebit, nopat=nopat, da=da, capex=capex, dnwc=DNWC, fcff=fcff))
    return rows

def main():
    print(f"margin={EBIT_MARGIN:.4%}  DA%={DA_PCT:.4%}  capex%={CAPEX_PCT:.4%}")
    print(f"Ke={KE:.4%}  Kd_after={KD_AFT:.4%}  WACC={WACC:.6%}  g={G:.2%}")
    rows = fcff_path()
    pv_sum = 0.0
    print("\n yr     revenue      ebit     nopat       d&a     capex    fcff      df       pv")
    for r in rows:
        df = 1 / (1 + WACC) ** r["t"]          # year-end convention
        pv = r["fcff"] * df
        pv_sum += pv
        print(f"  {r['t']}  {r['rev']:9,.1f} {r['ebit']:9,.1f} {r['nopat']:8,.1f} {r['da']:8,.1f} {r['capex']:8,.1f} {r['fcff']:8,.1f}  {df:.5f}  {pv:8,.1f}")
    fcff_N = rows[-1]["fcff"]
    tv = fcff_N * (1 + G) / (WACC - G)         # Gordon, value as of end of year N
    pv_tv = tv / (1 + WACC) ** H
    ev = pv_sum + pv_tv
    tv_share = pv_tv / ev
    implied_exit = tv / rows[-1]["ebit"]       # implied EV/EBIT exit (TV / terminal EBIT)
    equity = ev - NET_DEBT - MINORITY - PREFERRED + NONOP
    per_share = equity / SHARES
    print(f"\n sum PV(FCFF) = {pv_sum:,.1f}")
    print(f" TV (undisc)  = {tv:,.1f}    PV(TV) = {pv_tv:,.1f}    TV share of EV = {tv_share:.2%}")
    print(f" implied exit EV/EBIT (terminal) = {implied_exit:.2f}x")
    print(f" EV           = {ev:,.1f}")
    print(f" - net debt {NET_DEBT:,.0f}  - minority {MINORITY:.0f}  - preferred {PREFERRED:.0f}  + non-op {NONOP:,.0f}")
    print(f" equity       = {equity:,.1f}")
    print(f" per share    = {per_share:,.2f}  (on {SHARES}M diluted)")

    # ---- sensitivity grid: per-share over WACC x g ----
    print("\n sensitivity (per share):   g across, WACC down")
    gs = [G - 0.005, G, G + 0.005]
    ws = [WACC - 0.005, WACC, WACC + 0.005]
    hdr = "  WACC\\g  " + "".join(f"{g:8.2%}" for g in gs)
    print(hdr)
    grid = {}
    for w in ws:
        line = f"  {w:6.3%} "
        for g in gs:
            pvs = sum(r["fcff"] / (1 + w) ** r["t"] for r in rows)
            tvv = fcff_N * (1 + g) / (w - g)
            evv = pvs + tvv / (1 + w) ** H
            eqv = evv - NET_DEBT + NONOP
            ps = eqv / SHARES
            grid[(round(w,5), round(g,5))] = ps
            line += f"{ps:8,.0f}"
        print(line)
    # per-share sensitivity to +-50bp WACC at base g
    ps_lowW  = grid[(round(WACC-0.005,5), round(G,5))]
    ps_highW = grid[(round(WACC+0.005,5), round(G,5))]
    print(f"\n per-share at base g: WACC-50bp={ps_lowW:,.0f}  base={per_share:,.0f}  WACC+50bp={ps_highW:,.0f}")
    print(f" +-50bp WACC swing: {(ps_lowW-per_share)/per_share:+.1%} / {(ps_highW-per_share)/per_share:+.1%}")

if __name__ == "__main__":
    main()
