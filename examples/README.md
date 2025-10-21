# Examples

This directory contains example files and templates for Tacview Log Analyzer.

## Custom Template Example

**File:** `custom_template_example.html`

This is a fully functional example of a custom HTML template that demonstrates how to:

- **Customize the visual appearance** with dark theme and terminal-style aesthetics
- **Change colors and fonts** throughout the interface
- **Add custom styling** while preserving all functionality
- **Use proper Jinja2 template syntax** for data binding
- **Implement responsive design** for different screen sizes

### How to Use

1. **Download** this example template
2. **Copy** it to the same directory as your `TacviewLogAnalyzer.exe`
3. **Rename** it to `index.html`
4. **Customize** the CSS styling as desired
5. **Run** the analyzer with `--web` option

### Template Features

- **Dark gradient background** (purple to blue)
- **Green terminal-style text** with glowing cyan headers
- **Custom notice banner** to show when template is active
- **Emoji icons** throughout the interface
- **Hover effects** on interactive elements
- **Fully responsive** design for mobile and desktop
- **All original functionality** preserved (sorting, filtering, etc.)

### Customization Tips

- **Colors:** Modify the CSS color values to match your preferred theme
- **Fonts:** Change the `font-family` properties to use different fonts
- **Layout:** Adjust the HTML structure to reorganize content
- **Icons:** Replace or remove emoji icons as desired
- **Animations:** Add or remove CSS animations and transitions

### Template Variables

The template receives these Jinja2 variables from the application:

#### Top-Level Variables

- `vm` - Complete view model with all pilot and mission data (see structure below)
- `xml` - String path to the currently loaded XML file (e.g., `"C:\logs\mission.xml"`)
- `error` - Error message string if loading failed, `None` if successful
- `hasData` - Boolean indicating if data was successfully loaded (`True`/`False`)

#### Complete Data Structure (`vm` object)

```python
vm = {
    # List of all pilots with their complete combat data
    "pilots": [
        {
            "pilot": "PilotCallsign",                    # Pilot callsign/name

            # Overall statistics totals
            "totals": {
                "shots": 12,                            # Total shots fired
                "hits": 8,                              # Total successful hits
                "kills": 5,                             # Total kills
                "misses": 4                             # Total misses
            },

            # Friendly fire statistics
            "totalsFriendly": {
                "shots": 1,                             # Friendly fire shots
                "hits": 0,                              # Friendly fire hits
                "kills": 0                              # Friendly fire kills
            },

            # Air-to-Air domain statistics
            "totalsAA": {
                "shots": 8,                             # A-A shots fired
                "hits": 6,                              # A-A hits
                "kills": 4                              # A-A kills
            },

            # Air-to-Ground domain statistics
            "totalsAG": {
                "shots": 4,                             # A-G shots fired
                "hits": 2,                              # A-G hits
                "kills": 1                              # A-G kills
            },

            # Flight information
            "flightTime": "01:23:45",                   # Formatted flight time (HH:MM:SS)
            "flightTimeSec": 5025.0,                    # Flight time in seconds
            "flightEnd": "Landed",                      # How flight ended: "Landed", "Shot down", "Ejected", etc.

            # Weapon breakdown per pilot
            "byWeapon": [
                {
                    "weapon": "AIM-120C AMRAAM",        # Weapon name
                    "shots": 6,                         # Shots with this weapon
                    "hits": 4,                          # Hits with this weapon
                    "kills": 3,                         # Kills with this weapon
                    "misses": 2                         # Misses with this weapon
                },
                # ... more weapons
            ],

            # Individual engagement chains (successful shots)
            "chains": [
                {
                    "shotT": 1234.5,                    # Shot time (seconds from mission start)
                    "shotStr": "20:34",                 # Shot time formatted (MM:SS)
                    "weapon": "AIM-120C AMRAAM",        # Weapon name
                    "weaponId": 12345,                  # Unique weapon ID
                    "targetName": "MiG-29A Fulcrum",    # Target name if hit/killed
                    "hitT": 1240.2,                     # Hit time (seconds) or None
                    "hitStr": "20:40",                  # Hit time formatted or ""
                    "killT": 1240.2,                    # Kill time (seconds) or None
                    "killStr": "20:40",                 # Kill time formatted or ""
                    "method": "deterministic",          # Linking method: "deterministic" or "heuristic"
                    "shooterMismatch": False,           # Boolean: shooter data inconsistent
                    "friendly": False,                  # Boolean: any friendly fire in this chain
                    "friendlyHit": False,               # Boolean: friendly fire hit
                    "friendlyKill": False,              # Boolean: friendly fire kill
                    "domain": "AA",                     # Weapon domain: "AA" (Air-to-Air) or "AG" (Air-to-Ground)
                    "extraKills": 1,                    # Number of additional splash kills
                    "extraKillNames": ["Target2"],      # Names of additional targets killed
                    "intercepted": False,               # Boolean: weapon was intercepted before reaching target
                    "interceptorName": None             # Name of intercepting weapon/system if intercepted
                },
                # ... more engagement chains
            ],

            # Miss events (shots that didn't hit anything)
            "misses": [
                {
                    "shotT": 1450.0,                    # Shot time (seconds from mission start)
                    "shotStr": "24:10",                 # Shot time formatted (MM:SS)
                    "weapon": "AIM-9X Sidewinder",      # Weapon name
                    "weaponId": 54321,                  # Unique weapon ID
                    "domain": "AA"                      # Weapon domain: "AA" or "AG"
                },
                # ... more misses
            ]
        },
        # ... more pilots
    ],

    # Mission overview statistics
    "overview": {
        "humanPilots": 24,                              # Total number of human pilots
        "landedPilots": 20,                             # Number who landed safely
        "ejectedOrShotPilots": 4,                       # Number ejected or shot down

        # Overall weapon usage statistics across all pilots
        "shotsByWeapon": [
            {
                "weapon": "AIM-120C AMRAAM",            # Weapon name
                "shots": 45,                            # Total shots fired with this weapon
                "hits": 32,                             # Total hits with this weapon
                "kills": 28                             # Total kills with this weapon
            },
            # ... more weapons, sorted by shot count descending
        ]
    }
}
```

#### Usage Examples in Templates

```jinja2
<!-- Display pilot list with basic stats -->
{% for pilot in vm.pilots %}
<div class="pilot">
    <h3>{{ pilot.pilot }}</h3>
    <p>{{ pilot.totals.shots }} shots, {{ pilot.totals.hits }} hits, {{ pilot.totals.kills }} kills</p>
    <p>Flight time: {{ pilot.flightTime }} ({{ pilot.flightEnd }})</p>
</div>
{% endfor %}

<!-- Show weapon breakdown for a pilot -->
{% for weapon in pilot.byWeapon %}
<tr>
    <td>{{ weapon.weapon }}</td>
    <td>{{ weapon.shots }}</td>
    <td>{{ weapon.hits }}</td>
    <td>{{ weapon.kills }}</td>
</tr>
{% endfor %}

<!-- Display engagement chains with details -->
{% for chain in pilot.chains %}
<div class="engagement {{ 'friendly' if chain.friendly else '' }} {{ 'intercepted' if chain.intercepted else '' }}">
    <span class="time">{{ chain.shotStr }}</span>
    <span class="weapon">{{ chain.weapon }}</span>
    {% if chain.targetName %}
        <span class="target">→ {{ chain.targetName }}</span>
    {% endif %}
    {% if chain.intercepted %}
        <span class="intercepted">Intercepted by {{ chain.interceptorName }}</span>
    {% endif %}
</div>
{% endfor %}

<!-- Mission overview stats -->
<div class="overview">
    <p>{{ vm.overview.humanPilots }} pilots participated</p>
    <p>{{ vm.overview.landedPilots }} landed safely, {{ vm.overview.ejectedOrShotPilots }} were lost</p>
</div>

<!-- Handle no data case -->
{% if not hasData %}
    {% if error %}
        <div class="error">Error: {{ error }}</div>
    {% else %}
        <div class="no-data">No mission data loaded. Please select an XML file.</div>
    {% endif %}
{% endif %}
```

#### Domain Classification

- **AA (Air-to-Air)**: Weapons targeting aircraft or helicopters (AIM-120, AIM-9, etc.)
- **AG (Air-to-Ground)**: Weapons targeting ground/naval targets (AGM-65, GBU-54, etc.)

#### Special Features

- **Interception Detection**: When A-G weapons are shot down by enemy missiles before reaching target
- **Friendly Fire Tracking**: Automatic detection of same-coalition engagements
- **Extra Kills**: Multi-target weapons (splash damage) tracked separately
- **Flight Outcomes**: Detailed tracking of how each pilot's mission ended

### Support

For questions about custom templates, please refer to the main README.md or open an issue on GitHub.
