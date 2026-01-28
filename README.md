# Guide Bot Marketing Website 🤖

A professional, modern marketing website for **Guide Bot** - the AI-powered Excel add-in for equity research automation.

## Live Site

🌐 **https://axelrodai.github.io/guidebot-website/**

## Tech Stack

- **HTML5** - Semantic markup
- **Tailwind CSS** (via CDN) - Utility-first styling
- **Vanilla JavaScript** - Interactive features
- **Vercel** - Hosting & deployment

## Features

- ✅ Responsive design (mobile-first)
- ✅ Dark mode aesthetic (fintech style)
- ✅ Smooth scroll navigation
- ✅ Interactive feature cards
- ✅ Mobile hamburger menu
- ✅ SEO-optimized meta tags
- ✅ Contact/waitlist form ready

## Pages/Sections

1. **Hero** - Main value proposition with live Excel preview mockup
2. **Features** - 6 key product features with icons
3. **How It Works** - 3-step getting started guide
4. **Demo** - Video placeholder section
5. **Pricing** - Free/Pro/Enterprise tiers
6. **About** - Company story
7. **Contact** - Email capture CTA
8. **Footer** - Links and social

## Local Development

Simply open `index.html` in a browser:

```bash
# macOS
open index.html

# Windows
start index.html

# Or use a local server
npx serve .
```

## Deployment

### Vercel (Recommended)

1. Push to GitHub
2. Connect to Vercel
3. Deploy automatically

Or use Vercel CLI:

```bash
npm i -g vercel
vercel
```

### Netlify

Drag and drop the folder into Netlify dashboard, or:

```bash
npm i -g netlify-cli
netlify deploy --prod
```

### GitHub Pages

Push to a repo and enable GitHub Pages in settings.

## Customization

### Colors
Edit the Tailwind config in `<script>` tag:
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                primary: '#10B981', // Change this
            }
        }
    }
}
```

### Contact Form
Update the form action URL to your email service:
- Formspree: `https://formspree.io/f/your-form-id`
- Getform: `https://getform.io/f/your-form-id`

### Demo Video
Replace the placeholder in the `#demo` section with an embedded video.

## Todo

- [ ] Add actual demo video
- [ ] Set up contact form endpoint
- [ ] Add screenshots of Excel add-in
- [ ] Add real testimonials
- [ ] Set up analytics (Plausible/Fathom)
- [ ] Add blog section

## License

© 2026 Guide Bot. All rights reserved.
