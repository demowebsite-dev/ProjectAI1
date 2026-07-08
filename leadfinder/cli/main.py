"""LeadFinder AI CLI entry point.

Commands
--------
leadfinder search    -- Run a lead search via Meta Ads Library
leadfinder leads     -- List leads already stored in the database
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

from leadfinder.config.settings import settings
from leadfinder.crawler.meta.country_codes import resolve_country_code
from leadfinder.crawler.meta.searcher import search_meta_ads
from leadfinder.utils.logger import logger
from leadfinder.database.db import DatabaseManager

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = typer.Typer(
    name="leadfinder",
    help="[bold cyan]LeadFinder AI[/bold cyan] – Find small businesses running Meta ads that need a website.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    """Print the LeadFinder AI welcome banner."""
    console.print(
        Panel.fit(
            "[bold cyan]LeadFinder AI[/bold cyan]  [dim]v0.1.0[/dim]\n"
            "[dim]Find Meta-ad-running businesses that need a website.[/dim]",
            border_style="cyan",
        )
    )


def _build_leads_table(leads: list[dict], title: str = "Leads") -> Table:
    """Build a Rich table from a list of lead dicts."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", justify="right", no_wrap=True)
    table.add_column("Business", style="bold white", min_width=20)
    table.add_column("Country", style="dim")
    table.add_column("Keyword", style="dim")
    table.add_column("Followers", justify="right")
    table.add_column("Phone", style="green")
    table.add_column("WhatsApp", justify="center")
    table.add_column("Website", style="yellow")
    table.add_column("Score", justify="right", style="magenta bold")

    for lead in leads:
        has_whatsapp = lead.get("whatsapp")
        table.add_row(
            str(lead.get("id", "")),
            lead.get("name", ""),
            lead.get("country") or "",
            lead.get("keyword") or "",
            str(lead.get("followers", "")) if lead.get("followers") is not None else "",
            lead.get("phone") or "",
            "[green]✓[/green]" if has_whatsapp else "[red]✗[/red]",
            lead.get("website") or "[dim]None[/dim]",
            str(lead.get("score", "")) if lead.get("score") is not None else "",
        )
    return table


def _build_ads_table(ads: list, title: str = "Meta Ads Found") -> Table:
    """Build a Rich table to display raw :class:`AdResult` objects."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", justify="right")
    table.add_column("Advertiser", style="bold white", min_width=22)
    table.add_column("CTA", style="cyan")
    table.add_column("Platforms", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Ad URL", style="dim", max_width=45, no_wrap=True)

    for i, ad in enumerate(ads, start=1):
        status_fmt = (
            "[green]Active[/green]" if ad.status == "Active"
            else "[red]Inactive[/red]" if ad.status == "Inactive"
            else f"[yellow]{ad.status}[/yellow]"
        )
        table.add_row(
            str(i),
            ad.advertiser_name,
            ad.cta or "",
            ", ".join(ad.platforms),
            status_fmt,
            ad.ad_url or "",
        )
    return table


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def search(
    country: str = typer.Option(..., "--country", "-c", help="Target country (e.g. India, US)"),
    keyword: str = typer.Option(..., "--keyword", "-k", help="Keyword for Meta Ads search (e.g. 'Real Estate')"),
    followers_max: Optional[int] = typer.Option(None, "--followers-max", help="Filter: max follower count"),
    phone_required: bool = typer.Option(False, "--phone-required", help="Filter: must have phone"),
    whatsapp_required: bool = typer.Option(False, "--whatsapp-required", help="Filter: must have WhatsApp"),
    max_results: int = typer.Option(50, "--max-results", help="Maximum number of ads to fetch"),
    export: Optional[str] = typer.Option(
        None, "--export", help="Export format: csv or txt", show_default=False
    ),
) -> None:
    """Search Meta Ads Library for leads and save results to the database.

    Example::

        leadfinder search --country India --keyword "Real Estate" --followers-max 1000
    """
    _print_banner()
    logger.info("Starting search | country=%s keyword=%s", country, keyword)

    console.print(f"[bold]Country:[/bold]  {country}")
    console.print(f"[bold]Keyword:[/bold]  {keyword}")
    if followers_max is not None:
        console.print(f"[bold]Max Followers:[/bold] {followers_max}")
    if phone_required:
        console.print("[bold]Filter:[/bold] Phone required")
    if whatsapp_required:
        console.print("[bold]Filter:[/bold] WhatsApp required")
    if export:
        console.print(f"[bold]Export:[/bold] {export.upper()}")
    console.print()

    # ── Validate country code ──────────────────────────────────────────────
    try:
        country_code = resolve_country_code(country)
    except ValueError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    # ── Run Meta Ads search ────────────────────────────────────────────────
    ads = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(
            f"Searching Meta Ads Library for [bold]{keyword}[/bold] in [bold]{country}[/bold] …",
            total=None,
        )
        try:
            ads = search_meta_ads(country, keyword, max_results=max_results)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]✗ Meta Ads search failed: {exc}[/red]")
            logger.error("Meta Ads search error: %s", exc, exc_info=True)
            raise typer.Exit(1)

    if not ads:
        console.print("[yellow]No ads found for the given search criteria.[/yellow]")
        raise typer.Exit(0)

    # ── Display results ────────────────────────────────────────────────────
    console.print(_build_ads_table(ads, title=f"Meta Ads Found ({len(ads)})"))

    # ── Save to DB ─────────────────────────────────────────────────────────
    db = DatabaseManager()
    saved = 0
    for ad in ads:
        try:
            db.insert_business(
                {
                    "name": ad.advertiser_name,
                    "facebook": ad.advertiser_url,
                    "cta": ad.cta,
                    "country": country_code,
                    "keyword": keyword,
                }
            )
            saved += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not save ad %r to DB: %s", ad.advertiser_name, exc)

    console.print(f"\n[green]✓[/green] Saved [bold]{saved}[/bold] advertisers to database.")
    console.print(
        "[dim]Next: run Milestone 3 (Facebook analysis) to enrich followers/phone/website data.[/dim]"
    )

    if export:
        console.print(f"[dim]Export ({export.upper()}) will be available from Milestone 9+.[/dim]")


@app.command(name="leads")
def list_leads(
    country: Optional[str] = typer.Option(None, "--country", "-c", help="Filter by country"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="Filter by keyword"),
) -> None:
    """List all leads currently stored in the database.

    Example::

        leadfinder leads --country India
    """
    _print_banner()
    db = DatabaseManager()
    results = db.list_businesses(country=country, keyword=keyword)

    if not results:
        console.print("[yellow]No leads found in the database.[/yellow]")
        raise typer.Exit(0)

    table = _build_leads_table(results, title=f"Stored Leads ({len(results)})")
    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
