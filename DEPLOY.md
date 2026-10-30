# PrintReady AI deploy

## Live now (free)
**https://basileion.github.io/printready/** — GitHub Pages (`site/` via Actions).

## Cloudflare Pages (printready.pages.dev) — blocked on API token

Box `CLOUDFLARE_API_TOKEN` can **list** Pages projects (Read) but **cannot create or deploy** (needs **Pages Write**). Cloudflare MCP also lacks `page.write`.

### One-time fix (Kurt, ~1 minute, $0)
1. Open https://dash.cloudflare.com/552c4ecb2438c0156cd65d0fc269c83c/pages/new
2. Connect Git → `Basileion/printready`
3. Project name: `printready`
4. Build command: *(empty)* · Output directory: `site` · Root: `/`
5. Save → production URL **https://printready.pages.dev**

Optional: add repo secrets `CLOUDFLARE_API_TOKEN` (with Pages Write) + `CLOUDFLARE_ACCOUNT_ID=552c4ecb2438c0156cd65d0fc269c83c`, then run workflow **Deploy Cloudflare Pages**.

After the project exists with Git connected, every push to `main` auto-deploys without the local token needing Write.
