# List All Slider GUIDs — GHPython Component
# ─────────────────────────────────────────────────────────────────────────────
# USAGE: Paste into a GHPython component (no inputs needed).
#        Run it and check the "out" output (connect to a Panel).
#        It will list every Number Slider on the canvas with its name and GUID.
#        Copy the GUIDs for your 8 zoning sliders and send them to Claude.
# ─────────────────────────────────────────────────────────────────────────────

import Grasshopper as gh

doc = ghenv.Component.OnPingDocument()

print("=== ALL NUMBER SLIDERS ===")
print("")

for obj in doc.Objects:
    if isinstance(obj, gh.Kernel.Special.GH_NumberSlider):
        name = obj.NickName if obj.NickName else "(unnamed)"
        val = obj.CurrentValue
        print("Name: {}".format(name))
        print("GUID: {}".format(obj.InstanceGuid))
        print("Value: {}".format(val))
        print("---")

print("")
print("Copy the GUIDs above for your 8 zoning sliders:")
print("siteWidth, siteDepth, zoneMaxHeight, zoneMaxFSR,")
print("zoneFrontSetback, zoneSideSetback, zoneRearSetback, zoneMaxCoverage")
