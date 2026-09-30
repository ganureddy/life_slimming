## life_slimming

Life slimming

### Production portal deployment

The Vue portal assets are generated and excluded from Git. Deploying the source
alone leaves `life_slimming/www/life_portal.html` pointing to missing hashed JS
and CSS files. Build the portal on each deployment; Vite writes the assets and
updates the HTML together. Do not edit the hashes manually.

From the production bench directory, after pulling the code:

```bash
cd apps/life_slimming
npm --prefix life_portal ci --include=dev
npm run build:portal
cd ../..
bench --site YOUR_SITE clear-cache
bench --site YOUR_SITE clear-website-cache
```

Replace `YOUR_SITE` with the production site name, then hard-refresh the browser.
The standard app `build` script builds both the older Angular frontend and the
Vue portal. The root install hook installs dependencies for both frontends.
For a full deployment, install app dependencies before running
`bench build --app life_slimming`.

If assets still return 404 after building, check that
`sites/assets/life_slimming` links to this app's `life_slimming/public` directory
and that the production web server serves `/assets` from `sites/assets`.

#### License

MIT