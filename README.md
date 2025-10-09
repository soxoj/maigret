# Maigret Expanded

<p align="center">
  <p align="center">
    <a href="https://pypi.org/project/maigret/">
        <img alt="PyPI version badge for Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" />
    </a>
    <a href="https://pypi.org/project/maigret/">  
        <img alt="PyPI download count for Maigret" src="https://img.shields.io/pypi/dw/maigret?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="Minimum Python version required: 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret/blob/main/LICENSE">
        <img alt="License badge for Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="View count for Maigret project" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" />
    </a>
  </p>
  <p align="center">
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300"/>
  </p>
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

agent@chatgpt:/$ cat <<'EOF' > /home/oai/share/updated_readme.md
# Maigret Expanded

This repository is a maintained fork of the original [Maigret](https://github.com/soxoj/maigret) project.  **Maigret Expanded** builds on Maigret’s powerful username‑based OSINT tool by adding optional integrations and extra site checkers.  The core Maigret functionality remains intact, but you can opt in to API‑backed checks (e.g., Shodan) or your own custom modules via a simple environment variable.

> **What’s the difference?**  
> Maigret searches hundreds of sites for a username and aggregates profile data.  **Maigret Expanded** includes everything in the upstream project plus optional "extras" you can enable at runtime.  These extras let you add API services or additional site definitions via a JSON file.  If you don’t enable extras, the tool behaves exactly like the original Maigret.

## Features

### Inherited from Maigret

- Parses profile pages and extracts usernames, names, links to other social profiles, and more.  
- Performs recursive searches using new usernames or IDs found on profile pages.  
- Supports tag filtering for categories (e.g., `--tags photo,dating`).  
- Detects censorship/captchas and retries requests.  
- Generates HTML, PDF and XMind reports (XMind 8 only).  

For a detailed description of Maigret’s default features, see the [original documentation](https://maigret.readthedocs.io/en/latest/features.html).

### Additional in Maigret Expanded

- **Opt‑in extras** via `sites_extra.json` – supply a JSON file with extra site definitions or API modules and enable it at runtime via an environment variable.  
- **API integration** – example checkers are provided for API services such as Shodan.  To use them, add the site entry to your extras file and set the corresponding API key as an environment variable (e.g., `SHODAN_API_KEY`).  Without a key, API checks remain disabled.  
- **Extensibility** – you can create your own modules in `maigret_sites_example/` and reference them in your extras file.  Each module must be opt‑in and disabled by default.

## Installation

Maigret Expanded is not distributed on PyPI; install it directly from this repository.

1. **Clone and install locally** (Python ≥3.10; 3.11 recommended):
   ```bash
   git clone https://github.com/dmoney96/maigretexpanded.git
   cd maigretexpanded
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install .
   ```

2. **Install from GitHub without cloning**:
   ```bash
   pip install git+https://github.com/dmoney96/maigretexpanded.git@feature/add-more-sites
   ```
   Replace `feature/add-more-sites` with the branch you want if it changes.

> **Note**: If you only want the original Maigret tool, install it from PyPI (`pip install maigret`) or use the upstream repository.  Windows binaries, Docker images and cloud‑shell buttons referenced below apply to the original project.

## Using optional extras

Extras are off by default.  To enable them:

1. Create or edit `sites_extra.json` with your extra definitions.  For example, a Shodan entry might look like:
   ```json
   {
     "shodan": {
       "name": "Shodan",
       "url": "https://api.shodan.io/shodan/host/search?query={username}",
       "type": "username",
       "priority": 120,
       "enabled_by_default": false,
       "notes": "Opt‑in: requires SHODAN_API_KEY and a custom checker"
     }
   }
   ```
2. Set the environment variable `MAIGRET_EXTRA_SITES` to the path of your JSON file:
   ```bash
   export MAIGRET_EXTRA_SITES="/path/to/your/sites_extra.json"
   ```
3. (Optional) set any API keys needed by extras:
   ```bash
   export SHODAN_API_KEY="your_real_key_here"
   ```
4. Run Maigret as usual:
   ```bash
   maigret username
   ```

If `MAIGRET_EXTRA_SITES` is unset, Maigret Expanded behaves exactly like the upstream tool.

## Usage examples

```bash
# Basic usage (no extras)
maigret username

# Generate reports
maigret username --html
maigret username --pdf
maigret username --xmind    # XMind 8 format

# Use tag filters
maigret username --tags photo,dating

# Search multiple usernames on all sites
maigret user1 user2 user3 -a

# Enable extras and run
export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"
# optionally set SHODAN_API_KEY or other keys here
maigret username
```

### Web interface

Maigret Expanded retains the original web UI.  Start it with:

```bash
maigret --web 5000
```

Open `http://127.0.0.1:5000` in your browser.  Enter one or more usernames and view results, graphs, and reports in your browser.  Extras will be used if `MAIGRET_EXTRA_SITES` is set.

## Contributing

Contributions are welcome!  To add new default sites, please contribute to the [upstream Maigret project](https://github.com/soxoj/maigret).  To add API‑based checkers or custom site definitions for Maigret Expanded:

- Add your checker code to `maigret_sites_example/` and include unit tests that mock network calls.
- Create an entry in your own `sites_extra.json` with `enabled_by_default: false`.
- Document any required environment variables (e.g., API keys).
- Submit a pull request.

## Disclaimer

**This tool is intended for lawful, educational purposes only.**  Users are responsible for ensuring compliance with all applicable laws and regulations in their jurisdiction.  Adding API integrations may have their own terms of service; use them responsibly.  The authors of this fork are not liable for misuse of the software.

## License

Maigret Expanded is licensed under the MIT License, the same as the upstream Maigret and the Sherlock Project.
EOF
