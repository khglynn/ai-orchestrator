# Resume web view

This folder contains a self-contained, static implementation of a two-page resume that mirrors the layout of the source PDF while staying simple to edit and host.

## Stack choices
- **Plain HTML, CSS, and vanilla JavaScript**: easy to inspect and modify without build tooling.
- **Google Fonts (Rubik)**: matches the typography from the original design with a reliable web-hosted source.
- **LocalStorage persistence**: edits you make in the browser are saved locally without any backend services.

## Project structure
- `index.html` — entry point with a minimal toolbar and containers for the two-page layout.
- `styles.css` — typography, spacing tokens, layout grid, and print rules. Adjust CSS variables near the top to tweak sizing and colors.
- `script.js` — renders resume data into the layout, toggles edit mode, and saves changes.
- `data/resume.json` — default resume content and variants. Edit this to change the canonical copy that loads for first-time visitors.

## Editing content
1. Open `resume/index.html` in your browser (see "Run locally").
2. Click **Enable editing** in the toolbar.
3. Click any highlighted text to edit in place. Changes save automatically to your browser.
4. Use **Reset content** to reload the defaults from `data/resume.json`.

To change the default copy shipped with the site, edit the strings in `data/resume.json` and commit the file. The data model nests under `variants` to make future additions (like multiple targeted resumes or AI-assisted editing) straightforward.

## Layout and typography tweaks
- Typography, spacing, and accent colors are controlled via CSS variables at the top of `styles.css`.
- The layout is grid-based; adjust column ratios in the `.grid` rule if you want different column widths.
- Print styles are defined under `@media print` and the `@page` rule. The layout is sized for US Letter with generous margins; adjust the `--page-width`, `--page-height`, and `--page-padding` variables for other sizes.

## Print behavior
The layout is designed to render as exactly two pages. The browser print dialog will use the print-specific rules (no toolbar, neutral background) and the `@page` sizing to export a clean PDF.

## Persistence approach
Edits are stored in `localStorage` under the key `resume-data-v1`. Clearing site data or using a private window resets to the defaults in `data/resume.json`.

## Run locally / hosting
- Serve the `resume/` folder with a simple static server to keep `fetch` working for `data/resume.json`, e.g. `python -m http.server 8000` from the repo root and visit `http://localhost:8000/resume/`.
- To host, publish the `resume/` directory on any static hosting service (GitHub Pages, Netlify, S3). No build step is required.

## Future-friendly structure
- The `variants` object in `data/resume.json` is ready for multiple named resume versions.
- `script.js` isolates rendering, editing, and persistence so additional features (like AI-powered editing) can hook into the same data structure without changing the layout code.
