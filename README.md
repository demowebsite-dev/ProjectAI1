# LeadFinder AI

LeadFinder AI is a production-ready AI lead generation platform. Its primary goal is to find small businesses currently running Meta ads that are likely to need a website or web development services.

By automating the process of scanning the Meta Ads Library, extracting Facebook and Instagram profiles, and aggregating contact information (Phone, WhatsApp, Website), LeadFinder AI helps agencies identify high-value prospects quickly and efficiently.

## Core Features

- **Meta Ads Library Crawler**: Extracts active ad campaigns based on search keywords.
- **Social Media Profiling**: Visits Facebook and Instagram pages to gather deep contact data.
- **Intelligent Parsers**: Extracts phones (normalized via `phonenumbers`), detects WhatsApp links, and parses follower counts robustly.
- **Lead Scoring**: Assigns a score based on lead quality (e.g., higher score for businesses with no website and active ads).
- **Data Export**: Exports enriched leads to CSV or formatted TXT.
- **Robustness**: Employs retry logic, exponential backoff, and async Playwright to handle scraping flakiness gracefully.

## Quickstart

After following the instructions in `INSTALL.md` to set up the project:

### Command Line Interface

```bash
# Search for real estate leads in India
leadfinder search "real estate" --country IN --limit 5

# View all saved leads in the database
leadfinder leads
```

## Documentation

- [INSTALL.md](INSTALL.md) - Installation and setup guide.
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and data flow.
- [ROADMAP.md](ROADMAP.md) - Project milestones and future plans.
