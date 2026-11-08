# Haslital 3D

Interactive 3D map of the Haslital in the Bernese Oberland: Meiringen, Hasliberg, Rosenlaui, Grimsel, Gadmental and Engstlenalp. Pick a region, a place or a hike and the camera flies there. Every place and region has its own page with info, links and how to get there. Hikes come with distance, time, ascent and an elevation profile.

Live: https://eliasthecactus.github.io/haslital-3d/

Available in English, German, French, Italian and Spanish.

## How it works

Plain HTML and three.js, no build step. Everything the page needs is in `site/`:

- `places.json`: places and hikes (region, categories, filters, links, camera view)
- `text-en.json`, `text-de.json`, …: all texts per language
- `routes.json`: hiking routes with distance, ascent and elevation profile
- `terrain.png`, `ortho.jpg`, `tile-*.jpg`, `detail.jpg`: terrain and aerial images
- `buildings.txt`, `trees.txt`, `meta.json`: buildings, trees, lifts and peaks

To edit texts or places, change the JSON files. Pushing to `main` deploys to GitHub Pages.

To run it locally:

```
cd site && python3 -m http.server
```

The scripts in `build/` regenerate the map data from the sources below.

## Data

- Aerial imagery: © swisstopo (SWISSIMAGE)
- Elevation: Terrain Tiles on AWS Open Data
- Buildings, lifts, peaks and hiking routes: © OpenStreetMap contributors (ODbL)
