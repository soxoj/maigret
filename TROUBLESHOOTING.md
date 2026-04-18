# Troubleshooting

Common issues when running Maigret and how to fix them. If none of this helps, [open an issue](https://github.com/soxoj/maigret/issues) with the output of `maigret --version` and the exact command you ran.

## "Lots of sites fail / timeout / return 403"

This is by far the most common report. It almost always comes from anti-bot protection (Cloudflare, DDoS-Guard, Akamai, etc.) or a slow network — not from a bug in Maigret.

**Results vary a lot depending on where you run from.** The same command on the same username can produce very different output on:

- **Mobile internet** (4G/5G) — usually the best results. Carrier NAT shares your IP with thousands of real users, so WAFs rarely block it.
- **Home broadband** — generally good, though some ISPs are reputation-flagged.
- **Hosting / cloud / VPS infrastructure** (AWS, GCP, DigitalOcean, Hetzner, etc.) — the worst case. Datacenter IP ranges are blanket-blocked or challenged by most WAFs, so you will see many false negatives and 403s.

If a run looks suspiciously empty, **try a different network before assuming Maigret is broken**: tether from your phone, switch between Wi-Fi and mobile, or move the run off a VPS onto a residential machine. Comparing results across two networks is also the fastest way to tell whether a missing account is genuinely missing or just blocked on the current IP.

Once you have a sense of the baseline, try these tweaks in order:

1. **Raise the timeout.** The default is 30 seconds. On mobile networks or for slow sites, bump it:
   ```bash
   maigret user --timeout 60
   ```
2. **Retry failed checks.** Transient 5xx / timeouts often clear on a second try:
   ```bash
   maigret user --retries 2
   ```
3. **Lower parallelism.** Some WAFs rate-limit aggressively. Maigret defaults to 100 concurrent connections (`-n` / `--max-connections`) — dropping this makes you look less like a scanner:
   ```bash
   maigret user -n 20
   ```
4. **Route through a residential proxy.** Datacenter IPs (AWS, GCP, DigitalOcean) are blanket-blocked by many WAFs. A residential / mobile proxy usually fixes this:
   ```bash
   maigret user --proxy http://user:pass@residential-proxy:port
   ```
   Note: Tor (`--tor-proxy`) rarely helps here — most WAFs block Tor exit nodes just as aggressively as datacenter IPs. Use Tor only when you actually need to reach `.onion` sites (see below).

If specific sites *always* fail regardless of the above, they are likely broken in the database (stale markers, new WAF, site redesign). Report them with `--print-errors` output so a maintainer can look at the check config.

## "No results at all" / "maigret: command not found"

- **`command not found`** — `pip install maigret` put the binary under `~/.local/bin` (Linux/macOS) or `%APPDATA%\Python\Scripts` (Windows). Add that directory to `PATH`, or run `python3 -m maigret user` instead.
- **Empty output** — check that you actually passed a username; `maigret` alone prints help. Also confirm Python 3.10+ with `python3 --version`.

## "SSL / certificate errors"

Usually caused by a corporate MITM proxy or an outdated `certifi` bundle.

```bash
pip install --upgrade certifi
```

If you are behind a corporate proxy, set `HTTPS_PROXY` / `HTTP_PROXY` environment variables and pass `--proxy "$HTTPS_PROXY"` so Maigret uses the same route.

## ".onion / .i2p sites are skipped"

These sites only load through the matching gateway. Start your Tor or I2P daemon first, then:

```bash
# Tor
maigret user --tor-proxy socks5://127.0.0.1:9050

# I2P
maigret user --i2p-proxy http://127.0.0.1:4444
```

Maigret does not launch or manage these daemons — they must already be running.

## "The PDF / XMind / HTML report looks wrong"

- **PDF** — requires `weasyprint` and its system dependencies (Pango, Cairo, GDK-PixBuf). On Debian/Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`. macOS: `brew install pango`.
- **XMind** — the `--xmind` flag generates **XMind 8** files. XMind 2022+ (Zen / XMind 2023) uses a different format and will not open them. Use XMind 8 or convert via `--html`.
- **HTML** looks unstyled — open it through a local file path (`file:///...`), not via a preview pane that strips CSS.

## "The site database is out of date"

Maigret auto-fetches a fresh `data.json` from GitHub once every 24 hours. To force-refresh now:

```bash
maigret user --force-update
```

To run entirely against the local built-in copy (e.g. offline):

```bash
maigret user --no-autoupdate
```

## Still stuck?

- [Open an issue](https://github.com/soxoj/maigret/issues) — include your OS, Python version, Maigret version, and the full command.
- Ask in [GitHub Discussions](https://github.com/soxoj/maigret/discussions) or the [Telegram](https://t.me/soxoj) channel.
