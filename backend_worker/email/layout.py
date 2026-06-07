"""
Email layout — clean, Lysa-inspired HTML wrapper.
No emojis, neutral typography, single accent color.
Light theme only (email clients vary).
"""

BASE_STYLES = """
<style>
  body { margin: 0; padding: 0; background-color: #F8F9FB; font-family: 'Inter', -apple-system, sans-serif; }
  .wrapper { max-width: 600px; margin: 0 auto; padding: 24px; }
  .card { background: #FFFFFF; border-radius: 16px; padding: 24px; border: 1px solid #E3E6EC; }
  .header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
  .header h1 { font-size: 16px; font-weight: 600; color: #14181F; margin: 0; letter-spacing: -0.01em; }
  .footer { text-align: center; padding: 16px; font-size: 11px; color: #8B929F; }
  .footer a { color: #1D4ED8; text-decoration: underline; }
</style>
"""


def layout(content: str) -> str:
    """Wrap content in a full HTML email."""
    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {BASE_STYLES}
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" stroke-width="2">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
        <polyline points="17 6 23 6 23 12"/>
      </svg>
      <h1>MarketScan</h1>
    </div>
    <div class="card">
      {content}
    </div>
    <div class="footer">
      <p>MarketScan — personlig aktieanalys</p>
      <p><a href="{{unsubscribe_url}}">Avregistrera från e-postnotiser</a></p>
    </div>
  </div>
</body>
</html>"""


def section(text: str) -> str:
    """A text section inside the card."""
    return f'<p style="font-size: 13px; line-height: 1.6; color: #4A5567; margin: 0 0 12px 0;">{text}</p>'


def metric_row(label: str, value: str) -> str:
    """A label-value pair row."""
    return f"""
    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 12px; border-bottom: 1px solid #E3E6EC;">
      <span style="color: #8B929F;">{label}</span>
      <span style="color: #14181F; font-weight: 500; font-variant-numeric: tabular-nums;">{value}</span>
    </div>"""


def stock_table(rows: list[tuple[str, str, str, str]]) -> str:
    """Stock table: ticker, name, signal, score.
    Each row: (ticker, name, signal, score)
    """
    lines = []
    for ticker, name, signal, score in rows:
        lines.append(f"""
        <tr>
          <td style="padding: 6px 8px; font-size: 11px; color: #14181F; font-weight: 600;">{ticker}</td>
          <td style="padding: 6px 8px; font-size: 11px; color: #4A5567;">{name}</td>
          <td style="padding: 6px 8px; font-size: 11px; color: #15803D;">{signal}</td>
          <td style="padding: 6px 8px; font-size: 11px; color: #14181F; font-variant-numeric: tabular-nums;">{score}</td>
        </tr>""")
    return f"""
    <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
      <thead>
        <tr style="border-bottom: 1px solid #E3E6EC;">
          <th style="padding: 6px 8px; font-size: 10px; color: #8B929F; text-align: left;">Ticker</th>
          <th style="padding: 6px 8px; font-size: 10px; color: #8B929F; text-align: left;">Namn</th>
          <th style="padding: 6px 8px; font-size: 10px; color: #8B929F; text-align: left;">Signal</th>
          <th style="padding: 6px 8px; font-size: 10px; color: #8B929F; text-align: left;">Betyg</th>
        </tr>
      </thead>
      <tbody>
        {''.join(lines)}
      </tbody>
    </table>"""


def button(text: str, url: str) -> str:
    """CTA button."""
    return f"""
    <div style="text-align: center; margin: 16px 0;">
      <a href="{url}" style="display: inline-block; padding: 10px 24px; border-radius: 8px;
         background: #1D4ED8; color: #FFFFFF; font-size: 13px; font-weight: 500;
         text-decoration: none;">{text}</a>
    </div>"""
