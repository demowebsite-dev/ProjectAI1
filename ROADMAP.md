# Project Roadmap

## Version 1.0 (Current)

The goal of V1 is to find small businesses running Meta ads that likely need web development services, strictly relying on Meta platforms for data.

- [x] **Milestone 1**: Core Project Setup (CLI, DB, Settings, Logger, base models).
- [x] **Milestone 2**: Meta Ads Library Crawler (HTML parser + Playwright searcher).
- [x] **Milestone 3**: Facebook Page Analysis (Profile parsing, followers, contact info).
- [x] **Milestone 4**: Instagram Profile Analysis (Bio parsing, followers).
- [x] **Milestone 5**: Phone Extraction (`phonenumbers` normalization).
- [x] **Milestone 6**: WhatsApp Detection (wa.me, api.whatsapp.com).
- [x] **Milestone 7**: Website Detection (Validating external URLs, Facebook redirect decoding).
- [x] **Milestone 8**: Lead Scoring Engine.
- [x] **Milestone 9**: CSV Export Integration.
- [x] **Milestone 10**: TXT Export Integration & Final Polish.

## Version 2.0 (Future)

V2 will expand the intelligence and reach of the platform beyond the Meta ecosystem.

- **Google Maps Integration**: Cross-reference businesses found on Meta with their Google My Business listings to grab verified emails and ratings.
- **Local Directories**: Integrate scrapers for JustDial and Sulekha to enrich India-specific leads.
- **Email Finder**: Integrate with services like Hunter.io or perform deep website crawling to find contact emails.
- **Automated Outreach**: Draft personalized emails or WhatsApp messages based on the extracted business profile and score.
- **Web App UI**: Move beyond the CLI to a full Next.js or React dashboard for managing leads.
