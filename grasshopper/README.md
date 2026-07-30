# Grasshopper Engineering Layer

`ArchSim Script.gh` is the Grasshopper definition that runs the engineering layer of ArchSim.

It contains the parametric massing logic, the structural analysis (Karamba3D), and the environmental simulation (Ladybug Tools) that ground every agent's claim in real numerical data — beam utilisation, deflection, lateral drift, solar radiation, daylight hours, energy load, and carbon emissions.

## Requirements

- **Rhino 8+** (the definition uses Python 3 script components, which require Rhino 8)
- **Grasshopper** (bundled with Rhino)
- **[Karamba3D](https://karamba3d.com/)** — for structural analysis
- **[Ladybug Tools](https://www.ladybug.tools/)** — for environmental simulation

## Folder layout — keep these files together

`massing_helpers.py` and `structure_helpers.py` **must stay in the same folder as `ArchSim Script.gh`** — the massing and structure components import them from the folder the `.gh` file lives in. If you move or copy the definition, move the two helper files with it.

To run the environmental simulation, drop an `.epw` weather file into [`Ladybug_epw/`](Ladybug_epw/) and point the *File Path* parameter feeding **LB Import EPW** at it (see the README in that folder for where to download one).

## First open: red components are normal

When you open the definition before the app has ever run, `gh-massing` and `gh_structure` will show errors such as *"floors must be >= 1"* or *"No floor_curves provided"*. This is expected: the definition reads its design parameters from `snapshots/.gh-inputs.json`, which does not exist until the browser app posts one. Start `serve.py`, open the app, and trigger a round — the components recover on the next solve. No fixing required.

## How it connects to the app

```
Browser app  ←──── snapshot files ─────→  serve.py  ←──── parameters ─────→  Grasshopper
                                                                              (this file)
```

The bridge protocol works as follows:

1. The browser app posts the current parameter set to `serve.py`
2. `serve.py` writes the payload atomically to `snapshots/.gh-inputs.json`
3. This Grasshopper definition reads `snapshots/.gh-inputs.json` on its next solve
4. Karamba and Ladybug compute structural and environmental performance
5. The results are written back to `snapshots/latest/params.json`
6. The browser app polls that file, recognises the round-token, and resumes

## Running it

1. Start `serve.py` from the project root: `python serve.py`
2. Open `ArchSim Script.gh` in Rhino + Grasshopper
3. Open `http://localhost:3000` in your browser
4. Use the app — every time you change parameters and trigger a round, this definition recomputes
