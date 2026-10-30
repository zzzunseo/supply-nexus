# Local rendering assets

All runtime assets are bundled locally; no CDN or external API is used during the demonstration.

- Three.js 0.180.0 and OrbitControls: MIT, © 2010–2025 three.js authors. Full license: `../legacy/frontend/node_modules/three/LICENSE` (also retained in the bundled JavaScript legal comments).
- Earth night, blue marble, and topology textures copied from the upstream three-globe example assets: https://github.com/vasturiano/three-globe/tree/master/example/img . Sources downloaded 2026-10-27; upstream example: https://github.com/vasturiano/globe.gl/blob/master/example/earth-shield/index.html . These are illustrative static Earth textures, not live satellite or news imagery.
- Boundary lines decoded from the existing local `static/world_110m.json`; see `../static/ATTRIBUTION.md`.

Rebuild (Node.js and existing dependencies):

    node legacy/frontend/node_modules/esbuild/bin/esbuild night_globe/index.js --bundle --format=esm --minify --loader:.jpg=dataurl --loader:.png=dataurl --outfile=night_globe/dist/globe.js --legal-comments=eof

Rendering is capped at approximately 30 frames/s with device pixel ratio ≤ 1.75. Animation pauses in a hidden tab, respects reduced-motion preference, and disposes GPU resources on removal.
