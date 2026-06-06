"""
AdSpy Agent - Facebook Ad Library Research Automation
=====================================================
Automated competitor ad research agent that:
1. Opens browser & navigates to Facebook Ad Library
2. Searches for any brand/keyword
3. Extracts all ad data + images
4. Analyzes copy DNA, creative DNA, angles, funnels
5. Generates rewrite suggestions based on competitor DNA
"""

import asyncio
import base64
import hashlib
import os
import re
from patchright.async_api import async_playwright


class AdSpyAgent:
    """Browser automation agent for Facebook Ad Library research."""

    AD_LIBRARY_URL = "https://www.facebook.com/ads/library/"

    def __init__(self, headless=False, max_ads=30, scroll_rounds=5, images_dir=None, slow_mo=None):
        self.headless = headless
        self.max_ads = max_ads
        self.scroll_rounds = scroll_rounds
        # When showing the browser, slow each action down so it is visible.
        self.slow_mo = slow_mo if slow_mo is not None else (0 if headless else 400)
        self.images_dir = images_dir or os.path.join(os.path.dirname(__file__), "..", "reports", "images")
        self.browser = None
        self.context = None
        self.page = None
        self.ads = []
        self.brand_info = {}
        self.copy_dna = {}
        self.creative_dna = {}

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def launch(self):
        self._pw = await async_playwright().start()
        # --no-sandbox / --disable-dev-shm-usage are required to run Chromium
        # inside a Docker container (root user, small /dev/shm).
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
        if not self.headless:
            launch_args.append("--start-maximized")
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=launch_args,
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()

    # ------------------------------------------------------------------
    # Navigate
    # ------------------------------------------------------------------

    async def navigate_to_ad_library(self, query: str, country: str = "ALL"):
        # Open the Ad Library for the chosen country WITHOUT a query, so the
        # search box is on screen and we can visibly type into it.
        base = (
            f"{self.AD_LIBRARY_URL}"
            f"?active_status=all&ad_type=all&country={country}"
            f"&search_type=keyword_unordered&media_type=all"
        )
        await self.page.goto(base, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        await self._dismiss_cookies()

        typed = await self._type_search(query)
        if not typed:
            # Fallback: load the full URL with the query baked in (reliable).
            print("       (search box not found - using direct URL)")
            await self.page.goto(base + f"&q={query}", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(4)
            await self._dismiss_cookies()
        await asyncio.sleep(3)

    async def _dismiss_cookies(self):
        try:
            cookie_btn = self.page.locator(
                'button:has-text("Allow all cookies"), '
                'button:has-text("Accept All"), '
                'button:has-text("Allow essential and optional cookies"), '
                'button:has-text("Allow")'
            )
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click()
                await asyncio.sleep(1.5)
        except Exception:
            pass

    async def _type_search(self, query: str) -> bool:
        """Visibly type the keyword into the Ad Library search box. Returns True on success."""
        selectors = [
            'input[placeholder*="keyword" i]',
            'input[placeholder*="advertiser" i]',
            'input[placeholder*="Search" i]',
            'input[type="search"]',
            'input[aria-label*="Search" i]',
            'input[role="combobox"]',
        ]
        box = None
        for sel in selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    box = loc
                    break
            except Exception:
                continue
        if box is None:
            return False
        try:
            await box.scroll_into_view_if_needed()
            await box.click()
            await asyncio.sleep(0.5)
            await box.fill("")
            # Type character-by-character so the keystrokes are visible.
            await box.press_sequentially(query, delay=140)
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(5)  # let results load
            return True
        except Exception as e:
            print(f"       (typing failed: {e})")
            return False

    # ------------------------------------------------------------------
    # Identify brand
    # ------------------------------------------------------------------

    async def identify_brand(self, query: str):
        body_text = await self.page.inner_text("body")
        results_match = re.search(r'([\d,>]+)\s*results?', body_text)
        total_results = results_match.group(1) if results_match else "Unknown"

        brand_names = re.findall(r'\n([A-Za-z0-9 .&\'-]+)\nSponsored', body_text)
        primary_brand = brand_names[0].strip() if brand_names else query

        brand_counts = {}
        for name in brand_names:
            n = name.strip()
            brand_counts[n] = brand_counts.get(n, 0) + 1

        self.brand_info = {
            "query": query,
            "matched_brand": primary_brand,
            "total_results": total_results,
            "brand_frequency": brand_counts,
        }
        return self.brand_info

    # ------------------------------------------------------------------
    # Scroll, collect text AND images
    # ------------------------------------------------------------------

    async def scroll_and_collect(self):
        for i in range(self.scroll_rounds):
            # Smooth, visible scroll: several small mouse-wheel steps per round.
            for _ in range(6):
                await self.page.mouse.wheel(0, 600)
                await asyncio.sleep(0.4)
            await asyncio.sleep(1.5)  # pause for new ads to lazy-load
        # Scroll back to top so image extraction starts from the beginning.
        await self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(1.5)

        full_text = await self.page.inner_text("body")
        return full_text

    async def extract_images(self):
        """Extract all ad creative images from the page."""
        os.makedirs(self.images_dir, exist_ok=True)

        # Get all images inside ad cards
        images_data = await self.page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            const results = [];
            for (const img of imgs) {
                const src = img.src || img.dataset.src || '';
                const alt = img.alt || '';
                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;
                // Filter: only ad creative images (skip icons, avatars, small images)
                if (src && w > 100 && h > 100 && !src.includes('emoji') && !src.includes('rsrc.php')) {
                    results.push({src, alt, width: w, height: h});
                }
            }
            return results;
        }""")

        # Also get video thumbnails / poster frames
        videos_data = await self.page.evaluate("""() => {
            const vids = document.querySelectorAll('video');
            const results = [];
            for (const vid of vids) {
                const poster = vid.poster || '';
                if (poster) results.push({src: poster, alt: 'Video thumbnail', width: 0, height: 0, is_video: true});
            }
            return results;
        }""")

        all_media = images_data + videos_data
        saved = []

        for i, img in enumerate(all_media):
            src = img.get("src", "")
            if not src or src.startswith("data:"):
                continue
            try:
                filename = f"ad_img_{i}_{hashlib.md5(src.encode()).hexdigest()[:8]}.jpg"
                filepath = os.path.join(self.images_dir, filename)

                # Download via the browser context to keep cookies/session
                response = await self.page.evaluate(f"""async () => {{
                    try {{
                        const resp = await fetch("{src}");
                        const blob = await resp.blob();
                        const reader = new FileReader();
                        return new Promise(resolve => {{
                            reader.onload = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }});
                    }} catch(e) {{ return null; }}
                }}""")

                if response and response.startswith("data:"):
                    # Strip the data URL prefix and decode
                    b64_data = response.split(",", 1)[1]
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    saved.append({
                        "filename": filename,
                        "url": src,
                        "alt": img.get("alt", ""),
                        "width": img.get("width", 0),
                        "height": img.get("height", 0),
                        "is_video": img.get("is_video", False),
                    })
            except Exception as e:
                print(f"  Warning: Could not save image {i}: {e}")

        return saved

    # ------------------------------------------------------------------
    # Parse ads
    # ------------------------------------------------------------------

    def parse_ads(self, full_text: str):
        parts = re.split(r'Library ID:\s*', full_text)
        ads = []
        for section in parts[1:]:
            ad = self._parse_single_ad(section)
            if ad:
                ads.append(ad)
            if len(ads) >= self.max_ads:
                break
        self.ads = ads
        return ads

    def _parse_single_ad(self, section: str):
        lines = [l.strip() for l in section.split("\n") if l.strip()]
        if len(lines) < 3:
            return None

        ad_id = self._extract_id(lines)
        status, date_range = self._extract_status_and_date(lines)
        platforms = self._extract_platforms(section)
        primary_text, headline, description, link_domain = self._extract_all_creative(lines)
        cta = self._extract_cta(section)
        media_type = self._detect_media_type(section)
        price = self._extract_price(section)

        return {
            "ad_id": ad_id,
            "platform": platforms,
            "status": status,
            "start_date": date_range,
            "primary_text": primary_text,
            "headline": headline,
            "description": description,
            "link_domain": link_domain,
            "cta": cta,
            "media_type": media_type,
            "price": price,
            "image_url": "",
            "image_file": "",
        }

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_id(lines):
        match = re.match(r'(\d+)', lines[0])
        return match.group(1) if match else "N/A"

    @staticmethod
    def _extract_status_and_date(lines):
        status = "Unknown"
        date_range = "N/A"
        for line in lines[:6]:
            if "Inactive" in line:
                status = "Inactive"
            elif "Active" in line and "Inactive" not in line:
                status = "Active"
            m = re.search(r'(\d{1,2}\s+\w+\s+\d{4})\s*[-\u2013]\s*(\d{1,2}\s+\w+\s+\d{4})', line)
            if m:
                date_range = f"{m.group(1)} - {m.group(2)}"
                if status == "Unknown": status = "Inactive"
                continue
            m2 = re.search(r'Started running on\s+(.+)', line)
            if m2:
                date_range = m2.group(1).strip()
                if status == "Unknown": status = "Active"
        return status, date_range

    @staticmethod
    def _extract_platforms(section):
        platforms = []
        low = section.lower()
        for name in ["facebook", "instagram", "messenger", "audience network"]:
            if name in low:
                platforms.append(name.title())
        return ", ".join(platforms) if platforms else "Facebook"

    @staticmethod
    def _extract_all_creative(lines):
        """Extract primary text, headline, description, and link domain."""
        sponsored_idx = None
        for idx, line in enumerate(lines):
            if line == "Sponsored":
                sponsored_idx = idx
                break
        if sponsored_idx is None:
            return "", "", "", ""

        stop_words = {
            "shop now", "learn more", "install now", "sign up", "download",
            "book now", "contact us", "apply now", "see more", "get offer",
            "watch more", "get started", "order now", "subscribe", "get quote",
        }

        copy_lines = []
        link_domain = ""
        headline_after_domain = ""
        description_line = ""
        found_domain = False

        for line in lines[sponsored_idx + 1:]:
            if line.lower() in stop_words:
                break
            if "See ad details" in line:
                break
            # Detect domain line (e.g. PLAY.GOOGLE.COM, NIKE.COM)
            if re.match(r'^[A-Z0-9._-]+\.[A-Z]{2,}$', line, re.IGNORECASE):
                link_domain = line
                found_domain = True
                continue
            # After domain, next lines are headline and description
            if found_domain:
                if not headline_after_domain:
                    headline_after_domain = line
                elif not description_line:
                    description_line = line
                continue
            # Price lines
            if re.match(r'^[\$\u20b9\u20ac\u00a3]', line):
                continue
            copy_lines.append(line)

        primary_text = " ".join(copy_lines)
        headline = copy_lines[0] if copy_lines else ""
        # If we found a headline after the domain, that's the actual link headline
        if headline_after_domain:
            description = headline_after_domain
        else:
            description = description_line

        return primary_text, headline, description, link_domain

    @staticmethod
    def _extract_cta(section):
        ctas = [
            "Shop Now", "Learn More", "Sign Up", "Download", "Get Offer",
            "Book Now", "Contact Us", "Apply Now", "Subscribe", "Watch More",
            "Get Quote", "See More", "Order Now", "Get Started", "Install Now",
        ]
        low = section.lower()
        for cta in ctas:
            if cta.lower() in low:
                return cta
        return "N/A"

    @staticmethod
    def _detect_media_type(section):
        low = section.lower()
        types = []
        if "video" in low:
            types.append("Video")
        else:
            types.append("Image")
        if "multiple versions" in low:
            types.append("Multiple Versions")
        if "carousel" in low:
            types.append("Carousel")
        return ", ".join(types)

    @staticmethod
    def _extract_price(section):
        m = re.search(r'([\$\u20b9\u20ac\u00a3][\d,.]+)', section)
        return m.group(1) if m else ""

    # ------------------------------------------------------------------
    # Assign images to ads
    # ------------------------------------------------------------------

    def assign_images_to_ads(self, saved_images):
        """Best-effort: assign downloaded images to ad entries."""
        # Images appear in page order, roughly matching ad order
        # Skip very small or icon images
        creative_imgs = [img for img in saved_images if not img.get("is_video", False)]
        for i, ad in enumerate(self.ads):
            if i < len(creative_imgs):
                ad["image_url"] = creative_imgs[i].get("url", "")
                ad["image_file"] = creative_imgs[i].get("filename", "")
                ad["image_alt"] = creative_imgs[i].get("alt", "")

    # ------------------------------------------------------------------
    # Copy breakdown
    # ------------------------------------------------------------------

    @staticmethod
    def analyze_copy(text: str) -> dict:
        if not text or len(text) < 10:
            return {k: "N/A" for k in ("hook", "problem", "solution", "offer", "cta")}
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if s.strip()]
        return {
            "hook": sentences[0] if len(sentences) > 0 else "N/A",
            "problem": sentences[1] if len(sentences) > 1 else "N/A",
            "solution": sentences[2] if len(sentences) > 2 else "N/A",
            "offer": sentences[3] if len(sentences) > 3 else "N/A",
            "cta": sentences[-1] if len(sentences) > 1 else "N/A",
        }

    # ------------------------------------------------------------------
    # Angle detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_angle(text: str) -> str:
        if not text:
            return "Unknown"
        low = text.lower()
        scores = {
            "Emotional": ["feel", "love", "heart", "dream", "inspire", "believe", "passion", "joy", "life", "story", "imagine", "empower"],
            "Logical": ["proven", "data", "research", "study", "percent", "%", "fact", "result", "compare", "benefit", "tested", "science"],
            "Fear-based": ["don't miss", "last chance", "limited", "hurry", "before it's too late", "warning", "risk", "lose", "never", "urgent", "running out", "ends soon"],
            "Luxury / Status": ["premium", "exclusive", "luxury", "elite", "vip", "limited edition", "iconic", "legendary", "prestige", "finest", "crafted", "curated"],
            "Discount / Offer": ["off", "sale", "discount", "free", "save", "deal", "offer", "code", "coupon", "buy one", "bogo", "clearance"],
        }
        totals = {a: sum(1 for kw in kws if kw in low) for a, kws in scores.items()}
        best = max(totals, key=totals.get)
        return best if totals[best] > 0 else "Brand Awareness"

    # ------------------------------------------------------------------
    # Funnel mapping
    # ------------------------------------------------------------------

    @staticmethod
    def detect_funnel_stage(ad: dict) -> str:
        blob = " ".join(ad.get(k, "") for k in ("primary_text", "headline", "cta")).lower()
        c = sum(1 for w in ["shop now", "buy", "order", "get offer", "add to cart", "purchase", "checkout", "sign up", "install now"] if w in blob)
        co = sum(1 for w in ["learn more", "compare", "review", "see how", "find out", "discover", "explore", "watch more"] if w in blob)
        a = sum(1 for w in ["introducing", "meet", "new", "announcing", "check out", "watch", "story", "inspire", "just do it"] if w in blob)
        if c > co and c > a: return "Conversion"
        if co > a: return "Consideration"
        return "Awareness"

    # ------------------------------------------------------------------
    # COPY DNA ANALYSIS - patterns across ALL ads
    # ------------------------------------------------------------------

    def analyze_copy_dna(self):
        """Analyze patterns across all ad copies to extract the brand's copy DNA."""
        texts = [a.get("primary_text", "") for a in self.ads if a.get("primary_text")]
        headlines = [a.get("headline", "") for a in self.ads if a.get("headline")]
        ctas = [a.get("cta", "") for a in self.ads if a.get("cta") and a["cta"] != "N/A"]

        if not texts:
            self.copy_dna = {}
            return self.copy_dna

        # Average copy length
        avg_len = sum(len(t) for t in texts) / len(texts)
        avg_words = sum(len(t.split()) for t in texts) / len(texts)
        avg_sentences = sum(len(re.split(r'[.!?]+', t)) for t in texts) / len(texts)

        # Emoji usage
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F9FF\U00002700-\U000027BF\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]')
        emoji_count = sum(len(emoji_pattern.findall(t)) for t in texts)
        uses_emoji = emoji_count > 0
        emoji_per_ad = emoji_count / len(texts) if texts else 0

        # Tone analysis
        all_text = " ".join(texts).lower()
        tone_scores = {
            "Conversational": ["you", "your", "you're", "let's", "hey", "ready", "want"],
            "Professional": ["achieve", "optimize", "solution", "deliver", "proven", "results"],
            "Urgent": ["now", "today", "hurry", "limited", "fast", "don't wait", "last chance"],
            "Inspirational": ["dream", "believe", "imagine", "transform", "unlock", "empower", "inspire"],
            "Direct/Command": ["get", "try", "start", "join", "discover", "find", "shop", "buy"],
        }
        tone_results = {}
        for tone, words in tone_scores.items():
            score = sum(all_text.count(w) for w in words)
            tone_results[tone] = score
        dominant_tone = max(tone_results, key=tone_results.get) if tone_results else "Neutral"

        # Hook patterns (first line analysis)
        hook_types = {"Question": 0, "Statement": 0, "Command": 0, "Exclamation": 0, "Number/Stat": 0}
        for t in texts:
            first = t.split(".")[0].split("!")[0].split("?")[0].strip()
            if "?" in t.split(".")[0]:
                hook_types["Question"] += 1
            elif first and first[0].isdigit():
                hook_types["Number/Stat"] += 1
            elif any(t.startswith(w) for w in ["Get ", "Try ", "Start ", "Join ", "Find ", "Shop ", "Buy ", "Discover "]):
                hook_types["Command"] += 1
            elif "!" in t[:50]:
                hook_types["Exclamation"] += 1
            else:
                hook_types["Statement"] += 1
        dominant_hook = max(hook_types, key=hook_types.get)

        # Language detection (simple)
        lang_indicators = {
            "English": ["the", "and", "for", "with", "your", "our"],
            "Spanish": ["para", "los", "las", "con", "mejor", "tu"],
            "Portuguese": ["para", "com", "sua", "seu", "mais"],
            "Hindi": ["\u0915\u0947", "\u0939\u0948", "\u0915\u093e", "\u0915\u0940"],
        }
        lang_scores = {}
        for lang, words in lang_indicators.items():
            lang_scores[lang] = sum(all_text.count(f" {w} ") for w in words)
        languages_used = [l for l, s in lang_scores.items() if s > 2]

        # CTA patterns
        from collections import Counter
        cta_freq = dict(Counter(ctas).most_common())

        # Power words frequency
        power_words = ["free", "new", "best", "exclusive", "limited", "premium", "save", "discover",
                       "transform", "ultimate", "proven", "guaranteed", "instant", "easy", "secret"]
        found_power_words = {w: all_text.count(w) for w in power_words if all_text.count(w) > 0}

        # Headline patterns
        avg_headline_len = sum(len(h) for h in headlines) / len(headlines) if headlines else 0
        avg_headline_words = sum(len(h.split()) for h in headlines) / len(headlines) if headlines else 0

        self.copy_dna = {
            "total_ads_analyzed": len(texts),
            "avg_copy_length_chars": round(avg_len),
            "avg_copy_length_words": round(avg_words, 1),
            "avg_sentences_per_ad": round(avg_sentences, 1),
            "avg_headline_length_chars": round(avg_headline_len),
            "avg_headline_words": round(avg_headline_words, 1),
            "uses_emoji": uses_emoji,
            "emoji_per_ad": round(emoji_per_ad, 1),
            "dominant_tone": dominant_tone,
            "tone_scores": tone_results,
            "dominant_hook_type": dominant_hook,
            "hook_type_distribution": hook_types,
            "cta_frequency": cta_freq,
            "languages_detected": languages_used or ["English"],
            "power_words_used": found_power_words,
            "copy_formula": self._detect_copy_formula(texts),
        }
        return self.copy_dna

    @staticmethod
    def _detect_copy_formula(texts):
        """Detect which copy framework the brand most uses."""
        formulas = {
            "PAS (Problem-Agitate-Solve)": 0,
            "AIDA (Attention-Interest-Desire-Action)": 0,
            "BAB (Before-After-Bridge)": 0,
            "Direct Offer": 0,
            "Storytelling": 0,
        }
        for t in texts:
            low = t.lower()
            sentences = len(re.split(r'[.!?\n]+', t))
            if any(w in low for w in ["problem", "struggle", "tired of", "frustrated"]):
                formulas["PAS (Problem-Agitate-Solve)"] += 1
            if sentences >= 3 and any(w in low for w in ["imagine", "what if", "picture"]):
                formulas["BAB (Before-After-Bridge)"] += 1
            if any(w in low for w in ["story", "journey", "when i", "i remember", "once"]):
                formulas["Storytelling"] += 1
            if any(w in low for w in ["% off", "free", "discount", "deal", "save"]):
                formulas["Direct Offer"] += 1
            else:
                formulas["AIDA (Attention-Interest-Desire-Action)"] += 1

        return max(formulas, key=formulas.get)

    # ------------------------------------------------------------------
    # CREATIVE DNA ANALYSIS
    # ------------------------------------------------------------------

    def analyze_creative_dna(self):
        """Analyze visual/creative patterns across all ads."""
        from collections import Counter

        media_types = Counter(a.get("media_type", "Unknown") for a in self.ads)
        platforms = Counter(a.get("platform", "Unknown") for a in self.ads)
        statuses = Counter(a.get("status", "Unknown") for a in self.ads)
        angles = Counter(a.get("angle", "Unknown") for a in self.ads)
        funnels = Counter(a.get("funnel_stage", "Unknown") for a in self.ads)

        # Image alt text analysis for creative style
        alt_texts = [a.get("image_alt", "") for a in self.ads if a.get("image_alt")]
        creative_styles = {"Product Shot": 0, "Lifestyle": 0, "Text Overlay": 0, "Model/Person": 0, "Abstract/Brand": 0}
        for alt in alt_texts:
            low = alt.lower()
            if any(w in low for w in ["product", "shoe", "shirt", "pants", "dress", "bag"]):
                creative_styles["Product Shot"] += 1
            if any(w in low for w in ["person", "man", "woman", "people", "model", "wearing"]):
                creative_styles["Model/Person"] += 1
            if any(w in low for w in ["lifestyle", "outdoor", "running", "sport", "gym"]):
                creative_styles["Lifestyle"] += 1

        # Ad longevity analysis
        durations = []
        for ad in self.ads:
            date = ad.get("start_date", "")
            m = re.search(r'(\d{1,2}\s+\w+\s+\d{4})\s*-\s*(\d{1,2}\s+\w+\s+\d{4})', date)
            if m:
                try:
                    from datetime import datetime
                    start = datetime.strptime(m.group(1), "%d %b %Y")
                    end = datetime.strptime(m.group(2), "%d %b %Y")
                    durations.append((end - start).days)
                except Exception:
                    pass

        avg_duration = round(sum(durations) / len(durations)) if durations else 0
        has_multiversion = sum(1 for a in self.ads if "Multiple Versions" in a.get("media_type", ""))

        self.creative_dna = {
            "media_type_distribution": dict(media_types.most_common()),
            "platform_distribution": dict(platforms.most_common()),
            "status_distribution": dict(statuses.most_common()),
            "angle_distribution": dict(angles.most_common()),
            "funnel_distribution": dict(funnels.most_common()),
            "creative_style_hints": creative_styles,
            "avg_ad_duration_days": avg_duration,
            "ads_with_multiple_versions": has_multiversion,
            "ab_testing_rate": round(has_multiversion / len(self.ads) * 100) if self.ads else 0,
            "total_images_extracted": sum(1 for a in self.ads if a.get("image_file")),
        }
        return self.creative_dna

    # ------------------------------------------------------------------
    # REWRITE ENGINE
    # ------------------------------------------------------------------

    def generate_rewrites(self, product_name="", product_desc="", target_audience=""):
        """Generate ad copy rewrites based on the analyzed DNA."""
        dna = self.copy_dna
        if not dna:
            return []

        # Build parameters from DNA
        tone = dna.get("dominant_tone", "Direct/Command")
        hook_type = dna.get("dominant_hook_type", "Statement")
        formula = dna.get("copy_formula", "AIDA")
        uses_emoji = dna.get("uses_emoji", False)
        avg_words = int(dna.get("avg_copy_length_words", 20))
        cta_freq = dna.get("cta_frequency", {})
        top_cta = list(cta_freq.keys())[0] if cta_freq else "Learn More"
        power_words = list(dna.get("power_words_used", {}).keys())[:5]

        # Use actual ad copies as templates
        sample_copies = [a.get("primary_text", "") for a in self.ads if len(a.get("primary_text", "")) > 20][:5]

        product = product_name or self.brand_info.get("matched_brand", "Your Product")
        desc = product_desc or "our product"
        audience = target_audience or "your audience"

        rewrites = []

        # Rewrite 1: Mirror the dominant hook style
        if hook_type == "Question":
            hooks = [
                f"Still looking for the perfect {desc}?",
                f"What if {desc} could change your {audience}'s experience?",
                f"Ready to discover what makes {product} different?",
            ]
        elif hook_type == "Command":
            hooks = [
                f"Discover the {product} difference.",
                f"Get {desc} that actually delivers.",
                f"Start your journey with {product} today.",
            ]
        elif hook_type == "Exclamation":
            hooks = [
                f"The wait is over! {product} is here.",
                f"Game-changer alert! Meet {product}.",
                f"This changes everything! Introducing {product}.",
            ]
        else:
            hooks = [
                f"{product} brings you {desc} like never before.",
                f"Elevate your style with {product}.",
                f"Meet the all-new {product} collection.",
            ]

        # Rewrite templates based on copy formula
        templates = {
            "PAS (Problem-Agitate-Solve)": [
                "{hook}\n\nTired of {problem}? You're not alone.\n\nThat's why we created {product} - {solution}.\n\n{cta_text}",
                "{hook}\n\nWe know the struggle of {problem}.\n\n{product} is built to solve exactly that. {solution}.\n\n{cta_text}",
            ],
            "AIDA (Attention-Interest-Desire-Action)": [
                "{hook}\n\n{benefit}. Built for {audience} who demand more.\n\n{cta_text}",
                "{hook}\n\nExperience {product} - where {benefit} meets {value}.\n\n{cta_text}",
            ],
            "BAB (Before-After-Bridge)": [
                "{hook}\n\nBefore: {problem}.\nAfter: {solution}.\n\nThe bridge? {product}.\n\n{cta_text}",
                "{hook}\n\nImagine going from {problem} to {solution}. {product} makes it happen.\n\n{cta_text}",
            ],
            "Direct Offer": [
                "{hook}\n\n{offer}. Don't miss out.\n\n{cta_text}",
                "{hook}\n\nFor a limited time: {offer}.\n\n{cta_text}",
            ],
            "Storytelling": [
                "{hook}\n\nEvery {product} has a story. Yours starts here.\n\n{solution}.\n\n{cta_text}",
                "{hook}\n\nThis isn't just {desc} - it's a statement. {benefit}.\n\n{cta_text}",
            ],
        }

        formula_templates = templates.get(formula, templates["AIDA (Attention-Interest-Desire-Action)"])
        emoji_suffix = " \U0001F525" if uses_emoji else ""

        for i, hook in enumerate(hooks):
            for j, tmpl in enumerate(formula_templates):
                text = tmpl.format(
                    hook=hook,
                    product=product,
                    problem=f"settling for less",
                    solution=f"quality {desc} designed for you",
                    benefit=f"style, performance, and innovation",
                    value=f"unbeatable quality",
                    audience=audience,
                    offer=f"exclusive access to {product}",
                    desc=desc,
                    cta_text=f"{top_cta} \u2192{emoji_suffix}",
                )
                rewrites.append({
                    "version": f"V{len(rewrites)+1}",
                    "hook_style": hook_type,
                    "formula": formula,
                    "tone": tone,
                    "cta": top_cta,
                    "text": text,
                    "word_count": len(text.split()),
                    "matches_dna": True,
                })

            if len(rewrites) >= 6:
                break

        return rewrites[:6]

    # ------------------------------------------------------------------
    # Enrich all ads
    # ------------------------------------------------------------------

    def enrich_ads(self):
        for ad in self.ads:
            text = ad.get("primary_text", "")
            ad["copy_breakdown"] = self.analyze_copy(text)
            ad["angle"] = self.detect_angle(text)
            ad["funnel_stage"] = self.detect_funnel_stage(ad)

    # ------------------------------------------------------------------
    # Full research pipeline
    # ------------------------------------------------------------------

    async def research(self, query: str, country: str = "ALL", use_gemini: bool = False):
        """Execute the full research pipeline."""
        self.gemini_copy_dna = {}
        self.gemini_creative_dna = {}
        self.image_analyses = []

        await self.launch()
        try:
            print(f"\n[1/8] Opening Ad Library for '{query}'...")
            await self.navigate_to_ad_library(query, country)

            print("[2/8] Identifying brand...")
            brand = await self.identify_brand(query)
            print(f"       Brand: {brand['matched_brand']}")
            print(f"       Total results: {brand['total_results']}")

            print(f"[3/8] Scrolling & collecting ads ({self.scroll_rounds} rounds)...")
            raw_text = await self.scroll_and_collect()

            print("[4/8] Extracting images...")
            saved_images = await self.extract_images()
            print(f"       Saved {len(saved_images)} images")

            print("[5/8] Parsing ad cards...")
            self.parse_ads(raw_text)
            self.assign_images_to_ads(saved_images)
            print(f"       Parsed {len(self.ads)} ads")

            print("[6/8] Analyzing copy, angles & funnels...")
            self.enrich_ads()

            print("[7/8] Building Copy DNA & Creative DNA (rule-based)...")
            self.analyze_copy_dna()
            self.analyze_creative_dna()

            if use_gemini:
                print("[8/8] Running Gemini AI deep analysis...")
                try:
                    from .gemini_engine import GeminiEngine
                    import time as _time
                    gemini = GeminiEngine()

                    # Filter: only analyze ads that have actual copy (skip disclaimers/empty)
                    analyzable = [a for a in self.ads if len(a.get("primary_text", "")) > 30]

                    # Deduplicate by primary_text to avoid analyzing the same copy multiple times
                    seen_texts = set()
                    unique_ads = []
                    for a in analyzable:
                        txt_key = a.get("primary_text", "")[:100]
                        if txt_key not in seen_texts:
                            seen_texts.add(txt_key)
                            unique_ads.append(a)

                    total_to_analyze = len(unique_ads)
                    print(f"       {len(self.ads)} total ads, {len(analyzable)} with copy, {total_to_analyze} unique")
                    print(f"       Running full Creative DNA Breakdown on ALL {total_to_analyze} unique ads...")

                    # Process ALL unique ads in batches of 5 with small delay
                    for i, ad in enumerate(unique_ads):
                        img_file = ad.get("image_file", "")
                        img_path = os.path.join(self.images_dir, img_file) if img_file else None
                        if img_path and not os.path.exists(img_path):
                            img_path = None
                        try:
                            breakdown = gemini.full_ad_breakdown(ad, img_path)
                            ad["full_breakdown"] = breakdown
                            if breakdown.get("visual_breakdown"):
                                self.image_analyses.append(breakdown["visual_breakdown"])
                            print(f"         Ad {i+1}/{total_to_analyze} done")
                        except Exception as e:
                            print(f"         Ad {i+1}/{total_to_analyze} failed: {e}")
                            ad["full_breakdown"] = {"error": str(e)}

                        # Small delay every 5 ads to avoid rate limits
                        if (i + 1) % 5 == 0 and i + 1 < total_to_analyze:
                            print(f"         Pausing 2s to avoid rate limits...")
                            _time.sleep(2)

                    # Copy the breakdown to duplicate ads that share the same copy
                    breakdown_cache = {}
                    for a in self.ads:
                        if a.get("full_breakdown") and "error" not in a.get("full_breakdown", {}):
                            key = a.get("primary_text", "")[:100]
                            breakdown_cache[key] = a["full_breakdown"]
                    for a in self.ads:
                        if not a.get("full_breakdown"):
                            key = a.get("primary_text", "")[:100]
                            if key in breakdown_cache:
                                a["full_breakdown"] = breakdown_cache[key]

                    # AI Copy DNA across all ads
                    print("       Analyzing copy DNA with Gemini...")
                    self.gemini_copy_dna = gemini.analyze_copy_dna(self.ads)

                    # AI Creative DNA from visual breakdowns
                    if self.image_analyses:
                        print("       Building creative DNA with Gemini...")
                        self.gemini_creative_dna = gemini.analyze_creative_dna(self.image_analyses)

                    analyzed_count = sum(1 for a in self.ads if a.get("full_breakdown") and "error" not in a.get("full_breakdown", {}))
                    print(f"       Gemini analysis complete. {analyzed_count}/{len(self.ads)} ads fully analyzed.")
                except Exception as e:
                    print(f"       Gemini error (falling back to rule-based): {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("[8/8] Skipping Gemini (set GEMINI_API_KEY to enable).")

            print("       Done.\n")
            return self.ads
        finally:
            await self.close()
