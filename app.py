"""
India Professional Stock Analyzer — Web App
Backend: Flask + yfinance
"""
import os
import warnings
warnings.filterwarnings('ignore')

from flask import Flask, request, jsonify, Response

def render_template(t): return HTML_PAGE
from datetime import datetime

try:
    import yfinance as yf
except Exception as e:
    print(f"yfinance import error: {e}")
    yf = None

try:
    import pandas as pd
except Exception as e:
    print(f"pandas import error: {e}")
    pd = None

try:
    import numpy as np
except Exception as e:
    print(f"numpy import error: {e}")
    np = None

try:
    import ta
except Exception as e:
    print(f"ta import error: {e}")
    ta = None

app = Flask(__name__)
app = Flask(__name__)

# ─── Sector Intelligence ──────────────────────────────────────────────────────
SECTOR_INTELLIGENCE = {
    'defence':        {'fair_pe_low': 35, 'fair_pe_high': 45, 'tailwind': 9, 'risk': 5, 'govt_support': 'Very High — ₹2.19 Lakh Cr defence budget. Indigenous manufacturing push.'},
    'pharma':         {'fair_pe_low': 28, 'fair_pe_high': 35, 'tailwind': 8, 'risk': 4, 'govt_support': 'High — ₹10,000 Cr Biopharma SHAKTI scheme. India = pharmacy of world.'},
    'energy':         {'fair_pe_low': 14, 'fair_pe_high': 22, 'tailwind': 8, 'risk': 5, 'govt_support': 'Very High — 500GW renewable target. ₹22,000 Cr solar allocation.'},
    'banking':        {'fair_pe_low': 14, 'fair_pe_high': 20, 'tailwind': 7, 'risk': 4, 'govt_support': 'Moderate — RBI rate cuts expected. Credit growth 9-10%.'},
    'technology':     {'fair_pe_low': 25, 'fair_pe_high': 35, 'tailwind': 7, 'risk': 5, 'govt_support': 'Moderate — India Semiconductor Mission 2.0. PLI schemes for electronics.'},
    'infrastructure': {'fair_pe_low': 20, 'fair_pe_high': 30, 'tailwind': 9, 'risk': 6, 'govt_support': 'Very High — ₹12.2 Lakh Cr capex. New rail corridors, highways.'},
    'semiconductor':  {'fair_pe_low': 40, 'fair_pe_high': 60, 'tailwind': 9, 'risk': 7, 'govt_support': 'Very High — ISM 2.0 launched. Multiple chip fabs approved.'},
    'consumer':       {'fair_pe_low': 40, 'fair_pe_high': 60, 'tailwind': 5, 'risk': 3, 'govt_support': 'Low — Rural demand improving. Middle class growth.'},
    'automobile':     {'fair_pe_low': 18, 'fair_pe_high': 28, 'tailwind': 6, 'risk': 6, 'govt_support': 'Moderate — EV push, PLI for auto.'},
    'default':        {'fair_pe_low': 20, 'fair_pe_high': 30, 'tailwind': 6, 'risk': 5, 'govt_support': 'General India GDP growth 6.5-7% tailwind applies.'},
}

def get_sector_key(sector_str):
    if not sector_str: return 'default'
    s = sector_str.lower()
    if any(x in s for x in ['defence','defense','aerospace','military']): return 'defence'
    if any(x in s for x in ['pharma','health','biotech','drug','medical']): return 'pharma'
    if any(x in s for x in ['energy','power','electric','solar','wind','oil','gas']): return 'energy'
    if any(x in s for x in ['bank','financial','insurance','nbfc','finance']): return 'banking'
    if any(x in s for x in ['tech','software','it ','information','computer']): return 'technology'
    if any(x in s for x in ['infra','construction','cement','road','rail','engineer']): return 'infrastructure'
    if any(x in s for x in ['semiconductor','electronic','chip','component']): return 'semiconductor'
    if any(x in s for x in ['consumer','fmcg','retail','food','beverage']): return 'consumer'
    if any(x in s for x in ['auto','vehicle','motor','car','truck']): return 'automobile'
    return 'default'

def safe_round(val, digits=2):
    try:
        return round(float(val), digits)
    except:
        return 0

def analyze_stock(symbol_input):
    symbol = symbol_input.strip().upper()
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol += '.NS'

    print(f"Fetching ticker: {symbol}")
    ticker = yf.Ticker(symbol)

    # Fetch history first - more reliable than info on free hosting
    try:
        hist_1y = ticker.history(period='1y', interval='1d')
        print(f"History rows: {len(hist_1y)}")
    except Exception as e:
        print(f"History error: {e}")
        return {'error': f"Could not fetch data for {symbol_input}. Check your internet and try again. ({str(e)})"}

    if hist_1y is None or len(hist_1y) == 0:
        return {'error': f"No price data found for '{symbol_input}'. Make sure it is a valid NSE symbol like HAL, TCS, RELIANCE, INFY"}

    # Fetch info with fallback
    try:
        info = ticker.info
        print(f"Info keys: {len(info) if info else 0}")
    except Exception as e:
        print(f"Info error (using fallback): {e}")
        info = {}

    # If info is empty, build minimal info from history
    if not isinstance(info, dict) or len(info) < 5:
        last_close = float(hist_1y['Close'].iloc[-1])
        info = {
            'currentPrice': last_close,
            'longName': symbol.replace('.NS',''),
            'sector': 'Unknown',
            'industry': 'Unknown',
        }

    try:
        hist_3mo = ticker.history(period='3mo', interval='1d')
    except:
        hist_3mo = hist_1y.tail(60)

    if hist_1y.empty:
        return {'error': f"No price history found for {symbol}. Try again later."}

    try: income   = ticker.financials
    except: income = pd.DataFrame()
    try: cashflow = ticker.cashflow
    except: cashflow = pd.DataFrame()

    r = {}

    # ── Basic ──
    r['name']     = info.get('longName', symbol)
    r['symbol']   = symbol
    r['sector']   = info.get('sector', 'Unknown')
    r['industry'] = info.get('industry', 'Unknown')
    r['website']  = info.get('website', '')

    cmp = info.get('currentPrice') or info.get('regularMarketPrice') or hist_1y['Close'].iloc[-1]
    r['cmp'] = safe_round(cmp, 2)

    mcap = info.get('marketCap', 0) or 0
    if mcap >= 2e11:   r['cap_type'] = 'Large Cap'
    elif mcap >= 5e9:  r['cap_type'] = 'Mid Cap'
    else:              r['cap_type'] = 'Small Cap'

    if mcap >= 1e12:   r['market_cap'] = f"₹{mcap/1e12:.2f} Lakh Cr"
    elif mcap >= 1e9:  r['market_cap'] = f"₹{mcap/1e9:.0f}B"
    else:              r['market_cap'] = f"₹{mcap/1e6:.0f}M"

    # ── Price levels ──
    r['week52_high']        = safe_round(hist_1y['High'].max())
    r['week52_low']         = safe_round(hist_1y['Low'].min())
    r['discount_from_high'] = safe_round((r['week52_high'] - r['cmp']) / r['week52_high'] * 100) if r['week52_high'] > 0 else 0
    r['yearly_return']      = safe_round((r['cmp'] / hist_1y['Close'].iloc[0] - 1) * 100) if len(hist_1y) > 1 else 0

    # ── Fundamentals ──
    r['pe_ratio']       = safe_round(info.get('trailingPE') or 0)
    r['forward_pe']     = safe_round(info.get('forwardPE') or 0)
    r['pb_ratio']       = safe_round(info.get('priceToBook') or 0)
    r['peg_ratio']      = safe_round(info.get('pegRatio') or 0)
    r['roe']            = safe_round((info.get('returnOnEquity') or 0) * 100)
    r['roa']            = safe_round((info.get('returnOnAssets') or 0) * 100)
    r['profit_margin']  = safe_round((info.get('profitMargins') or 0) * 100)
    r['op_margin']      = safe_round((info.get('operatingMargins') or 0) * 100)
    r['debt_equity']    = safe_round(info.get('debtToEquity') or 0)
    r['current_ratio']  = safe_round(info.get('currentRatio') or 0)
    r['eps']            = safe_round(info.get('trailingEps') or 0)
    r['forward_eps']    = safe_round(info.get('forwardEps') or 0)
    r['book_value']     = safe_round(info.get('bookValue') or 0)
    r['dividend_yield'] = safe_round((info.get('dividendYield') or 0) * 100)
    r['beta']           = safe_round(info.get('beta') or 1)
    r['revenue_growth'] = safe_round((info.get('revenueGrowth') or 0) * 100)
    r['earnings_growth']= safe_round((info.get('earningsGrowth') or 0) * 100)
    r['free_cashflow']  = info.get('freeCashflow') or 0
    r['ev_ebitda']      = safe_round(info.get('enterpriseToEbitda') or 0)

    # ── CAGR from financials ──
    try:
        rev_s = income.loc['Total Revenue'].dropna()
        r['rev_cagr_3y'] = safe_round(((rev_s.iloc[0]/rev_s.iloc[-1])**(1/(len(rev_s)-1))-1)*100) if len(rev_s)>=3 else r['revenue_growth']
    except:
        r['rev_cagr_3y'] = r['revenue_growth']

    try:
        p_s = income.loc['Net Income'].dropna()
        r['profit_cagr_3y'] = safe_round(((p_s.iloc[0]/p_s.iloc[-1])**(1/(len(p_s)-1))-1)*100) if len(p_s)>=3 else r['earnings_growth']
    except:
        r['profit_cagr_3y'] = r['earnings_growth']

    # ── ROCE ──
    try:
        ebit = info.get('ebit') or 0
        ta_  = info.get('totalAssets') or 0
        tl_  = info.get('totalDebt') or 0
        ce   = ta_ - tl_
        r['roce'] = safe_round(ebit/ce*100) if ce > 0 else 0
    except:
        r['roce'] = 0

    # ── Interest Coverage ──
    try:
        op_i = income.loc['Operating Income'].iloc[0] if 'Operating Income' in income.index else 0
        int_e = income.loc['Interest Expense'].iloc[0] if 'Interest Expense' in income.index else 1
        r['interest_coverage'] = safe_round(abs(op_i/int_e)) if int_e else 99
    except:
        r['interest_coverage'] = 0

    # ── FCF ──
    r['fcf_status'] = 'Positive ✅' if r['free_cashflow'] > 0 else 'Negative ⚠️'

    # ── Technicals ──
    if len(hist_1y) >= 30 and ta is not None:
        try:
            h = hist_1y.copy()
            h['RSI']      = ta.momentum.RSIIndicator(h['Close'], window=14).rsi()
            macd_i        = ta.trend.MACD(h['Close'])
            h['MACD']     = macd_i.macd()
            h['MACD_Sig'] = macd_i.macd_signal()
            h['EMA20']    = ta.trend.EMAIndicator(h['Close'], window=20).ema_indicator()
            h['EMA50']    = ta.trend.EMAIndicator(h['Close'], window=50).ema_indicator()
            h['EMA200']   = ta.trend.EMAIndicator(h['Close'], window=200).ema_indicator()
            bb            = ta.volatility.BollingerBands(h['Close'])
            h['BB_up']    = bb.bollinger_hband()
            h['BB_lo']    = bb.bollinger_lband()
        except Exception as e:
            print(f"Technical indicator error: {e}")
            for k in ['rsi','macd','macd_sig','ema20','ema50','ema200','bb_upper','bb_lower','return_1m','return_3m','support','resistance']:
                r[k] = 0
            r['above_ema20'] = r['above_ema50'] = r['above_ema200'] = r['golden_cross'] = r['macd_bull'] = False
            return r

        lt = h.iloc[-1]
        r['rsi']         = safe_round(lt['RSI']) if pd.notna(lt['RSI']) else 50
        r['macd']        = safe_round(lt['MACD']) if pd.notna(lt['MACD']) else 0
        r['macd_sig']    = safe_round(lt['MACD_Sig']) if pd.notna(lt['MACD_Sig']) else 0
        r['ema20']       = safe_round(lt['EMA20']) if pd.notna(lt['EMA20']) else 0
        r['ema50']       = safe_round(lt['EMA50']) if pd.notna(lt['EMA50']) else 0
        r['ema200']      = safe_round(lt['EMA200']) if pd.notna(lt['EMA200']) else 0
        r['bb_upper']    = safe_round(lt['BB_up']) if pd.notna(lt['BB_up']) else 0
        r['bb_lower']    = safe_round(lt['BB_lo']) if pd.notna(lt['BB_lo']) else 0
        r['above_ema20'] = r['cmp'] > r['ema20']
        r['above_ema50'] = r['cmp'] > r['ema50']
        r['above_ema200']= r['cmp'] > r['ema200']
        r['golden_cross']= r['ema50'] > r['ema200']
        r['macd_bull']   = r['macd'] > r['macd_sig']
        r['return_1m']   = safe_round((h['Close'].iloc[-1]/h['Close'].iloc[-20]-1)*100) if len(h)>=20 else 0
        r['return_3m']   = safe_round((h['Close'].iloc[-1]/h['Close'].iloc[-60]-1)*100) if len(h)>=60 else 0
        r['support']     = safe_round(h['Low'].tail(60).min())
        r['resistance']  = safe_round(h['High'].tail(60).max())
    else:
        for k in ['rsi','macd','macd_sig','ema20','ema50','ema200','bb_upper','bb_lower','return_1m','return_3m','support','resistance']:
            r[k] = 0
        r['above_ema20'] = r['above_ema50'] = r['above_ema200'] = r['golden_cross'] = r['macd_bull'] = False

    # ── Sector ──
    sk = get_sector_key(r['sector'])
    si = SECTOR_INTELLIGENCE[sk]
    r['fair_pe_low']   = si['fair_pe_low']
    r['fair_pe_high']  = si['fair_pe_high']
    r['fair_pe_mid']   = (si['fair_pe_low'] + si['fair_pe_high']) / 2
    r['sector_tailwind'] = si['tailwind']
    r['sector_risk']   = si['risk']
    r['govt_support']  = si['govt_support']

    # ── Valuation status ──
    r['pe_vs_fair'] = safe_round(r['pe_ratio'] / r['fair_pe_mid'], 2) if r['fair_pe_mid'] and r['pe_ratio'] else 1
    if r['pe_vs_fair'] <= 0.75:   r['valuation_status'] = 'Undervalued'
    elif r['pe_vs_fair'] <= 0.90: r['valuation_status'] = 'Slightly Undervalued'
    elif r['pe_vs_fair'] <= 1.10: r['valuation_status'] = 'Fairly Valued'
    elif r['pe_vs_fair'] <= 1.30: r['valuation_status'] = 'Slightly Overvalued'
    else:                          r['valuation_status'] = 'Overvalued'

    # ── 2Y Target ──
    gr   = min(max(r['profit_cagr_3y']/100, 0.05), 0.40)
    r['growth_rate_pct'] = safe_round(gr*100)
    r['fwd_eps_2y']      = safe_round(r['eps'] * (1+gr)**2) if r['eps'] > 0 else 0
    r['fwd_eps_cons']    = safe_round(r['eps'] * (1+gr*0.75)**2) if r['eps'] > 0 else 0
    r['target_base']     = safe_round(r['fwd_eps_2y'] * r['fair_pe_mid'])
    r['target_cons']     = safe_round(r['fwd_eps_cons'] * si['fair_pe_low'])
    r['target_aggr']     = safe_round(r['fwd_eps_2y'] * si['fair_pe_high'])
    cmp_ = r['cmp'] if r['cmp'] > 0 else 1
    r['upside_base'] = safe_round((r['target_base']/cmp_-1)*100)
    r['upside_cons'] = safe_round((r['target_cons']/cmp_-1)*100)
    r['upside_aggr'] = safe_round((r['target_aggr']/cmp_-1)*100)

    # ── Score ──
    score, rating, breakdown = calculate_score(r)
    r['score']     = score
    r['rating']    = rating
    r['breakdown'] = breakdown

    # ── Decision ──
    rec = generate_recommendation(r, score)
    r['decision']      = rec['decision']
    r['decision_color']= rec['color']
    r['action']        = rec['action']
    r['buy_reasons']   = rec['buy_reasons']
    r['wait_reasons']  = rec['wait_reasons']
    r['risks']         = rec['risks']

    # ── Price history for sparkline (last 30 closes) ──
    closes = hist_1y['Close'].tail(60).round(2).tolist()
    dates  = [str(d.date()) for d in hist_1y.tail(60).index]
    r['price_history'] = {'dates': dates, 'prices': closes}

    r['report_time'] = datetime.now().strftime('%d %b %Y, %I:%M %p')
    return r

def calculate_score(r):
    bd = {}

    # Business Quality (30)
    bq  = 0
    bq += 6 if r['roce'] >= 25 else (4 if r['roce'] >= 18 else (2 if r['roce'] >= 12 else 0))
    bq += 6 if r['roe']  >= 20 else (4 if r['roe']  >= 15 else (2 if r['roe']  >= 10 else 0))
    bq += 8 if r['profit_cagr_3y'] >= 20 else (6 if r['profit_cagr_3y'] >= 12 else (3 if r['profit_cagr_3y'] >= 6 else 0))
    bq += 5 if r['free_cashflow'] > 0 else 0
    bq += 5 if r['profit_margin'] >= 15 else (3 if r['profit_margin'] >= 8 else 1)
    bd['Business Quality'] = min(bq, 30)

    # Financial Strength (20)
    fs  = 0
    fs += 8 if r['debt_equity'] <= 0.3 else (6 if r['debt_equity'] <= 0.7 else (3 if r['debt_equity'] <= 1.5 else 0))
    fs += 7 if r['interest_coverage'] >= 10 else (5 if r['interest_coverage'] >= 5 else (2 if r['interest_coverage'] >= 2 else 0))
    fs += 5 if r['current_ratio'] >= 2 else (3 if r['current_ratio'] >= 1.2 else 1)
    bd['Financial Strength'] = min(fs, 20)

    # Valuation (20)
    pv = r['pe_vs_fair']
    val = 20 if pv<=0.6 else (16 if pv<=0.75 else (12 if pv<=0.9 else (8 if pv<=1.1 else (4 if pv<=1.3 else 0))))
    if r['peg_ratio'] > 0 and r['peg_ratio'] <= 1: val += 2
    if r['discount_from_high'] > 30: val += 2
    bd['Valuation'] = max(min(val, 20), 0)

    # Growth Visibility (15)
    gv  = r['sector_tailwind']
    gv += 4 if r['revenue_growth'] >= 20 else (2 if r['revenue_growth'] >= 10 else 0)
    bd['Growth Visibility'] = min(gv, 15)

    # Risk (15)
    rp  = r['sector_risk']
    rp += 3 if r['beta'] > 1.5 else (1 if r['beta'] > 1.2 else 0)
    rp += 2 if r['debt_equity'] > 2 else 0
    bd['Risk Score'] = max(15 - rp, 0)

    total = sum(bd.values())
    bd['TOTAL'] = total

    if total >= 80:   rating = 'STRONG COMPOUNDER'
    elif total >= 60: rating = 'QUALITY BUY'
    elif total >= 40: rating = 'WATCHLIST'
    else:             rating = 'AVOID'

    return total, rating, bd

def generate_recommendation(r, score):
    buy_reasons, wait_reasons, risks = [], [], []

    if r['valuation_status'] in ['Undervalued', 'Slightly Undervalued']:
        buy_reasons.append(f"Stock is {r['valuation_status']} vs fair PE range of {r['fair_pe_low']}x–{r['fair_pe_high']}x")
    elif r['valuation_status'] == 'Overvalued':
        wait_reasons.append(f"Trading above fair PE. Current PE {r['pe_ratio']}x vs fair range {r['fair_pe_low']}x–{r['fair_pe_high']}x")

    if r['discount_from_high'] > 25:
        buy_reasons.append(f"Buying {r['discount_from_high']}% below 52-week high — significant discount")
    elif r['discount_from_high'] < 5:
        wait_reasons.append("Trading near 52-week high — higher entry risk right now")

    if r['roce'] >= 20: buy_reasons.append(f"Strong ROCE of {r['roce']}% — excellent capital efficiency")
    if r['profit_cagr_3y'] >= 15: buy_reasons.append(f"Profit growing at {r['profit_cagr_3y']}% CAGR — compounding machine")
    if r['debt_equity'] <= 0.5: buy_reasons.append(f"Very low debt (D/E: {r['debt_equity']}) — financially safe")
    elif r['debt_equity'] > 2: risks.append(f"High debt burden D/E: {r['debt_equity']} — risky in rising rate environment")

    if r['above_ema200']: buy_reasons.append("Price above 200 EMA — confirmed long-term uptrend")
    else: wait_reasons.append("Price below 200 EMA — long-term trend not yet confirmed bullish")

    if r['golden_cross']: buy_reasons.append("Golden Cross signal active — EMA50 above EMA200")

    if r['rsi'] < 45: buy_reasons.append(f"RSI at {r['rsi']} — oversold / good accumulation zone")
    elif r['rsi'] > 75: wait_reasons.append(f"RSI at {r['rsi']} — overbought, wait for RSI to cool to 50–60")

    if r['sector_tailwind'] >= 8: buy_reasons.append(f"Strong sector tailwind: {r['govt_support']}")
    if r['free_cashflow'] > 0: buy_reasons.append("Positive free cash flow — company generates real cash")
    else: risks.append("Negative free cash flow — monitor closely")

    if r['beta'] > 1.5: risks.append(f"High beta ({r['beta']}) — very volatile stock")

    buy_score = len(buy_reasons) - len(wait_reasons)
    if score >= 70 and buy_score >= 3:
        decision = '🟢 STRONG BUY'
        color = 'green'
        action = f"High conviction buy at ₹{r['cmp']:,}. Accumulate in 2–3 tranches over next 4–6 weeks."
    elif score >= 55 and buy_score >= 1:
        decision = '🔵 BUY — ACCUMULATE'
        color = 'blue'
        action = f"Good stock at reasonable price. Buy first tranche now at ₹{r['cmp']:,}. Keep cash for 5–10% dip."
    elif score >= 40:
        decision = '🟡 WAIT FOR BETTER PRICE'
        color = 'amber'
        action = f"Decent business but not ideal entry. Set alert at ₹{round(r['cmp']*0.9):,} (10% lower)."
    else:
        decision = '🔴 AVOID'
        color = 'red'
        action = "Risk/reward not favorable. Capital preservation is priority. Find a better stock."

    return {'decision': decision, 'color': color, 'action': action,
            'buy_reasons': buy_reasons, 'wait_reasons': wait_reasons, 'risks': risks}

# ─── Routes ───────────────────────────────────────────────────────────────────
# Read HTML at startup — more reliable than render_template on some hosts
import os

def get_html():
    # Try template file first, fall back to inline
    template_paths = [
        os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),
        os.path.join(os.getcwd(), 'templates', 'index.html'),
        'templates/index.html',
    ]
    for path in template_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    return "<h1>Template not found</h1><p>templates/index.html missing</p>"

@app.route('/')
def index():
    return HTML_PAGE

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0"/>
<meta name="theme-color" content="#0f172a"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<title>Stock Analyzer India</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root {
    --bg:        #0f172a;
    --surface:   #1e293b;
    --surface2:  #273548;
    --border:    #334155;
    --text:      #f1f5f9;
    --muted:     #94a3b8;
    --green:     #22c55e;
    --green-bg:  #052e16;
    --blue:      #3b82f6;
    --blue-bg:   #0c1a3a;
    --amber:     #f59e0b;
    --amber-bg:  #1c1200;
    --red:       #ef4444;
    --red-bg:    #1f0505;
    --gold:      #fbbf24;
    --radius:    14px;
    --shadow:    0 4px 24px rgba(0,0,0,0.4);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding-bottom: 40px;
  }

  /* ── Header ── */
  .header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
    padding: 20px 16px 16px;
    text-align: center;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
  }
  .header h1 { font-size: 1.2rem; font-weight: 700; color: var(--gold); letter-spacing: 0.5px; }
  .header p  { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }

  /* ── Search ── */
  .search-wrap {
    padding: 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .search-row { display: flex; gap: 10px; }
  .search-input {
    flex: 1;
    background: var(--bg);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 13px 16px;
    color: var(--text);
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-input:focus { border-color: var(--blue); }
  .search-input::placeholder { color: var(--muted); font-weight: 400; }
  .search-btn {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    border: none;
    border-radius: 12px;
    padding: 13px 20px;
    color: #fff;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    white-space: nowrap;
  }
  .search-btn:active { transform: scale(0.97); opacity: 0.9; }
  .search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .quick-label { font-size: 0.72rem; color: var(--muted); margin: 10px 0 6px; }
  .quick-chips { display: flex; flex-wrap: wrap; gap: 7px; }
  .chip {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 5px 13px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    transition: all 0.15s;
  }
  .chip:active, .chip:hover { background: var(--blue); color: #fff; border-color: var(--blue); }

  /* ── Loading ── */
  .loader-wrap {
    display: none;
    flex-direction: column;
    align-items: center;
    padding: 60px 20px;
    gap: 16px;
  }
  .loader-wrap.show { display: flex; }
  .spinner {
    width: 44px; height: 44px;
    border: 3px solid var(--border);
    border-top-color: var(--blue);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loader-text { color: var(--muted); font-size: 0.9rem; }

  /* ── Error ── */
  .error-box {
    display: none;
    margin: 16px;
    background: var(--red-bg);
    border: 1px solid var(--red);
    border-radius: var(--radius);
    padding: 16px;
    color: var(--red);
    font-size: 0.9rem;
    text-align: center;
  }
  .error-box.show { display: block; }

  /* ── Result ── */
  .result { display: none; padding: 0; }
  .result.show { display: block; }

  /* Decision Banner */
  .decision-banner {
    margin: 16px;
    border-radius: var(--radius);
    padding: 20px;
    text-align: center;
    box-shadow: var(--shadow);
  }
  .decision-banner.green  { background: linear-gradient(135deg, #052e16, #064e23); border: 1.5px solid var(--green); }
  .decision-banner.blue   { background: linear-gradient(135deg, #0c1a3a, #0f2347); border: 1.5px solid var(--blue); }
  .decision-banner.amber  { background: linear-gradient(135deg, #1c1200, #2a1a00); border: 1.5px solid var(--amber); }
  .decision-banner.red    { background: linear-gradient(135deg, #1f0505, #2d0808); border: 1.5px solid var(--red); }

  .stock-name  { font-size: 1rem; font-weight: 700; color: var(--muted); margin-bottom: 4px; }
  .stock-price { font-size: 2rem; font-weight: 800; color: var(--text); margin: 6px 0; }
  .decision-text {
    font-size: 1.15rem;
    font-weight: 800;
    margin: 10px 0 6px;
  }
  .decision-banner.green  .decision-text { color: var(--green); }
  .decision-banner.blue   .decision-text { color: var(--blue); }
  .decision-banner.amber  .decision-text { color: var(--amber); }
  .decision-banner.red    .decision-text { color: var(--red); }
  .action-text { font-size: 0.82rem; color: var(--muted); line-height: 1.5; }

  /* Score Ring */
  .score-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    margin: 14px 0 10px;
  }
  .score-ring {
    width: 72px; height: 72px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    border: 3px solid;
    flex-shrink: 0;
  }
  .score-ring.green  { border-color: var(--green); }
  .score-ring.blue   { border-color: var(--blue); }
  .score-ring.amber  { border-color: var(--amber); }
  .score-ring.red    { border-color: var(--red); }
  .score-num  { font-size: 1.4rem; font-weight: 900; line-height: 1; }
  .score-denom{ font-size: 0.65rem; color: var(--muted); }
  .rating-badge {
    font-size: 0.85rem;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 20px;
  }
  .rating-badge.green { background: var(--green-bg); color: var(--green); border: 1px solid var(--green); }
  .rating-badge.blue  { background: var(--blue-bg);  color: var(--blue);  border: 1px solid var(--blue); }
  .rating-badge.amber { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber); }
  .rating-badge.red   { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red); }

  /* Targets */
  .targets-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin: 0 16px 16px;
  }
  .target-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 8px;
    text-align: center;
  }
  .target-label { font-size: 0.65rem; color: var(--muted); font-weight: 600; text-transform: uppercase; }
  .target-price { font-size: 0.95rem; font-weight: 800; color: var(--text); margin: 4px 0 2px; }
  .target-upside { font-size: 0.72rem; font-weight: 700; }
  .up   { color: var(--green); }
  .down { color: var(--red); }

  /* Chart */
  .chart-wrap {
    margin: 0 16px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
  }
  .section-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 12px;
  }
  .chart-canvas { width: 100% !important; height: 130px !important; }

  /* Metrics Grid */
  .metrics-grid {
    margin: 0 16px 16px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
  }
  .metric-label { font-size: 0.68rem; color: var(--muted); font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
  .metric-value { font-size: 1.05rem; font-weight: 800; color: var(--text); }
  .metric-sub   { font-size: 0.68rem; color: var(--muted); margin-top: 2px; }
  .metric-value.good { color: var(--green); }
  .metric-value.bad  { color: var(--red); }
  .metric-value.warn { color: var(--amber); }

  /* Score Breakdown */
  .breakdown-wrap {
    margin: 0 16px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
  }
  .breakdown-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }
  .breakdown-row:last-child { margin-bottom: 0; }
  .breakdown-label { font-size: 0.78rem; color: var(--muted); width: 110px; flex-shrink: 0; }
  .breakdown-bar-bg {
    flex: 1;
    height: 8px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
  }
  .breakdown-bar { height: 100%; border-radius: 4px; transition: width 1s ease; }
  .breakdown-score { font-size: 0.8rem; font-weight: 700; color: var(--text); width: 40px; text-align: right; flex-shrink: 0; }

  /* Technicals */
  .tech-grid {
    margin: 0 16px 16px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .tech-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .tech-label { font-size: 0.72rem; color: var(--muted); }
  .tech-badge {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 10px;
  }
  .tech-badge.bull { background: var(--green-bg); color: var(--green); }
  .tech-badge.bear { background: var(--red-bg);   color: var(--red); }
  .tech-badge.neut { background: var(--surface2); color: var(--muted); }

  /* Reasons */
  .reasons-wrap { margin: 0 16px 16px; display: flex; flex-direction: column; gap: 8px; }
  .reason-item {
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 0.82rem;
    line-height: 1.5;
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  .reason-item.buy  { background: var(--green-bg); border-left: 3px solid var(--green); color: #a7f3d0; }
  .reason-item.wait { background: var(--amber-bg); border-left: 3px solid var(--amber); color: #fde68a; }
  .reason-item.risk { background: var(--red-bg);   border-left: 3px solid var(--red);   color: #fca5a5; }
  .reason-icon { flex-shrink: 0; margin-top: 1px; }

  /* Section header */
  .sec-head {
    margin: 0 16px 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sec-head-line { flex: 1; height: 1px; background: var(--border); }
  .sec-head-text { font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; white-space: nowrap; }

  /* Govt Support */
  .govt-box {
    margin: 0 16px 16px;
    background: linear-gradient(135deg, #0c1a3a, #0f2347);
    border: 1px solid #1d4ed8;
    border-radius: var(--radius);
    padding: 14px;
    font-size: 0.82rem;
    color: #93c5fd;
    line-height: 1.6;
  }
  .govt-box strong { color: var(--blue); display: block; margin-bottom: 4px; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Disclaimer */
  .disclaimer {
    margin: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    font-size: 0.7rem;
    color: var(--muted);
    text-align: center;
    line-height: 1.6;
  }

  /* Top bar meta */
  .meta-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 8px;
  }
  .meta-pill {
    font-size: 0.68rem;
    padding: 3px 10px;
    border-radius: 20px;
    background: rgba(255,255,255,0.07);
    color: var(--muted);
    border: 1px solid var(--border);
  }

  /* Welcome screen */
  .welcome {
    padding: 40px 24px;
    text-align: center;
  }
  .welcome-icon { font-size: 3.5rem; margin-bottom: 16px; }
  .welcome h2  { font-size: 1.1rem; font-weight: 700; color: var(--text); margin-bottom: 8px; }
  .welcome p   { font-size: 0.85rem; color: var(--muted); line-height: 1.6; margin-bottom: 20px; }
  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    text-align: left;
    max-width: 340px;
    margin: 0 auto;
  }
  .feature-item {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 0.83rem;
    color: var(--muted);
  }
  .feature-icon { font-size: 1.2rem; flex-shrink: 0; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>🏦 India Stock Analyzer</h1>
  <p>Professional • Real-Time • AI-Powered</p>
</div>

<!-- Search -->
<div class="search-wrap">
  <div class="search-row">
    <input class="search-input" id="symbolInput" type="text" placeholder="Enter symbol: HAL, TCS..." maxlength="20" autocomplete="off" autocapitalize="characters" spellcheck="false"/>
    <button class="search-btn" id="analyzeBtn" onclick="runAnalysis()">Analyze</button>
  </div>
  <div class="quick-label">Quick pick:</div>
  <div class="quick-chips">
    <span class="chip" onclick="quickSearch('HAL')">HAL</span>
    <span class="chip" onclick="quickSearch('TCS')">TCS</span>
    <span class="chip" onclick="quickSearch('RELIANCE')">RELIANCE</span>
    <span class="chip" onclick="quickSearch('INFY')">INFY</span>
    <span class="chip" onclick="quickSearch('BEL')">BEL</span>
    <span class="chip" onclick="quickSearch('HDFCBANK')">HDFCBANK</span>
    <span class="chip" onclick="quickSearch('SBIN')">SBIN</span>
    <span class="chip" onclick="quickSearch('NTPC')">NTPC</span>
    <span class="chip" onclick="quickSearch('SUNPHARMA')">SUNPHARMA</span>
    <span class="chip" onclick="quickSearch('DIXON')">DIXON</span>
  </div>
</div>

<!-- Loader -->
<div class="loader-wrap" id="loader">
  <div class="spinner"></div>
  <div class="loader-text" id="loaderText">Fetching data from NSE...</div>
</div>

<!-- Error -->
<div class="error-box" id="errorBox"></div>

<!-- Welcome -->
<div class="welcome" id="welcome">
  <div class="welcome-icon">📊</div>
  <h2>Professional Stock Analysis</h2>
  <p>Enter any NSE stock symbol above to get a complete investment analysis with score, targets, and buy/sell recommendation.</p>
  <div class="feature-list">
    <div class="feature-item"><span class="feature-icon">🎯</span>0–100 scoring across 5 pillars</div>
    <div class="feature-item"><span class="feature-icon">💰</span>Valuation-based 2-year price targets</div>
    <div class="feature-item"><span class="feature-icon">📈</span>Live price chart & technical indicators</div>
    <div class="feature-item"><span class="feature-icon">🏛️</span>Government policy & sector tailwinds</div>
    <div class="feature-item"><span class="feature-icon">⚠️</span>Risk analysis & buy/wait/avoid decision</div>
  </div>
</div>

<!-- Result -->
<div class="result" id="result"></div>

<script>
let priceChart = null;

function quickSearch(sym) {
  document.getElementById('symbolInput').value = sym;
  runAnalysis();
}

document.getElementById('symbolInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') runAnalysis();
});

async function runAnalysis() {
  const symbol = document.getElementById('symbolInput').value.trim();
  if (!symbol) return;

  // UI state
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('result').classList.remove('show');
  document.getElementById('errorBox').classList.remove('show');
  document.getElementById('loader').classList.add('show');
  document.getElementById('analyzeBtn').disabled = true;

  const msgs = ['Fetching live data from NSE...','Calculating fundamentals...','Running scoring engine...','Building your report...'];
  let mi = 0;
  const msgInt = setInterval(() => {
    document.getElementById('loaderText').textContent = msgs[Math.min(mi++, msgs.length-1)];
  }, 2000);

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol})
    });

    clearInterval(msgInt);
    document.getElementById('loader').classList.remove('show');
    document.getElementById('analyzeBtn').disabled = false;

    // Safe JSON parse - never crash on empty response
    let data;
    const rawText = await res.text();
    if (!rawText || rawText.trim() === '') {
      document.getElementById('errorBox').textContent = '❌ Server returned empty response. The server may be waking up — please wait 30 seconds and try again.';
      document.getElementById('errorBox').classList.add('show');
      return;
    }
    try {
      data = JSON.parse(rawText);
    } catch(parseErr) {
      document.getElementById('errorBox').textContent = '❌ Server error: ' + rawText.substring(0, 200);
      document.getElementById('errorBox').classList.add('show');
      return;
    }

    if (data.error) {
      document.getElementById('errorBox').textContent = '❌ ' + data.error;
      document.getElementById('errorBox').classList.add('show');
    } else {
      renderResult(data);
    }
  } catch(e) {
    clearInterval(msgInt);
    document.getElementById('loader').classList.remove('show');
    document.getElementById('analyzeBtn').disabled = false;
    document.getElementById('errorBox').textContent = '❌ Network error: ' + e.message + '. Check your connection and try again.';
    document.getElementById('errorBox').classList.add('show');
  }
}

function fmt(n) { return n?.toLocaleString('en-IN') ?? 'N/A'; }
function pct(n) { return (n >= 0 ? '+' : '') + n?.toFixed(1) + '%'; }
function colorClass(color) { return color; }

function pillarColor(score, max) {
  const pct = score/max;
  if (pct >= 0.75) return '#22c55e';
  if (pct >= 0.50) return '#3b82f6';
  if (pct >= 0.25) return '#f59e0b';
  return '#ef4444';
}

function renderResult(d) {
  const col  = d.decision_color;
  const up   = d.upside_base >= 0;
  const html = `
    <!-- Decision Banner -->
    <div class="decision-banner ${col}">
      <div class="stock-name">${d.name}</div>
      <div class="stock-price">₹${fmt(d.cmp)}</div>
      <div class="meta-row">
        <span class="meta-pill">${d.cap_type}</span>
        <span class="meta-pill">${d.sector}</span>
        <span class="meta-pill">${d.market_cap}</span>
        <span class="meta-pill">${d.report_time}</span>
      </div>
      <div class="score-row">
        <div class="score-ring ${col}">
          <div class="score-num" style="color:${col==='green'?'#22c55e':col==='blue'?'#3b82f6':col==='amber'?'#f59e0b':'#ef4444'}">${d.score}</div>
          <div class="score-denom">/ 100</div>
        </div>
        <div>
          <div class="rating-badge ${col}">${d.rating}</div>
          <div style="font-size:0.75rem;color:var(--muted);margin-top:6px">${d.valuation_status}</div>
        </div>
      </div>
      <div class="decision-text">${d.decision}</div>
      <div class="action-text">${d.action}</div>
    </div>

    <!-- 2-Year Targets -->
    <div class="targets-row">
      <div class="target-card">
        <div class="target-label">Conservative</div>
        <div class="target-price">₹${fmt(d.target_cons)}</div>
        <div class="target-upside ${d.upside_cons>=0?'up':'down'}">${pct(d.upside_cons)}</div>
      </div>
      <div class="target-card" style="border-color:${col==='green'?'#22c55e':col==='blue'?'#3b82f6':col==='amber'?'#f59e0b':'#ef4444'}">
        <div class="target-label">Base Case</div>
        <div class="target-price">₹${fmt(d.target_base)}</div>
        <div class="target-upside ${d.upside_base>=0?'up':'down'}">${pct(d.upside_base)}</div>
      </div>
      <div class="target-card">
        <div class="target-label">Aggressive</div>
        <div class="target-price">₹${fmt(d.target_aggr)}</div>
        <div class="target-upside ${d.upside_aggr>=0?'up':'down'}">${pct(d.upside_aggr)}</div>
      </div>
    </div>

    <!-- Price Chart -->
    <div class="chart-wrap">
      <div class="section-title">📈 60-Day Price Chart</div>
      <canvas id="priceChart" class="chart-canvas"></canvas>
    </div>

    <!-- Key Metrics -->
    <div class="sec-head"><div class="sec-head-line"></div><div class="sec-head-text">Key Metrics</div><div class="sec-head-line"></div></div>
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">PE Ratio</div>
        <div class="metric-value ${d.pe_ratio>0&&d.pe_ratio<d.fair_pe_high?'good':'bad'}">${d.pe_ratio || 'N/A'}</div>
        <div class="metric-sub">Fair: ${d.fair_pe_low}x–${d.fair_pe_high}x</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">ROE %</div>
        <div class="metric-value ${d.roe>=15?'good':d.roe>=10?'warn':'bad'}">${d.roe}%</div>
        <div class="metric-sub">Good: ≥15%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">ROCE %</div>
        <div class="metric-value ${d.roce>=20?'good':d.roce>=12?'warn':'bad'}">${d.roce}%</div>
        <div class="metric-sub">Good: ≥20%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Debt / Equity</div>
        <div class="metric-value ${d.debt_equity<=0.5?'good':d.debt_equity<=1.5?'warn':'bad'}">${d.debt_equity}</div>
        <div class="metric-sub">Good: ≤0.5</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Profit CAGR 3Y</div>
        <div class="metric-value ${d.profit_cagr_3y>=15?'good':d.profit_cagr_3y>=6?'warn':'bad'}">${d.profit_cagr_3y}%</div>
        <div class="metric-sub">Good: ≥15%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Net Margin</div>
        <div class="metric-value ${d.profit_margin>=15?'good':d.profit_margin>=8?'warn':'bad'}">${d.profit_margin}%</div>
        <div class="metric-sub">Good: ≥15%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">52W High</div>
        <div class="metric-value">₹${fmt(d.week52_high)}</div>
        <div class="metric-sub ${d.discount_from_high>20?'':''}">–${d.discount_from_high}% from high</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">1Y Return</div>
        <div class="metric-value ${d.yearly_return>=0?'good':'bad'}">${pct(d.yearly_return)}</div>
        <div class="metric-sub">vs Nifty ~12%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">EPS (TTM)</div>
        <div class="metric-value">₹${d.eps}</div>
        <div class="metric-sub">Fwd 2Y: ₹${d.fwd_eps_2y}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">PEG Ratio</div>
        <div class="metric-value ${d.peg_ratio>0&&d.peg_ratio<=1?'good':d.peg_ratio<=2?'warn':'bad'}">${d.peg_ratio||'N/A'}</div>
        <div class="metric-sub">Good: ≤1</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Beta</div>
        <div class="metric-value ${d.beta<=1.2?'good':d.beta<=1.5?'warn':'bad'}">${d.beta}</div>
        <div class="metric-sub">Market volatility</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Free Cash Flow</div>
        <div class="metric-value ${d.free_cashflow>0?'good':'bad'}" style="font-size:0.85rem">${d.fcf_status}</div>
        <div class="metric-sub">${d.free_cashflow>0?'₹'+(d.free_cashflow/1e7).toFixed(0)+'Cr':'Cash burn'}</div>
      </div>
    </div>

    <!-- Score Breakdown -->
    <div class="sec-head"><div class="sec-head-line"></div><div class="sec-head-text">Score Breakdown</div><div class="sec-head-line"></div></div>
    <div class="breakdown-wrap" id="breakdownWrap"></div>

    <!-- Technicals -->
    <div class="sec-head"><div class="sec-head-line"></div><div class="sec-head-text">Technical Signals</div><div class="sec-head-line"></div></div>
    <div class="tech-grid">
      <div class="tech-item"><span class="tech-label">RSI (14)</span><span class="tech-badge ${d.rsi<45?'bull':d.rsi>70?'bear':'neut'}">${d.rsi} ${d.rsi<45?'↓Oversold':d.rsi>70?'↑Overbought':'Neutral'}</span></div>
      <div class="tech-item"><span class="tech-label">MACD</span><span class="tech-badge ${d.macd_bull?'bull':'bear'}">${d.macd_bull?'Bullish':'Bearish'}</span></div>
      <div class="tech-item"><span class="tech-label">vs EMA 20</span><span class="tech-badge ${d.above_ema20?'bull':'bear'}">${d.above_ema20?'Above ✅':'Below ❌'}</span></div>
      <div class="tech-item"><span class="tech-label">vs EMA 50</span><span class="tech-badge ${d.above_ema50?'bull':'bear'}">${d.above_ema50?'Above ✅':'Below ❌'}</span></div>
      <div class="tech-item"><span class="tech-label">vs EMA 200</span><span class="tech-badge ${d.above_ema200?'bull':'bear'}">${d.above_ema200?'Above ✅':'Below ❌'}</span></div>
      <div class="tech-item"><span class="tech-label">Golden Cross</span><span class="tech-badge ${d.golden_cross?'bull':'neut'}">${d.golden_cross?'Active ✅':'Not Yet'}</span></div>
      <div class="tech-item"><span class="tech-label">1M Return</span><span class="tech-badge ${d.return_1m>=0?'bull':'bear'}">${pct(d.return_1m)}</span></div>
      <div class="tech-item"><span class="tech-label">3M Return</span><span class="tech-badge ${d.return_3m>=0?'bull':'bear'}">${pct(d.return_3m)}</span></div>
      <div class="tech-item"><span class="tech-label">Support</span><span class="tech-badge neut">₹${fmt(d.support)}</span></div>
      <div class="tech-item"><span class="tech-label">Resistance</span><span class="tech-badge neut">₹${fmt(d.resistance)}</span></div>
    </div>

    <!-- Buy/Wait/Risk Reasons -->
    <div class="sec-head"><div class="sec-head-line"></div><div class="sec-head-text">Analysis Signals</div><div class="sec-head-line"></div></div>
    <div class="reasons-wrap" id="reasonsWrap"></div>

    <!-- Govt Support -->
    <div class="sec-head"><div class="sec-head-line"></div><div class="sec-head-text">Sector & Policy</div><div class="sec-head-line"></div></div>
    <div class="govt-box">
      <strong>🏛️ Government Support — ${d.sector}</strong>
      ${d.govt_support}
      <br/><br/>
      <strong style="color:#fbbf24">📊 Fair PE Range</strong>
      ${d.fair_pe_low}x – ${d.fair_pe_high}x &nbsp;|&nbsp; Current PE: ${d.pe_ratio}x &nbsp;|&nbsp; Status: <strong>${d.valuation_status}</strong>
    </div>

    <!-- Disclaimer -->
    <div class="disclaimer">
      ⚠️ For educational purposes only. Not SEBI-registered investment advice.<br/>
      Always consult a qualified financial advisor before investing real money.<br/>
      Data sourced from Yahoo Finance. May be delayed by 15–20 minutes.
    </div>
  `;

  const resultDiv = document.getElementById('result');
  resultDiv.innerHTML = html;
  resultDiv.classList.add('show');

  // Scroll to top of result
  resultDiv.scrollIntoView({behavior: 'smooth', block: 'start'});

  // Render score breakdown bars
  const bd = d.breakdown;
  const pillars = [
    {name:'Business Quality', score: bd['Business Quality'], max: 30},
    {name:'Financial Strength', score: bd['Financial Strength'], max: 20},
    {name:'Valuation', score: bd['Valuation'], max: 20},
    {name:'Growth Visibility', score: bd['Growth Visibility'], max: 15},
    {name:'Risk Score', score: bd['Risk Score'], max: 15},
  ];
  const bwrap = document.getElementById('breakdownWrap');
  bwrap.innerHTML = pillars.map(p => `
    <div class="breakdown-row">
      <div class="breakdown-label">${p.name}</div>
      <div class="breakdown-bar-bg">
        <div class="breakdown-bar" style="width:${(p.score/p.max*100).toFixed(0)}%;background:${pillarColor(p.score,p.max)}"></div>
      </div>
      <div class="breakdown-score">${p.score}/${p.max}</div>
    </div>
  `).join('');

  // Render reasons
  const rwrap = document.getElementById('reasonsWrap');
  let rhtml = '';
  d.buy_reasons.forEach(r => rhtml += `<div class="reason-item buy"><span class="reason-icon">✅</span>${r}</div>`);
  d.wait_reasons.forEach(r => rhtml += `<div class="reason-item wait"><span class="reason-icon">⚠️</span>${r}</div>`);
  d.risks.forEach(r => rhtml += `<div class="reason-item risk"><span class="reason-icon">🔴</span>${r}</div>`);
  if (!rhtml) rhtml = '<div class="reason-item wait"><span class="reason-icon">ℹ️</span>Insufficient data for detailed signal analysis.</div>';
  rwrap.innerHTML = rhtml;

  // Render chart
  if (priceChart) { priceChart.destroy(); priceChart = null; }
  const ctx = document.getElementById('priceChart');
  if (ctx && d.price_history && d.price_history.prices.length > 0) {
    const prices = d.price_history.prices;
    const labels = d.price_history.dates;
    const minP = Math.min(...prices) * 0.995;
    const maxP = Math.max(...prices) * 1.005;
    const gradColor = col==='green'?'34,197,94':col==='blue'?'59,130,246':col==='amber'?'245,158,11':'239,68,68';

    priceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: prices,
          borderColor: `rgb(${gradColor})`,
          backgroundColor: ctx => {
            const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, 130);
            gradient.addColorStop(0, `rgba(${gradColor},0.3)`);
            gradient.addColorStop(1, `rgba(${gradColor},0.0)`);
            return gradient;
          },
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: {display:false}, tooltip: {
          callbacks: { label: ctx => '₹' + ctx.parsed.y.toLocaleString('en-IN') }
        }},
        scales: {
          x: { display: false },
          y: {
            min: minP, max: maxP,
            ticks: { color: '#64748b', font:{size:9}, callback: v => '₹'+Math.round(v).toLocaleString('en-IN') },
            grid: { color: '#1e293b' }
          }
        }
      }
    });
  }
}
</script>
</body>
</html>
"""

@app.route('/analyze', methods=['POST'])
def analyze():
    import traceback, json
    symbol = 'UNKNOWN'
    try:
        # Parse request safely
        raw = request.get_data(as_text=True)
        print(f"Raw request data: {raw[:100]}")
        try:
            data = json.loads(raw) if raw else {}
        except:
            data = {}
        symbol = data.get('symbol', '').strip().upper()
        print(f"Analyzing symbol: {symbol}")
        if not symbol:
            return jsonify({'error': 'Please enter a stock symbol'})
        result = analyze_stock(symbol)
        if result is None:
            return jsonify({'error': f'No data for {symbol}'})
        print(f"Analysis complete for {symbol}: score={result.get('score','?')}")
        return jsonify(result)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"ANALYZE ERROR for {symbol}:\n{tb}")
        return jsonify({'error': f'{str(e)}'})


@app.route('/health')
def health():
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    cwd_path = os.path.join(os.getcwd(), 'templates', 'index.html')
    libs = {}
    try:
        import yfinance; libs['yfinance'] = 'ok'
    except Exception as e: libs['yfinance'] = str(e)
    try:
        import pandas; libs['pandas'] = pandas.__version__
    except Exception as e: libs['pandas'] = str(e)
    try:
        import ta; libs['ta'] = 'ok'
    except Exception as e: libs['ta'] = str(e)
    return jsonify({
        'status': 'running',
        'cwd': os.getcwd(),
        'template_exists_abs': os.path.exists(template_path),
        'template_exists_cwd': os.path.exists(cwd_path),
        'files_in_cwd': os.listdir(os.getcwd()),
        'libs': libs
    })


@app.route('/test/<symbol>')
def test_symbol(symbol):
    import traceback
    result = {}
    try:
        import yfinance as yf
        result['yfinance'] = 'imported ok'
        t = yf.Ticker(symbol + '.NS')
        result['ticker_created'] = 'ok'
        info = t.info
        result['info_keys'] = len(info) if info else 0
        result['price'] = info.get('currentPrice') or info.get('regularMarketPrice', 'not found')
        result['name'] = info.get('longName', 'not found')
        hist = t.history(period='5d', interval='1d')
        result['hist_rows'] = len(hist)
        result['status'] = 'SUCCESS'
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
