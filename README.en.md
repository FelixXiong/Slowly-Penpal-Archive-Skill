# Slowly-Penpal-Archive-Skill

[简体中文](README.md) | [English](README.en.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [العربية](README.ar.md)

## Why I made this
> Preserve every pen-pal connection with care.

Some exchanges gradually come to an end. Some pen pals are people we need to say goodbye to.

But before clearing out our pen-pal list, we still want to keep the letters we put so much thought into writing and receiving.

Once you have downloaded all those PDFs, how do you organize them and revisit each letter and each pen-pal connection?

Slowly users know that without Plus, we have only 100 pen-pal slots. If you have subscribed to Slowly Plus and decide not to renew when it expires, you may need to make room in your pen-pal list.

That is why I made this skill.

This skill:
1. Does not download letters from the website for you.
2. Organizes your saved letters into a searchable, browsable local archive, giving every exchange a place to stay.

Currently, this tool is intended for archiving Slowly letters. Other apps that can export letters as PDFs have not been tested. Feel free to try them and share your feedback in Issues.

## Before you start
Open the Slowly web app and save your pen pals’ letters as PDFs yourself. Create one folder for each pen pal, for example:

```text
Letters/
└── A pen pal/
    ├── Slowly.pdf
    ├── Slowly2.pdf
    ├── Stamps/
    │   ├── Stamp1.png
    │   └── Stamp2.png
    └── Profile/
        └── Avatar.png
```

Note: You will need to verify compatibility with your manually exported files.

## Workflow
Save letters as PDFs → Create a folder for each pen pal (keep letters from the same person together) → Optionally ask AI to standardize filenames → Have the skill generate the archive → Open it and read.

## Getting started
1. Download this repository (green **Code** button → *Download ZIP*, or `git clone`) and unpack it. You get a folder that contains `SKILL.md` and `scripts/` (from a ZIP it is named `Slowly-Penpal-Archive-Skill-main`). Move that **whole folder** into the skills directory your tool uses and rename it to `slowly-penpal-archive`, or use the tool's local skill import feature.
   Do not copy `SKILL.md` alone: without `scripts/` next to it the skill cannot run `scripts/pdf_index.py`.
2. In an office tool that supports Skills (WorkBuddy, Qianwen Office / 千问办公, or Doubao Work / 豆包工作), or an IDE, say:

> Use slowly-penpal-archive to organize the PDFs in (the path where I saved my letters) into an offline archive. Preserve the original files and open the archive entry point when it is ready.

To add more letters:

> Use slowly-penpal-archive. My source directory is (the path where I saved my letters). Append the new letters to the existing archive.

The first run requires a host environment capable of running Python. If `pypdf` is missing, the AI will handle it as permitted by that environment.

Fetching dependencies for the first time may require an internet connection. Archiving and reading do not access Slowly.

After generation, open the local `index.html` to read. You do not need to keep the AI or a local service running afterward.

## Run it without an AI host
Two commands are enough:

```bash
python3 -m pip install -r requirements.txt

python3 scripts/pdf_index.py --root '<letters folder>' --out '<output folder>'
open '<output folder>/index.html'    # Windows: start / Linux: xdg-open
```

- Without `--root` it reads `~/Desktop/笔友库`. If that folder is missing the script tells you where to point it instead of guessing.
- Without `--out` results go to `~/Desktop/Slowly离线档案`. Keep one output folder per letters folder — the next run only adds what changed.
- Other flags: `--pal '<pen pal>'`, `--full`, `--pdf-only`, `--verify-data`, `--sql '<query>'`.
- Verified on Python 3.9 / 3.12 / 3.14 with identical data. Self-checks: `python3 -m unittest discover -s scripts -t scripts` (32 tests) and `bash scripts/audit_offline.sh`.

## Generated files

| File | Purpose |
| --- | --- |
| `index.html` | Offline archive you can open directly |
| `slowly_pdf.db` | Letter database |
| `letters.jsonl` | Structured letter records |
| `build.json` | Import statistics, failure records, and the number of items awaiting confirmation |
| `media.json` | Index of local images, text, and their associations |

## Preview
A preview of the pen-pal archive:

<img width="1440" height="1000" alt="Letter list" src="https://github.com/user-attachments/assets/a36b1725-bb47-465f-8345-772511a49c02" />
<img width="1920" height="1080" alt="Pen-pal archive preview 2" src="https://github.com/user-attachments/assets/c26fa704-91a7-432c-af86-03447fffb644" />
<img width="1920" height="1080" alt="Pen-pal archive preview 3" src="https://github.com/user-attachments/assets/195632ad-4681-450e-9e95-f1b345cd3767" />

## Data privacy and security
The skill itself does not access the internet, automate the Slowly website, or read your login session. You do not need to sign in to Slowly. It only reads letter PDFs you have already saved, extracts their text with `pypdf`, and generates a searchable SQLite database and a self-contained, single-file web archive with embedded data that you can open by double-clicking.

Dependency: `pypdf`. Installing it for the first time requires an internet connection to download the package.

You do not have to take this on faith: `bash scripts/audit_offline.sh` scans the scripts, the page template and the generated archive, and fails on any network stack, external reference or browser-automation call. The generated `index.html` carries zero external `link`/`script`/`img` references.

One caution: `index.html` embeds your letter bodies and links every letter to its absolute path on your disk. Keep the generated page, `*.db`, `letters.jsonl` and `media.json` to yourself — they are git-ignored on purpose.

## FAQ
**Q: What if I change the directory where my letters are stored?**

A: Return to your IDE or WorkBuddy, tell the AI the new path, and generate the archive again.

## Support
<img width="1920" height="1080" alt="Support the project" src="https://github.com/user-attachments/assets/b84194e5-e9d3-4149-81ae-f9d664d9f813" />
