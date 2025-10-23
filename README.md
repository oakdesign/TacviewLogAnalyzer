# Tacview Log Analyzer

A comprehensive tool to parse Tacview XML logs and generate detailed combat statistics and analysis. Features advanced weapon tracking, pilot performance metrics, air-to-air kill analysis, and interception detection.

## Features

- **Comprehensive Statistics**: Pilot performance with shots, hits, kills, and flight times
- **Weapon Analysis**: Detailed breakdown by weapon type and effectiveness
- **Air-to-Air Combat**: Specialized A-A kill tracking grouped by target aircraft type  
- **Interception Detection**: Identifies when A-G weapons are shot down before reaching targets
- **Web Interface**: Interactive browser-based analysis dashboard
- **Standalone Executable**: No Python installation required for end users
- **CLI Tools**: Command-line interface for automated analysis
- **Multiple Output Formats**: Summary reports, detailed chains, and web UI

## End-User Guide (Standalone Executable)

### Download and Setup

1. **Download** the latest `TacviewLogAnalyzer.exe` from the [GitHub Releases](https://github.com/oakdesign/TacviewLogAnalyzer/releases) page
2. **No installation required** - the .exe is completely standalone
3. **Place the executable** in any folder of your choice

### Basic Usage

**Quick Start - Double Click**: Simply double-click `TacviewLogAnalyzer.exe` to start the web interface automatically! No command line required.

**From Tacview**: Load your .acmi file in Tacview, go to File → Export Flight Log, and export as .xml format.

**Command Line Options** (for advanced users):

```cmd
# Generate comprehensive summary report
TacviewLogAnalyzer.exe --summary your_tacview_log.xml

# Launch interactive web interface (opens in browser)
TacviewLogAnalyzer.exe --web your_tacview_log.xml

# View detailed engagement chains
TacviewLogAnalyzer.exe --chains-combined your_tacview_log.xml

# Show all available options
TacviewLogAnalyzer.exe --help
```

**Double-Click Mode**: When you double-click the executable:
- 🚀 Automatically starts web interface 
- 🌐 Opens your browser to the analysis page
- 📁 Looks for XML files in the same folder
- 🔧 Uses smart port detection (8000, 8090, 9000, etc.)

### Custom Web Interface Templates

**Advanced Feature**: You can customize the web interface appearance by providing your own HTML template:

1. **Create custom template**: Copy the original `index.html` from inside the executable or create your own
2. **Place alongside executable**: Save your custom template as `index.html` in the same folder as `TacviewLogAnalyzer.exe`
3. **Launch normally**: The executable will automatically use your custom template instead of the built-in one

```cmd
# Example directory structure for custom template:
MyAnalysisFolder/
├── TacviewLogAnalyzer.exe
├── index.html          <- Your custom template
└── mission_log.xml

# Run with custom template (automatically detected)
TacviewLogAnalyzer.exe --web mission_log.xml
```

**Template Requirements:**
- Must be valid HTML with Jinja2 template syntax
- Use the same template variables as the original (`vm`, `xml`, `error`, `hasData`)
- Include JavaScript for sorting functionality if desired
- Can completely customize styling, colors, fonts, and layout

**Example Template:**
Download the [example custom template](examples/custom_template_example.html) from this repository to see:
- Dark theme with terminal-style aesthetics
- Custom colors and styling
- Comprehensive comments explaining customization options
- All functionality preserved from the original template

### Understanding the Output

**Summary Report includes:**
- **Pilot Statistics**: Individual pilot performance with shots/hits/kills and flight time
- **Weapon Breakdown**: Shots fired per weapon type for each pilot
- **Flight Outcomes**: How each pilot's flight ended (Landed, Shot down, Ejected, etc.)
- **A-A Kills by Target**: Air-to-air kills grouped by target aircraft type (e.g., "MiG-29S Fulcrum-C 12 kills")

**Web Interface provides:**
- Interactive browsing of all engagement data
- Sortable tables and detailed event information
- Visual timeline of combat events
- Export capabilities for further analysis

### Example Usage

```cmd
# Double-click the executable (recommended for most users)
# - No command needed! Just double-click TacviewLogAnalyzer.exe

# OR use command line for specific analysis
TacviewLogAnalyzer.exe --summary "2025-10-22_Mission.xml"

# OR launch web interface with a specific file
TacviewLogAnalyzer.exe --web "2025-10-22_Mission.xml"
```

**Double-Click Experience:**
1. 🖱️ Double-click `TacviewLogAnalyzer.exe`
2. 📝 See friendly startup message with instructions
3. 🌐 Browser automatically opens to the analysis interface
4. 📂 Browse and select XML files from the web interface
5. ❌ Press Ctrl+C in the console window to exit

The web interface will automatically open in your default browser at `http://localhost:8000`.

### System Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **No additional software required** - the executable is completely self-contained
- **Memory**: Sufficient RAM to load XML files (typically 100MB+ for large mission logs)
- **Disk Space**: Minimal (executable is ~15-20MB)

### Troubleshooting

**If double-click doesn't work:**
- Ensure you're using a 64-bit Windows system
- If a console window opens but nothing happens, check for error messages
- Try running from Command Prompt to see detailed error output

**If the executable doesn't run:**
- Ensure you're using a 64-bit Windows system  
- Try running from Command Prompt to see any error messages
- Check that your antivirus isn't blocking the executable

**If the web interface doesn't open automatically:**
- The console will show the URL (usually `http://127.0.0.1:8000`)
- Manually copy and paste this URL into your browser
- If port 8000 is in use, the tool will automatically try alternatives (8090, 9000, etc.)

**If the web interface doesn't open:**
- Manually navigate to `http://localhost:8000` in your browser
- Ensure no other application is using port 8000
- Check Windows Firewall settings if needed

**For large XML files:**
- The tool can handle files up to several hundred MB
- Processing time scales with file size and number of events
- Consider using `--summary` mode for faster analysis of very large files

**For custom templates:**
- Ensure your custom `index.html` is in the same folder as the .exe
- Check the console output for template loading messages
- Refer to the example template in the GitHub repository for proper structure

**For custom templates:**
- Ensure your `index.html` is in the same directory as the executable
- Check browser console for JavaScript errors if sorting doesn't work
- Use the [example template](examples/custom_template_example.html) as a starting point
- Template must use valid HTML and Jinja2 syntax

**Custom template issues:**
- If your custom `index.html` causes errors, remove it to revert to the built-in template
- Ensure your template uses proper Jinja2 syntax and includes required template variables
- Test template changes incrementally to identify syntax errors

## Developer Guide

### Development Setup (Windows PowerShell)

```powershell
# 1) Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install development dependencies
pip install -U pip
pip install -e .[dev]

# 3) Run tests
pytest -q

# 4) Run from source
python -m tacview_log_analyzer --help
python -m tacview_log_analyzer --summary your_tacview_log.xml

# 5) Build standalone executable
pyinstaller TacviewLogAnalyzer.spec
# Output: dist/TacviewLogAnalyzer.exe
```

### Building Releases

The project uses GitHub Actions for automated building:
- **Push to master**: Automatically builds and creates release artifacts
- **Manual releases**: Download from GitHub Releases page
- **Local builds**: Use `pyinstaller TacviewLogAnalyzer.spec` for development builds

## Project Structure

- `src/tacview_log_analyzer/` – Main package
  - `cli.py` – Command-line interface and summary reports
  - `parser.py` – Tacview XML parsing logic
  - `linking.py` – Event linking and chain analysis
  - `stats.py` – Statistics computation and rendering
  - `viewmodel.py` – Data transformation for web UI
  - `webapp.py` – FastAPI web application
  - `webui/` – HTML templates and web assets
- `tests/` – Unit tests and test data
- `.github/workflows/` – GitHub Actions CI/CD
- `TacviewLogAnalyzer.spec` – PyInstaller build configuration

## Key Features Explained

### Air-to-Air Kill Analysis
Groups A-A kills by target aircraft type using sophisticated weapon classification:
- Automatically detects A-A vs A-G weapons based on target type and weapon characteristics
- Provides cumulative counts (e.g., "MiG-29S Fulcrum-C 12 kills")
- Excludes ground targets and non-combat events

### Interception Detection
Identifies when air-to-ground weapons are intercepted before reaching their targets:
- Tracks AGM, GBU, JDAM, and other A-G weapons
- Detects when they are shot down by enemy missiles
- Classifies as "intercepted" rather than miss or hit

### Web Interface
Provides comprehensive analysis dashboard:
- Real-time event browsing and filtering
- Interactive engagement chains
- Sortable pilot and weapon statistics
- Export capabilities for detailed analysis
