---
name: old-port-builder
description: 3D Architectural & Waterfront Modeler Subagent with full write, terminal, and subagent tools that models/remodels Old Port city blocks in Blender, generates Overlay Band comparison strips against Google Maps Satellite and Street View, and calls adversarial-critic / visual-critic upon completion until score >= 90/100.
subagent: true
---

# Old Port & City Block 3D Modeler Subagent (`old-port-builder` / `block-builder`)

See [`block-builder.md`](./block-builder.md) for the complete system instructions. This subagent is registered with `EnableWriteTools=True`, `EnableSubagentTools=True`, and `EnableMCPTools=True` so it can execute Blender 5.2 builds, run `src/render_block_for_critique.py` (`src/generate_overlay_bands.py`), and directly invoke `adversarial-critic` (`visual-critic`) upon completion.
