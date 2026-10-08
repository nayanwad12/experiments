# pinterest-refs

Pulls Pinterest pins into a local folder so Claude can study them for style:
palette, lighting, materials, composition, and motion ideas.

**These are references, not assets.** Pins belong to their creators. Look at them,
write down what makes the look work, then make original artwork. Never copy a pin
or put one in a render.

## Setup

The cloud environment must allow these domains: `www.pinterest.com`, `pinterest.com`,
`i.pinimg.com`, `s.pinimg.com`. The tool uses the Chromium that comes with the container.

```bash
cd tools/pinterest-refs && npm install
```

## Usage

```bash
# search terms
node tools/pinterest-refs/pinsearch.js "clay mascot character 3d" references/clay-mascot 12

# or a board / pin / search URL
node tools/pinterest-refs/pinsearch.js "https://www.pinterest.com/<user>/<board>/" references/my-board 20
```

Each run writes to the output folder:
- `01.jpg … NN.jpg`: pins at 736px wide
- `_grid.png`: a screenshot of the results page, for a quick overview
- `pins.json`: the query and the source URL of each image

`references/` is gitignored, so pins never get committed. Commit only the
written brief (`references/<topic>/BRIEF.md`) that describes the look.

## Limits

- Pinterest shows a sign-up wall to visitors who aren't logged in, so each run
  gets about 20–25 pins. To get more, run several narrower searches.
- Only public boards work. Secret boards need a login.
