# Discoverability, attribution, and launch measurement

This is the owner-operated visibility runbook for Irrevon. It prepares the
repository and static site for search, answer engines, launch attribution, and
measurement without claiming that metadata guarantees crawling, ranking, rich
results, citations, or adoption.

The machine-readable page-intent map is
[`site/search-intents.json`](../site/search-intents.json). Metric definitions are
in [`discoverability-metrics.json`](discoverability-metrics.json).

## What current primary guidance actually says

- Google applies ordinary search requirements to AI Overviews and AI Mode. There
  is no additional “AEO” schema, AI markup, or required AI text file. Important
  content should be crawlable, internally linked, visible as text, useful, and
  accurately represented by structured data. [Google: AI features and your
  website](https://developers.google.com/search/docs/appearance/ai-features)
- Structured data must describe visible, current content. It enables
  eligibility, never a display or ranking guarantee. [Google structured-data
  guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
- `lastmod` is useful only when it represents a significant content change.
  Google ignores sitemap `priority` and `changefreq`. [Google sitemap
  guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- `OAI-SearchBot` supports ChatGPT Search discovery and is separate from
  `GPTBot`, which may collect for foundation-model training. [OpenAI publisher
  guidance](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)
- `PerplexityBot` supports search/link surfacing and is not a foundation-model
  training crawler. User-triggered fetchers may not follow robots policy.
  [Perplexity crawler documentation](https://docs.perplexity.ai/docs/resources/perplexity-crawlers)
- IndexNow notifies participating engines that canonical URLs changed. A receipt
  is not proof of crawling or indexing. [IndexNow
  protocol](https://www.indexnow.org/documentation)
- Vercel Web Analytics is cookie-free aggregated measurement, but it is still
  Vercel-processed telemetry. Custom events require Pro or Enterprise; the UTM
  dashboard requires Web Analytics Plus or Enterprise. [Vercel analytics
  plans](https://vercel.com/docs/analytics/limits-and-pricing) and [privacy
  details](https://vercel.com/docs/analytics/privacy-policy)
- GitHub repository traffic exposes only the previous 14 days. Views/clones,
  popular content, and referrers therefore need an owner-controlled retention
  process if longitudinal data matters. [GitHub traffic
  documentation](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository)

`site/public/llms.txt` is an optional navigation index. It is not a ranking
control, crawler policy, licensing control, or requirement for Google or answer
engines.

## Crawler and indexing policy

Generated `robots.txt`:

- explicitly allows `OAI-SearchBot` and `PerplexityBot`;
- disallows `GPTBot`, `Google-Extended`, and `CCBot`;
- allows the wildcard group, which includes Googlebot, Bingbot, and ordinary
  crawlers; and
- names the canonical sitemap index.

This is a voluntary crawl preference, not access control and not an amendment to
Apache-2.0. Public content remains public. Do not enable a blanket Vercel
“deny AI bots” rule: that category can combine search, training, and
user-triggered fetchers. If a WAF is later used, verify vendor user agents
against current vendor-published IP ranges rather than trusting a spoofable
header alone.

`/docs/search/` is `noindex,follow` and absent from the sitemap because it is an
internal result surface. `/404.html` is `noindex,nofollow`. Canonical
documentation, public policy pages, guides, and research notes remain
indexable. Canonicals always omit campaign/query parameters.

## Search Console and Bing Webmaster setup

These are external owner actions. Do not automate them in CI.

1. Choose the durable production HTTPS host. Avoid deliberately indexing a
   preview host immediately before a domain migration.
2. In Google Search Console, prefer DNS verification of a Domain property. If
   that is unavailable, set `GOOGLE_SITE_VERIFICATION` only in the protected
   production build environment; the value appears only on the home page.
3. In Bing Webmaster Tools, verify the same host. If using its meta method, set
   `BING_SITE_VERIFICATION` only in the protected production build environment.
4. Submit `https://<host>/sitemap-index.xml` once to each tool.
5. Inspect the home, install, benchmark, one guide, one reference document, and
   any future video watch page. Confirm final 200 status, selected canonical,
   rendered HTML, mobile rendering, and structured data.
6. Monitor Page Indexing, sitemaps, Core Web Vitals, crawl errors, and security
   reports. Use Google's Generative AI report only if it is available for the
   property; otherwise AI-feature traffic remains within ordinary Search
   reporting.
7. In Bing, separately track submitted, crawled, and indexed state. They are not
   interchangeable.

Preview deployments should remain access-protected or explicitly `noindex`.
Canonical-to-production is only a hint and does not reliably deindex a preview.
When Vercel builds with `VERCEL_ENV` set to any value other than
`production`, every HTML page emits `noindex,nofollow` and that deployment's
`robots.txt` disallows all crawling. Local validation builds retain the
production policy so the generated search surface can be tested before deploy.

## IndexNow after an owner-controlled deployment

Set `INDEXNOW_KEY` in the protected production build environment. The build then
emits `/indexnow-key.txt`; no value exists in the source tree. The key is
low-sensitivity ownership proof, but it should not appear in commits or logs.

Dry-run an initial launch from the built canonical sitemap:

```bash
python3 scripts/indexnow.py \
  --origin https://<production-host> \
  --sitemap site/dist/sitemap-0.xml
```

For later changes, provide canonical URLs one per line:

```bash
python3 scripts/indexnow.py \
  --origin https://<production-host> \
  --sitemap site/dist/sitemap-0.xml \
  --changed /private/path/changed-urls.txt
```

Deleted URLs additionally require the previous canonical sitemap:

```bash
python3 scripts/indexnow.py \
  --origin https://<production-host> \
  --sitemap site/dist/sitemap-0.xml \
  --deleted /private/path/deleted-urls.txt \
  --previous-sitemap /private/path/previous-sitemap-0.xml
```

The tool rejects HTTP, credentials, nondefault ports, foreign/preview variants,
queries, fragments, redirects, assets, noindex pages, noncanonical paths,
unproven deletions, and oversized batches. Network verification and submission
occur only with both `--submit` and an exact host confirmation:

```bash
INDEXNOW_KEY=<deployment-provided-value> python3 scripts/indexnow.py \
  --origin https://<production-host> \
  --sitemap site/dist/sitemap-0.xml \
  --changed /private/path/changed-urls.txt \
  --submit --confirm-host <production-host>
```

The fixed endpoint is `https://api.indexnow.org/indexnow`; a 200/202 receipt is
reported as acceptance, never as indexing.

## Privacy-safe analytics

The default keeps Vercel Web Analytics and Speed Insights and strips **all**
query parameters before pageview telemetry. Visitors can opt out in the site
Privacy page; the choice is stored locally in the browser.

Two build-time feature gates prevent the code from pretending a plan supports
features it does not:

- `SITE_ENABLE_CUSTOM_EVENTS=1` enables the fixed event/placement allowlist.
  Use only after confirming Pro or Enterprise.
- `SITE_ENABLE_UTM_ANALYTICS=1` retains the five validated campaign parameters.
  Use only after confirming Web Analytics Plus or Enterprise and approving the
  taxonomy.

No event may contain effect IDs, stable IDs, API payloads, search text, email,
credentials, raw URLs, referrers, commit hashes, free text, user IDs, or other
high-cardinality values. The only custom property is the fixed `placement`
enum. If custom events are unavailable, links, copy controls, the demo, and all
site navigation remain fully functional without event collection.

## Campaign-link convention

Every value is lowercase and bounded:

```text
utm_source   origin platform: github, x, linkedin, hacker-news, reddit, newsletter, partner
utm_medium   channel class: readme, organic-social, community, email, referral, video
utm_campaign stable launch: oss-launch
utm_content  placement or creative: hero, launch-post, explainer-video, technical-article
utm_term     optional; only a genuine paid/search keyword, never identity or free text
```

Generate links with the tested helper:

```bash
python3 scripts/campaign_url.py https://<production-host>/ \
  --source linkedin --medium organic-social \
  --campaign oss-launch --content explainer-video
```

Recommended launch mappings:

| Surface | source | medium | content |
|---|---|---|---|
| GitHub README | `github` | `readme` | `hero` or `launch-video` |
| X | `x` | `organic-social` | `launch-post` |
| LinkedIn | `linkedin` | `organic-social` | `technical-explainer` |
| Hacker News | `hacker-news` | `community` | `show-hn` |
| Reddit | `reddit` | `community` | `technical-post` |
| Newsletter | `newsletter` | `email` | `launch-edition` |
| Launch video | host platform name | `video` | `explainer-video` |
| Technical article | publisher name | `referral` | `technical-article` |
| Partner link | partner slug | `referral` | agreed fixed placement |

Campaign URLs canonicalize to the clean page URL. Do not append UTMs to outbound
GitHub links; GitHub traffic reports referrer domains, not those campaign
dimensions.

## GitHub discoverability owner checklist

Repository-local requirements already exist: concise README opening, Apache-2.0,
NOTICE, contribution/security policies, release metadata, and `CITATION.cff`.
On the default branch, GitHub will surface “Cite this repository.”

Owner-only settings:

1. Keep the current accurate description and production homepage URL.
2. Add no more than 20 natural lowercase topics. Suggested set:
   `ai-agents`, `agent-reliability`, `distributed-systems`, `reconciliation`,
   `idempotency`, `fault-injection`, `benchmark`, `python`, `postgresql`,
   `durable-execution`, `agent-safety`. Do not add `exactly-once`.
3. Upload a solid-background repository social preview (GitHub recommends
   1280×640, PNG/JPG/GIF, under 1 MB) and inspect its crop.
4. Keep Actions default token permissions read-only, PR approval disabled, and
   enable platform SHA-pin enforcement if available after verifying every
   active workflow.
5. Review whether an empty Wiki should remain enabled. Do not open a new
   feedback/governance channel without an owner policy for moderation.

## Measurement cadence and interpretation

- Daily during launch week: production availability, indexing errors, major
  referrers, launch CTAs if plan-enabled, GitHub views/clones, and security
  alerts.
- Weekly for the first month: branded/non-branded search, landing-page
  conversion, Bing/Google crawl and index state, ChatGPT/Perplexity referrers,
  Core Web Vitals, and campaign comparisons.
- Monthly: content usefulness, adapter/benchmark guide entry, returning
  contributors, dependency/security posture, and whether pages should be
  consolidated rather than multiplied.

GitHub totals can be aggregated by non-overlapping UTC day. Do **not** add
`uniques` across windows; the same visitor may recur. Popular paths/referrers
are top-ten samples, not a complete census. For retention, export the four
traffic endpoints to a private encrypted location at least weekly. A public
same-repository workflow is intentionally not provided: `GITHUB_TOKEN` cannot
request the needed Administration-read permission, and public artifacts are
not private durable storage.

An owner can make that export locally with an authenticated `gh` session whose
fine-grained credential has repository **Administration: read**. Choose an
encrypted directory outside the clone, then run:

```bash
umask 077
export IRREVON_TRAFFIC_DIR=/private/encrypted/irrevon-traffic
mkdir -p "$IRREVON_TRAFFIC_DIR"
IRREVON_TRAFFIC_DATE="$(date -u +%F)"
for IRREVON_TRAFFIC_KIND in views clones paths referrers; do
  gh api "repos/PranavMishra28/irrevon/traffic/$IRREVON_TRAFFIC_KIND" \
    >"$IRREVON_TRAFFIC_DIR/$IRREVON_TRAFFIC_DATE-$IRREVON_TRAFFIC_KIND.json"
done
```

Never commit that directory or its credential. Run often enough that the
14-day source window overlaps; deduplicate date buckets when building a longer
series.

## Video publication gate

Do not add `VideoObject`, a watch page, captions, transcript, or sitemap entry
until the final video passes claim review. When it does, publish a stable
same-origin MP4, thumbnail, WebVTT captions, and visible transcript on a
dedicated watch page. The structured data must match the exact duration,
upload date, title, description, thumbnail, and visible content. Critical
information must remain available as crawlable text.

The current candidate is deliberately not shipped: its exact millisecond
timeline is not present in the recorded artifact, and “where it shines”
prejudges a C2 result before live-provider or confirmatory evidence exists.
