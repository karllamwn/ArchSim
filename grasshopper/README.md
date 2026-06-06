# Grasshopper Engineering Layer

`ArchSim Script.gh` is the Grasshopper definition that runs the engineering layer of ArchSim.

It contains the parametric massing logic, the structural analysis (Karamba3D), and the environmental simulation (Ladybug Tools) that ground every agent's claim in real numerical data — beam utilisation, deflection, lateral drift, solar radiation, daylight hours, energy load, and carbon emissions.

## Requirements

- **Rhino 7+**
- **Grasshopper** (bundled with Rhino)
- **[Karamba3D](https://karamba3d.com/)** — for structural analysis
- **[Ladybug Tools](https://www.ladybug.tools/)** — for environmental simulation

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
