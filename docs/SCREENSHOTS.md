# DevSelect Screenshot Guide

The repository does not currently include recruiter-ready product screenshots. Add no more than four carefully reviewed images before sharing the project widely.

## Recommended Set

1. `assets/screenshots/landing-light.png`
   - Landing page in light mode.
   - Show the product name and primary workflow clearly.
   - Alt text: `DevSelect candidate evaluation landing page in light mode`.

2. `assets/screenshots/chat-dark.png`
   - Authenticated chat page in dark mode.
   - Use an empty state or fake candidate data.
   - Alt text: `DevSelect recruiter chat workspace in dark mode`.

3. `assets/screenshots/report-light.png`
   - Structured hiring report generated from a synthetic CV.
   - Show useful report sections without exposing personal data.
   - Alt text: `DevSelect structured AI hiring report generated from sample data`.

4. `assets/diagrams/architecture.png`
   - Export of the architecture diagram in `docs/ARCHITECTURE.md`.
   - Alt text: `DevSelect frontend, backend, database, Redis, and AI workflow architecture`.

## Privacy Checklist

Before adding an image:

- use only fake or intentionally public sample candidate data
- remove or blur email addresses, phone numbers, locations, user IDs, chat IDs, and filenames
- remove tokens, private query parameters, project references, admin controls, and browser developer tools
- remove real CV content and provider/dashboard details
- check sidebar history for unrelated candidate names
- check the browser address bar for sensitive paths or parameters
- confirm no notification, profile menu, or background window exposes personal data

## File Guidance

- Prefer compressed PNG or WebP.
- Keep each image reasonably sized for a GitHub README.
- Do not commit videos, large GIFs, raw screen recordings, or browser profiles.
- Store product screenshots under `assets/screenshots/`.
- Store diagrams under `assets/diagrams/`.
- Use descriptive lowercase filenames.
- Add useful alt text for every image.

## Optional Light/Dark Pair

If both report themes are stable, use GitHub's theme-aware markup:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/screenshots/report-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/screenshots/report-light.png">
  <img alt="DevSelect generated hiring report screen" src="assets/screenshots/report-light.png">
</picture>
```

Do not add this block to the root README until both referenced files exist.
