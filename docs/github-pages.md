# Publish this application on GitHub Pages

The application is a static site. The included workflow packages the committed `public/` datasets, fonts, equations and animation frames using Python, then deploys `dist/` to GitHub Pages. It needs no API keys, Node server, MHD solver, original research directory or access to the local session archives. Publishing includes the research record already present in the application.

Both project sites (`https://YOUR_USERNAME.github.io/mhd-3i-atlas/`) and an account site (`https://YOUR_USERNAME.github.io/`) work. Paths resolve relative to the application, including fonts, transcript chunks, animation frames and downloads. Navigation uses URL fragments such as `#methods`, so a page reload requires no server rewrite.

## Connect from your Mac to the existing WSL copy

Run in **Terminal on your Mac**, using your usual reachable Windows SSH destination in place of `cabot@TORCH` if needed:

```bash
ssh -t cabot@TORCH "wsl.exe -e bash"
```

This opens a shell **inside WSL on the Windows machine**. If you already have an SSH session into WSL, use that session. Run the remaining publishing commands there; do not run the `/mnt/c/...` commands directly on macOS.

## Prepare GitHub access in WSL

```bash
cd /mnt/c/Users/cabot/OneDrive/Documents/Research/Cambridge/X3I/mhd_llm_app
sudo apt update
sudo apt install git gh
GH_BROWSER=echo gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
gh auth status
```

`GH_BROWSER=echo` prints the login URL instead of trying to launch a browser on the remote machine, using the CLI's [browser override](https://cli.github.com/manual/gh_help_environment). Leave this command running in WSL. When prompted, press Enter, then open **https://github.com/login/device** in your Mac's browser, enter the one-time code printed in WSL and authorize your personal account. The WSL command completes after authorization; then run `gh auth setup-git` and `gh auth status`.

If the original command is still waiting after a browser-opening error, you can use its displayed code on your Mac without restarting it. If the code has expired or the command has exited, rerun the command above. The `workflow` scope permits uploading the included workflow file. This is the [GitHub CLI browser login](https://cli.github.com/manual/gh_auth_login); the browser and CLI can run on different machines.

Set your commit identity if it is not configured, using the name and verified email or GitHub no-reply address associated with your account:

```bash
git config --global user.name "Your Name"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

## Create and push your personal repository

This example uses `mhd-3i-atlas` as the repository name. Choose an unused name if that repository already exists. A public repository supports GitHub Pages on GitHub Free; private-repository availability depends on your plan. See [GitHub Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

For this initially unversioned application directory:

```bash
git init -b main
git add .
git status --short
git commit -m "Add 3I ATLAS solar-wind research dashboard"
gh repo create mhd-3i-atlas --public --source=. --remote=origin --push
gh repo view --json url --jq .url
```

The last command prints your repository URL. `gh repo create` uses the authenticated personal account when no owner is specified. `.gitignore` excludes the generated `dist/`, local runtime directory, dependencies, credentials files and task prompt; the precomputed assets in `public/` must be committed. See the [GitHub CLI repository command](https://cli.github.com/manual/gh_repo_create).

Alternatively, create an **empty public repository** called `mhd-3i-atlas` at [GitHub’s new-repository page](https://github.com/new), without a README, license or `.gitignore`. Run the `git init`, `git add` and `git commit` commands above, then replace `YOUR_USERNAME` and run these **instead of** `gh repo create`:

```bash
git remote add origin https://github.com/YOUR_USERNAME/mhd-3i-atlas.git
git push -u origin main
```

## Enable Pages and run the deployment

On your Mac, open the repository URL, then select **Settings → Pages → Build and deployment → Source → GitHub Actions**. The workflow is already included; you do not need to create a workflow from a template. These are GitHub’s [custom-workflow publishing settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

The initial push may run before Pages is enabled. After selecting the source, explicitly start it again in **WSL**:

```bash
gh workflow run pages.yml --ref main
gh run list --workflow pages.yml --limit 3
```

Open the repository’s **Actions** tab, select **Publish research dashboard**, and wait for both **build** and **deploy** to pass. The deploy job displays the site URL. It is also shown in **Settings → Pages**. On your Mac, replace `YOUR_USERNAME` and open:

```bash
open https://YOUR_USERNAME.github.io/mhd-3i-atlas/
```

The site is then hosted by GitHub; viewing it does not require the Windows machine, WSL server or SSH tunnel to remain running.

For an account-root site, name the repository exactly `YOUR_USERNAME.github.io` instead. Use the same workflow and Pages source; the site URL becomes `https://YOUR_USERNAME.github.io/`.

## Publish subsequent edits

Run in the application directory in **WSL**:

```bash
git add .
git commit -m "Update research dashboard"
git push
```

Each push to `main` deploys automatically. For a presentation change, do not run the data-extraction commands: the workflow packages the existing assets and verifies their checksums. If you intentionally update scientific products, regenerate those products locally and commit the changed files under `public/` before pushing.

## Local verification and troubleshooting

The build and static checks use Python’s standard library:

```bash
python3 scripts/build_app.py
python3 scripts/check_static_site.py dist
python3 scripts/serve.py --port 8080
```

For the dedicated browser check, use Node 22.12 or later:

```bash
npm ci
npx playwright install chromium
node tests/pages.mjs
```

This test serves the built site under both `/` and `/example-repo/` using strict static hosts. It checks eight views, field images and downloads, local fonts/equations, transcript chunks/search/notes, and a hash deep-link reload. The prefixed host rejects requests outside its repository path.

If deployment reports that Pages is not enabled, select **GitHub Actions** in Pages settings, then rerun `gh workflow run pages.yml --ref main`. If permission is denied, confirm you are signed into the repository-owning account and that Actions is enabled in **Settings → Actions → General**. The workflow explicitly grants `pages: read` to setup and `pages: write` plus `id-token: write` to deployment, as required by the [Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

If you see the repository README instead of the application, verify the Pages source is **GitHub Actions**, rather than a branch or the `docs/` folder. If a filename is missing, check that `public/` was committed. `dist/` is deliberately ignored because the workflow builds it. Hard-refresh after deployment if your browser still shows an older version.

The artifact must remain within [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), including a maximum published site size of 1 GB. The static checker reports the actual packaged size and rejects oversized artifacts and files. The current workflow uses `actions/checkout@v6`, `actions/setup-python@v6`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4` and `actions/deploy-pages@v4`; it needs no repository secrets.

Official documentation checked on 17 October 2026.
