"""Phone-width checks for the browser daemon, inside a same-origin iframe.

Firefox's set_viewport_size resizes the window, and the window cannot go below about 500 px, so a 375 px
check cannot be made by resizing. A page loaded into an iframe 375 CSS px wide sees the real width in its
media queries. The parent page is hidden behind the frame, so a full-page screenshot shows the frame alone.
"""
import json

PHONE_FRAME_ID = "tf-phone-frame"
DESKTOP_MIN_WIDTH = 1024  # wider than this is measured in the window itself; narrower widths use the frame


def phone_open_js(width: int, height: int = 900) -> str:
    """Load the current page into a `width` px frame, wait for it, and measure it there."""
    return f"""async () => {{
  const old = document.getElementById('{PHONE_FRAME_ID}'); if (old) old.remove();
  const frame = document.createElement('iframe'); frame.id = '{PHONE_FRAME_ID}';
  frame.style.cssText = 'position:absolute;top:0;left:0;width:{width}px;height:{height}px;border:0;background:#fff;visibility:visible;z-index:2147483647';
  document.documentElement.style.background = '#fff';
  document.body.style.visibility = 'hidden';
  frame.src = location.href;
  const loaded = new Promise(r => frame.addEventListener('load', r, {{ once: true }}));
  document.body.appendChild(frame);
  await loaded;
  await new Promise(r => setTimeout(r, 3000));
  const doc = frame.contentDocument, win = frame.contentWindow;
  frame.style.height = doc.documentElement.scrollHeight + 'px';
  const right = win.innerWidth + 1;
  const wide = Array.from(doc.querySelectorAll('body *'))
    .filter(e => e.getBoundingClientRect().right > right && e.getBoundingClientRect().width > 0)
    .slice(0, 3).map(e => e.tagName.toLowerCase() + '.' + String(e.className).trim().split(/\\s+/).slice(0, 2).join('.'));
  const themes = Array.from(doc.documentElement.classList).filter(c => c.startsWith('app-theme-'));
  return {{ width: win.innerWidth, scrollWidth: doc.documentElement.scrollWidth,
           overflow: doc.documentElement.scrollWidth > right, wide: wide, themes: themes }};
}}"""


PHONE_CLOSE_JS = f"""() => {{
  const frame = document.getElementById('{PHONE_FRAME_ID}'); if (frame) frame.remove();
  document.body.style.visibility = ''; document.documentElement.style.background = '';
  return true;
}}"""


def phone_run_js(source: str) -> str:
    """Run a page check (an `async () => {...}` source) inside the open frame, in the frame's own realm."""
    return f"""async () => {{
  const frame = document.getElementById('{PHONE_FRAME_ID}');
  if (!frame) return {{ error: 'no phone frame open' }};
  const check = frame.contentWindow.eval('(' + {json.dumps(source)} + ')');
  return await check();
}}"""
