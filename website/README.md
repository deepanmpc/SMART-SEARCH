# Search Wizard Website

Complete product website for Search Wizard — Spotlight For Your Computer.

## Files
- `index.html` — Full single-page website
- `styles.css` — All styles (dark theme, glassmorphism, animations)
- `script.js` — Interactions, typing effect, scroll animations, parallax

## Sections
1. **Hero** — Headline, CTA buttons, animated launcher mockup with typing effect
2. **Stats Bar** — 50K+ files, <400ms response, 5 file types, 100% privacy
3. **Features** — 6 feature cards with icons (large semantic + multimodal card)
4. **How It Works** — 5-step visual pipeline
5. **Demo** — Auto-cycling steps + terminal-style demo window
6. **Download** — 3 platform cards (macOS/Windows/Linux) + API key setup
7. **Documentation** — Links to setup.md, usage.md, faq.md + keyboard shortcuts
8. **GitHub** — Open source CTA banner
9. **Creator** — Deepan Chandrasekaran bio card
10. **Footer** — Links, creator credit, GitHub Pages mention

## Deployment to GitHub Pages

The `.github/workflows/deploy-website.yml` file auto-deploys on every push.

**Enable GitHub Pages:**
1. Go to your repo on GitHub → Settings → Pages
2. Set Source to "GitHub Actions"
3. Push any commit — site will deploy automatically

**Live URL:** `https://deepanmpc.github.io/SMART-SEARCH/`

## Design System
- **Font:** Inter (Google Fonts)
- **Background:** #05050a (near-black)
- **Accent:** #6366f1 (Indigo) + #c084fc (Purple)
- **Glass cards:** `backdrop-filter: blur(40px)` + subtle borders
- **Animations:** Floating orbs, parallax on mouse move, scroll reveal, typing loop
