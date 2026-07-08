from pydantic import BaseModel, Field

class MetaSelectors(BaseModel):
    """Selectors for Meta Ads Library scraper."""
    search_results_container: str = ".x1gl752r"  # General class for result grid or items
    ad_card: str = "div[style*='border-radius: 8px']"  # Facebook ad card usually has specific inline styles or classes
    advertiser_name: str = "a[href*='facebook.com/'], a[href*='instagram.com/']"
    ad_details_button: str = "div[role='button']:has-text('See ad details')"
    cta_text: str = "div[role='button']"  # or specific CTA spans
    platforms_container: str = "div:has(> img[src*='facebook']), div:has(> img[src*='instagram'])"
    ad_status: str = "span:has-text('Active'), span:has-text('Inactive')"

class FacebookSelectors(BaseModel):
    """Selectors for Facebook Page scraper."""
    # FB pages might use different versions (classic vs new profile page design)
    # We will define multiple selector options or clean text search approaches.
    page_name: str = "h1"
    # Selectors for followers
    followers_text: str = "a[href*='followers']"  # usually says "X followers"
    # Selectors for page details
    about_section: str = "div[role='main']"
    phone_link: str = "a[href^='tel:']"
    whatsapp_link: str = "a[href*='wa.me'], a[href*='api.whatsapp.com']"
    website_link: str = "a[href*='l.facebook.com/l.php']"  # FB redirects outgoing links

class InstagramSelectors(BaseModel):
    """Selectors for Instagram Profile scraper."""
    profile_header: str = "header"
    username: str = "h2"
    bio: str = "h1 ~ span, div._ap3a"
    followers_count: str = "a[href*='followers'] span"
    website: str = "a[href*='instagram.com/l.php'], a[target='_blank']"

class SelectorConfig(BaseModel):
    """Combined selector configuration."""
    meta: MetaSelectors = Field(default_factory=MetaSelectors)
    facebook: FacebookSelectors = Field(default_factory=FacebookSelectors)
    instagram: InstagramSelectors = Field(default_factory=InstagramSelectors)

selectors = SelectorConfig()
