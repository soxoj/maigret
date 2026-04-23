# Maigret

<div align="center">
  <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="220" alt="Maigret logo"/>
</div>

**Maigret** collects a dossier on a person **by username only**, checking for accounts on a huge number of sites and gathering all the available information from web pages. No API keys required.

## Installation

Google Cloud Shell does not ship with all the system libraries Maigret needs (`libcairo2-dev`, `pkg-config`). The helper script below installs them and then builds Maigret from the cloned source.

Copy the command and run it in the Cloud Shell terminal:

```bash
./utils/cloudshell_install.sh
```

When the script finishes, verify the install:

```bash
maigret --version
```

## Usage examples

Run a basic search for a username. By default Maigret checks the **500 highest-ranked sites by traffic** — pass `-a` to scan the full 3,000+ database.

```bash
maigret soxoj
```

Search several usernames at once:

```bash
maigret user1 user2 user3
```

Narrow the run to sites related to cryptocurrency via the `crypto` tag (you can also use country tags):

```bash
maigret vitalik.eth --tags crypto
```

Generate reports in HTML, PDF, and XMind 8 formats:

```bash
maigret soxoj --html
maigret soxoj --pdf
maigret soxoj --xmind
```

Download a generated report from Cloud Shell to your local machine:

```bash
cloudshell download reports/report_soxoj.pdf
```

Tune reliability on flaky networks — raise the timeout and retry failed checks:

```bash
maigret soxoj --timeout 60 --retries 2
```

For the full list of options see `maigret --help` or the [CLI documentation](https://maigret.readthedocs.io/en/latest/command-line-options.html).

## Further reading

Full project documentation: [maigret.readthedocs.io](https://maigret.readthedocs.io/)
