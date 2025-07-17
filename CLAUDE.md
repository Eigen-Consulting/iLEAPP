You're a coding agent that will help fill out artifact scripts for iLEAPP. Right now, iLEAPP doesn't support many apps, and you're going to help it support more. I have supplied you the iLEAPP repo which you live in (it's already on its own feature branch). You're going to be given a full file‑system or backup extraction to study. The extraction is in the folder `extraction`. You're going to look through this and make a checklist of all the apps that are not supported by iLEAPP. You'll save this checklist to a file called `apps_not_supported.txt`. And then using this guide, you'll design and implement the artifact scripts for each of the apps that are not supported. You'll update the checklist as you go along, and after you finish each artifact script, you'll test your changes. If your changes are good, you'll commit them to the feature branch. If your changes are bad, you'll fix them and repeat the process till it's working. You'll repeat this process until you have a complete list of apps that are not supported by iLEAPP.

Use the Task tool whenever you have a long running research task that feels like a large divergence.

<ileapp-artifact-guide>
Below is a soup‑to‑nuts playbook for adding support for a brand‑new iOS application to **iLEAPP** when you already have a full file‑system or backup extraction to study. Follow each numbered phase in order; treat bold bullets as individual tasks you should literally check off. (The steps assume you are familiar with basic Python and Git workflows.)

---

## 1  Set up your lab

## You are already living in an iLEAPP environment. You have a full file‑system or backup extraction to study. The extraction is in the folder `extraction`. You'll need to set up your environment by running `source .venv/bin/activate`.

## 2  Map the new app’s data structures

1. **Locate the container** in the extraction (typical pattern: `AppDomain‑<bundleID>`) and note sub‑paths (e.g., `Documents`, `Library/Preferences`, `Library/Application Support`).
2. **Inventory file types** (SQLite, Plist, JSON, binary blobs, protobuf, enzlib, etc.). Tools like DB Browser for SQLite, Xcode’s `plutil`, or `strings` can speed reconnaissance. Real‑world examples of dissecting Photos.sqlite and Camera plists illustrate the level of detail you need. ([The Forensic Scooter][4], [blog.d204n6.com][5])
3. **Document timestamps, units & time‑zones** (e.g., Cocoa epoch vs UNIX, GMT vs local). Keep notes—these become the header comments and help strings in your module.
4. **Draft SQL queries or parsing routines** that return _forensically meaningful_ rows—think “what an examiner would search for.”

---

## 3  Design your iLEAPP artifact(s)

- **Decide scope**: will you produce one monolithic artifact or multiple focused ones (messages, settings, cache, etc.)?
- **Fill in the `__artifacts_v2__` dictionary** at the top of a new file—this metadata drives auto‑loading and the sidebar icon in the HTML report. Required keys include `name`, `description`, `paths`, `category`, `output_types`, `author`, `version`, `date`, and a unique **function key that matches your processing function name**. ([GitHub][2], [GitHub][6])
- Because scripts are now _self‑contained_, you do **not** edit any central list—just add your `.py` file under `scripts/artifacts`. ([DFIRScience][1])

---

## 4  Implement the parser

```python
from scripts.ilapfuncs import artifact_processor, convert_utc_human_readable
from scripts.artifact_report import ArtifactHtmlReport
import sqlite3, json, os

__artifacts_v2__ = {
    "mycoolapp_chat": {
        "name":        "MyCoolApp – Chats",
        "description": "User conversations, participants, timestamps",
        "author":      "@yourhandle",
        "version":     "0.1",
        "date":        "2025-07-17",
        "category":    "Messaging",
        "paths":       ('*/MyCoolApp*/Chat.db',),
        "output_types":"all",
        "artifact_icon":"message-square"
    }
}

@artifact_processor
def mycoolapp_chat(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data = []
    for file in files_found:
        conn = sqlite3.connect(file)
        c = conn.cursor()
        c.execute("""SELECT message_id,
                            datetime(sent_ts+?, 'unixepoch') as sent,
                            sender, text
                     FROM   messages""", (timezone_offset,))
        for row in c:
            data.append(row + (file,))
        conn.close()

    headers = ('ID','Sent (local)','Sender','Body','Source File')
    return headers, data, file
```

- **Decorator & arguments** – `@artifact_processor` ensures iLEAPP supplies `files_found`, `report_folder`, `seeker`, and `wrap_text`. ([GitHub][6])
- **Outputs** – return a header tuple and list of tuples; helper functions in `artifact_report` and `ilapfuncs` generate HTML, TSV, LAVA, timeline and KML for you. ([GitHub][2])
- **Path globbing** – wildcard patterns in `paths` let the FileSeeker find files inside tar/zip or directory extractions. ([GitHub][2])

---

## 5  Local testing & linting

**IMPORTANT**: iLEAPP doesn't have a `-f` flag to run individual artifacts. Instead, use these proven methods:

### Method 1: Profile-based testing (Recommended)

1. **Create a test profile** for your artifact:

   ```bash
   # Hand-craft a profile file with your artifact name
   echo '{"leapp":"ileapp","format_version":1,"plugins":["yourArtifactName"]}' > test_artifact.ilprofile
   ```

2. **Run iLEAPP with the profile**:

   ```bash
   mkdir -p test_output
   python3 ileapp.py -t fs -i /path/extraction -o test_output -m test_artifact.ilprofile
   ```

3. **Verify the output**:
   - Check the HTML report at `test_output/iLEAPP_Reports_*/index.html`
   - Look for your artifact category in the sidebar
   - Verify column order, timestamp conversion, and source file links
   - Check the log output for any errors or warnings

### Method 2: Single-file testing

If your artifact processes a single file type (e.g., a specific SQLite database):

```bash
python3 ileapp.py -t file -i /path/to/specific/file.db -o test_output
```

### Method 3: GUI testing

- Use **iLEAPP-GUI** and uncheck all artifacts except yours
- Set input/output paths and click **Process**

### Testing best practices:

1. **Check artifact loading**: Verify your artifact appears in the log output
2. **Validate file discovery**: Check that your glob patterns find the expected files
3. **Test empty containers**: Ensure graceful handling when no data is found
4. **Verify data parsing**: Check that timestamps, data types, and content are correct
5. **Review HTML output**: Ensure proper formatting and forensic relevance

### Example testing workflow:

```bash
# Create profile
echo '{"leapp":"ileapp","format_version":1,"plugins":["myNewArtifact"]}' > test_my_artifact.ilprofile

# Test the artifact
mkdir -p test_output
python3 ileapp.py -t fs -i extraction -o test_output -m test_my_artifact.ilprofile

# Check results
open test_output/iLEAPP_Reports_*/index.html
```

### Debugging tips:

- Check the console output for your artifact's log messages
- Look for "Processing [YourApp] file:" messages to verify file discovery
- Verify the artifact completed without errors
- Check the "Files" tab in the HTML report to see which files were found

4. **PEP‑8 / Black / flake8**: keep code style consistent; the maintainers run automated linters.
5. **Edge‑case regression**: test iOS 14‑17 extractions if available; watch for NULLs and schema drift.

Autopsy can also load iLEAPP output, giving you a quick GUI validation. ([sleuthkit.org][7])

---

## 6  Automated tests & CI

- Add a minimal sample database or plist (scrubbed) under `tests/test_data`.
- Write `pytest` assertions (e.g., row counts, first/last timestamp) and update any GitHub Actions workflow if needed. Continuous integration keeps future refactors from breaking your artifact. See the existing PRs that add artifacts for patterns. ([GitHub][8], [YouTube][9])

---

## 7  Documentation & changelog

- At the top of your module, include a docstring with usage notes and schema version caveats.
- Update `README.md` bullet list _and/or_ the Wiki if the project uses it. ([GitHub][2])
- If your parser requires a new third‑party library, add it to `requirements.txt`. ([GitHub][2])

---

## 8  Contribute upstream

1. **Commit** with signed‑off message (`git commit -s -m "Add MyCoolApp chat artifact"`).
2. **Push & open a pull request**; template will ask for:

   - Brief description & screenshots of the HTML report
   - Sample data or hashed test fixture
   - Confirmation you ran `black .` and `pytest`

3. Respond to code‑review nits promptly; maintainers are active and friendly. ([GitHub][2])

---

## 9  After merge

- Monitor issues for bug reports; be ready to patch schema changes when Apple releases new iOS versions.
- Consider porting the parser to **xLEAPP** (the merged multi‑platform rewrite) or to **ALEAPP/WLEAPP** if the same vendor ships Android/Windows counterparts. ([GitHub][8])

---

### Quick reference checklist

| Phase    | Must‑do items                                     |
| -------- | ------------------------------------------------- |
| Env prep | Fork repo, install deps, verify run               |
| Recon    | Find files, reverse engineer, document units      |
| Design   | Fill `__artifacts_v2__`, choose output types      |
| Code     | Parse data, use helper funcs, return headers+rows |
| Test     | CLI run, view HTML, add pytest                    |
| Docs     | Module docstring, README bullet                   |
| PR       | Sign‑off, include sample, address review          |

Follow these steps and your new app will appear in iLEAPP’s GUI sidebar, complete with HTML, TSV, timeline and LAVA outputs—ready for every other investigator in the community. Happy parsing!

</ileapp-artifact-guide>
