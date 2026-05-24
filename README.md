# Email Domain Scraper

Welcome to the Barbie Bitch Cult Email Scraper:  your OSINT weapon for ripping contact lists out of the very institutions that profited off locking kids in hell. While TTI programs were busy charging desperate parents $20k a month to emotionally waterboard teenagers, we’ve been quietly building scrapers that harvest their staff emails, intake coordinators, and “executive leadership” faster than they can shred the evidence. This scraper helps researchers, advocates, journalists, and survivors collect email addresses that institutions have already exposed on their own websites, then save those findings into a spreadsheet for review, archiving, and accountability work. Use it lawfully, document carefully, and keep the receipts. The cult sends its regards. 

`email-scraper` crawls a website and writes email addresses exposed in page text or linked through page URLs to a CSV file.

It uses only Python's built-in libraries. There are no third-party package dependencies.

By default, it:

- Crawls only the starting host.
- Honors `robots.txt`.
- Limits the crawl to 100 pages.
- Waits briefly between requests.
- Writes one row per unique `email`, `source_url`, and `discovery_type`.

## What You Need

You need two things:

1. This project folder on your computer.
2. Python 3.9 or newer.

You do **not** need to install extra Python packages such as `requests`, `beautifulsoup`, or `pandas`. The scraper has no third-party dependencies.

## Step 1: Put This Project Somewhere Easy

Put the project folder somewhere easy to find, such as your Desktop or Documents folder.

If the folder is still zipped, unzip it first:

Windows 11:

1. Right-click the `.zip` file.
2. Click **Extract All**.
3. Click **Extract**.
4. Move the extracted folder to your Desktop or Documents folder.

macOS:

1. Double-click the `.zip` file.
2. Move the extracted folder to your Desktop or Documents folder.

## Step 2A: Install Python on Windows 11

1. Download Python from <https://www.python.org/downloads/windows/>.
2. Click the newest **Python 3** download button.
3. Open the installer you downloaded.
4. On the first installer screen, check the box labeled **Add python.exe to PATH**. This checkbox is important.
5. Click **Install Now**.
6. When installation finishes, click **Close**.

Check that Python works:

1. Click the Windows Start button.
2. Type `cmd`.
3. Press Enter to open Command Prompt.
4. Copy and paste this command, then press Enter:

```bat
py --version
```

You should see something like `Python 3.12.4`.

Now check that Python's installer tool works:

```bat
py -m pip --version
```

You should see version information. If either command fails, close Command Prompt, open it again, and retry.

## Step 2B: Install Python on macOS

1. Download Python from <https://www.python.org/downloads/macos/>.
2. Click the newest **Python 3** download button.
3. Open the `.pkg` installer you downloaded.
4. Follow the installer prompts.
5. When installation finishes, close the installer.

Check that Python works:

1. Press Command + Space.
2. Type `Terminal`.
3. Press Return to open Terminal.
4. Copy and paste this command, then press Return:

```bash
python3 --version
```

You should see something like `Python 3.12.4`.

Now check that Python's installer tool works:

```bash
python3 -m pip --version
```

You should see version information.

## Step 3: Open This Project Folder in the Command Line

You must run the install command from inside the project folder. The project folder is the folder that contains this `README.md` file.

Windows 11:

1. Open the project folder in File Explorer.
2. Click the address bar at the top of File Explorer.
3. Type `cmd`.
4. Press Enter.

A Command Prompt window should open already inside the project folder.

macOS:

1. Open Terminal.
2. Type `cd ` with a space after it.
3. Drag the project folder into the Terminal window.
4. Press Return.

The command should look something like this:

```bash
cd /Users/yourname/Desktop/email-domain-scraper
```

## Step 4: Install the Scraper

Install the scraper from inside the project folder.

Windows 11:

```bat
py -m pip install --force-reinstall .
```

macOS:

```bash
python3 -m pip install --force-reinstall .
```

This installs the `email-scraper` command. The dot at the end of the command means "install this folder."

If installation works, you can start the scraper with:

```bash
email-scraper
```

If `email-scraper` is not recognized, use the direct Python command instead.

Windows 11:

```bat
py -m email_scraper
```

macOS:

```bash
python3 -m email_scraper
```

## Quick Fixes

If you see `No module named email_scraper`, you are probably not inside the project folder. Go back to **Step 3**.

If Windows says `py` is not recognized, reinstall Python and make sure **Add python.exe to PATH** is checked.

If macOS says `python3` is not found, reinstall Python from <https://www.python.org/downloads/macos/>.

If `email-scraper` does not open the interactive tool, reinstall it from inside the project folder:

Windows 11:

```bat
py -m pip install --force-reinstall .
```

macOS:

```bash
python3 -m pip install --force-reinstall .
```

## Basic Usage

Start the scraper:

Windows:

```bat
email-scraper
```

macOS:

```bash
email-scraper
```

The tool will show a colored block-letter title screen and ask you questions:

```text
BARBIE
BITCH
CULT

Barbie Bitch Cult - Email Scraper

Website URL or domain:
CSV output file [emails.csv]:
Maximum pages to crawl [100]:
Maximum bytes to read per page [2000000]:
Delay between requests in seconds [0.2]:
HTTP timeout in seconds [10.0]:
Include subdomains? [y/N]:
Honor robots.txt? [Y/n]:
User-Agent [email-scraper/0.1 (+https://example.invalid/email-scraper)]:
Show progress while running? [y/N]:
```

Press Enter to use the value shown in brackets.

If your computer says `email-scraper` is not recognized, run the interactive tool through Python instead.

Windows:

```bat
py -m email_scraper
```

macOS:

```bash
python3 -m email_scraper
```

If nothing appears when you run `email-scraper`, reinstall the tool from this project folder:

Windows:

```bat
py -m pip install --force-reinstall .
email-scraper
```

macOS:

```bash
python3 -m pip install --force-reinstall .
email-scraper
```

You can also run the current project copy directly without reinstalling:

Windows:

```bat
py -m email_scraper
```

macOS:

```bash
python3 -m email_scraper
```

## Advanced One-Line Usage

If you do not want to answer questions interactively, you can still provide everything in one command:

```bash
email-scraper https://example.com --output emails.csv
```

Common one-line options:

```bash
email-scraper example.com \
  --output emails.csv \
  --max-pages 250 \
  --delay 0.25 \
  --include-subdomains \
  --verbose
```

Use a custom User-Agent when a site blocks generic crawlers:

```bash
email-scraper https://example.com \
  --output emails.csv \
  --user-agent "Mozilla/5.0 (compatible; EmailScraper/0.1; +https://example.com/contact)"
```

The scraper honors `robots.txt` by default. To skip `robots.txt` checks, use `--no-robots`.

Only use this when you have permission to crawl the site:

```bash
email-scraper https://example.com --no-robots --output emails.csv
```

The older option name also works:

```bash
email-scraper https://example.com --ignore-robots --output emails.csv
```

## See Progress While It Runs

Add `--verbose` to show each page as it is checked:

```bash
email-scraper https://example.com --output emails.csv --verbose
```

The output will look similar to this:

```text
robots: loaded https://example.com/robots.txt
fetch: https://example.com/
fetch: https://example.com/contact/
done: crawled=12 findings=4 output=emails.csv
```

## Open the Results

The results are saved as a CSV file. You can open the file with Microsoft Excel, Apple Numbers, Google Sheets, or any text editor.

## CSV Columns

- `email`: normalized lowercase email address
- `source_url`: page where the address was found
- `discovery_type`: `mailto`, `link`, or `text`

## Notes

This tool extracts email addresses visible in HTML pages. It does not execute JavaScript, submit forms, bypass access controls, or crawl outside the selected domain scope.
