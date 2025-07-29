# Custom Artifacts for iLEAPP

This directory contains example custom artifacts that demonstrate how to extend iLEAPP's functionality without modifying the core codebase.

## Quick Start

1. Copy `example_custom_artifact.py` as a template
2. Modify it for your specific use case
3. Place your custom artifacts in a directory
4. Run iLEAPP with the `--extra-artifacts` flag:

```bash
python ileapp.py -t fs -i /path/to/extraction -o /output/path --extra-artifacts /path/to/your/custom/artifacts
```

## Important Notes

### File Structure
- Each artifact must be a separate `.py` file
- The file must contain a `__artifacts_v2__` dictionary at the top
- The artifact function must be decorated with `@artifact_processor`
- The function name must match the key in `__artifacts_v2__`

### Import Requirements
Custom artifacts run from outside the main iLEAPP directory, so you must add the parent directory to sys.path:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Built-in Priority
If your custom artifact has the same ID as a built-in artifact, the built-in will take priority and your custom artifact will be skipped with a warning message.

### Categories
Use standard categories when possible for better organization:
- Accounts
- App Usage  
- Chats
- Communications
- Device Info
- Health & Fitness
- Locations
- Media
- Network
- etc.

### Testing Your Artifact

1. Test with a small extraction first:
```bash
python ileapp.py -t fs -i test_extraction -o test_output --extra-artifacts ./my_artifacts
```

2. Check the console output for any errors
3. Verify the HTML report contains your artifact data
4. Use `--artifact_paths` to verify your path patterns are included

### Common Patterns

#### Processing SQLite Databases
```python
import sqlite3

conn = sqlite3.connect(file_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM table_name")
for row in cursor.fetchall():
    # Process row
conn.close()
```

#### Processing Plist Files
```python
import plistlib

with open(file_path, 'rb') as f:
    plist = plistlib.load(f)
    # Process plist data
```

#### Timestamp Conversion
```python
from scripts.ilapfuncs import convert_ts_human_to_timezone_offset

# Convert timestamp to user's timezone
timestamp = convert_ts_human_to_timezone_offset(timestamp, timezone_offset)
```

## Troubleshooting

### Import Errors
- Ensure you've added the parent directory to sys.path
- Check that all required iLEAPP modules are imported correctly

### Artifact Not Loading
- Verify the function name matches the key in `__artifacts_v2__`
- Check for Python syntax errors
- Ensure the file has a `.py` extension

### No Data in Report
- Verify your path patterns match actual files
- Check SQL queries or parsing logic
- Add debug prints to trace execution

## Contributing

If you create useful custom artifacts, consider contributing them to the main iLEAPP project by submitting a pull request!