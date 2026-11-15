# Faction heraldry

## Scope and provenance

The rendering set contains exactly ten current faction IDs: `gilneas`, `greymane`, `crowley`, `silverlaine`, `godfrey`, `ashbury`, `marley`, `walden`, `dalaran`, and `lordaeron`.

The atlas phase is human Gilneas after the Second War, while it is still in the Alliance and before secession, the wall, and the worgen curse. Historical scenes in a later short story are usable evidence for the earlier court; the story's later shipwreck, secret hunts and transformed characters are not early heraldry evidence.

**Only Dalaran and Lordaeron are `canonical-stylized`: their identifying device is taken from a retrieved canonical-art source, but its silver finish and placement in the atlas shield are author treatment.** The seven noble houses are `author` designs, not discovered coats of arms. Gilneas is the existing, user-supplied `author` PNG, unchanged—not a redraw or an invented canonical attribution.

No asset establishes a new title, private estate, border, court appointment, curse, undead allegiance or RPG-derived identity. Evidence limits stay in this documentation and the JSON records, not in immersive UI labels.

## Per-faction basis

- **Gilneas:** existing `assets/ui/gilneas-royal-symbol.png`. Its bytes are preserved. The royal field remains `#131516`, while the faction/marker color remains `#9aa8b6`. This is supplied artwork, not a historical-canon claim.
- **Greymane:** crown above three short rain strokes. The early council scene supports the ruling family's continuity and Genn's appeal to his father's rule.[7] The crown and rain are invented devices; rain is not lifted from the story's later Cataclysm sea scenes.
- **Crowley:** fir above crossed arms. The Second-War account names Pyrewood and Ambermill as Crowley's holdings and depicts his advocacy of common aid.[3][7] Tree/arms imagery is author interpretation; it is not a later rebellion or liberation-front mark.
- **Silverlaine:** crenellated gate-tower with an open arch. The Adventure Guide states that Silverlaine was master of the keep before Arugal's takeover.[6] The tower is invented heraldry; that retrospective statement does not independently establish the pre-wall title date or a primary-source Crowley vassal chain.
- **Godfrey:** upright military blade over paired guard blades. The early council scene explicitly calls him commander of the standing militia.[7] The motif does not carry later pistols, undead imagery or a claim to the seized keep.
- **Ashbury:** trefoil-bowed court key. The early scene describes friendship with Genn and Archibald's trust in the Ashburys' fidelity to the crown.[7] A key does not claim a named hereditary office or an early eastern estate.
- **Marley:** north-pointing spear/compass with paired boundary marks. His domain is considered in the postwar wall-planning scene.[5][7] The north-facing motif is interpretation, not an assignment of Ambermill, Deep Elem, exact boundaries, a fort or a royal title.
- **Walden:** anchor with a short wave. The biography describes eastern origin; a Cataclysm quest, much later than this map phase, names a Walden house near the shore.[10][11] The asset is explicitly scenario-designed. Those later sources do not prove a pre-wall coastal title, private ownership, fleet or council seat.
- **Dalaran:** the actual Warcraft II eye, with its detached upper arch, central eye, lower band and three separate downward rays. Wowpedia's File page attributes the banner to Chris Metzen and the Warcraft II manuals, pages 44/42.[15] The Kirin Tor article identifies its insignia as an eye.[2] The silver vector retains that topology and does not use the separately scoped Warcraft-film Eye or the uncertain-authorship 64px wiki template icon.
- **Lordaeron:** actual central L-and-sword from the retrieved crest, excluding the enclosing shield, lion, hammer and crossed outside weapons. The File page identifies it as the Icon of Courage and a Warcraft III wallpaper; the article captions that image as the crest of Lordaeron.[13][1] The actual Warcraft II Lordaeron banner, attributed to Samwise Didier and manual pages 42/40, is retained as an early-sigil cross-check.[8] The source silhouette—not a font L—is traced and reduced for small-display clarity.

## Retrieval record

Wowpedia's article browser surfaces returned a challenge/403 for several requests. The live MediaWiki API succeeded: `action=parse` retrieved each selected File page's attribution and HTML/wikitext; `prop=imageinfo` returned the actual download URL, original dimensions, MIME, size and SHA-1. No image URL was guessed.

Selected source records:

| Use | Retrieved File page | Exact source bytes retained in scratch |
|---|---|---|
| Lordaeron main crest | `File:Human_Crest.jpg` | `heraldry-source-lordaeron-crest-original.jpg` |
| Lordaeron early cross-check | `File:Lordaeron-flag.jpg` | `heraldry-source-lordaeron-original.jpg` |
| Dalaran early eye | `File:Dalaran-flag.jpg` | `heraldry-source-dalaran-wc2-original.jpg` |
| Kirin Tor in-game eye cross-check | `File:Kirin_Tor_banner.jpg` | `heraldry-source-kirin-tor-banner-original.jpg` |

All scratch paths are beneath `/Users/daniil_si/.hermes/cache/scratch/gilneas-court/`. Each delivered source has a `.retrieval.json` sidecar containing the exact requested/final URL, HTTP status, actual Content-Type, SHA-256 and MediaWiki-original SHA-1. The CDN negotiated **WebP** while retaining `.jpg`/`.png` URL names. Delivered bytes remain untouched; `*-decoded.png` previews are separate, pixel-preserving decodes. The CDN-rendered SHA-1 must not be represented as matching the MediaWiki original-JPEG SHA-1.

- Lordaeron delivered crest SHA-256: `2131c72b8e387d5509d5e4127b49add0960c7dd53c14129e575ff13c86cdc8ef`.
- Dalaran delivered Warcraft II source SHA-256: `e9d3510b1fc3be672c3552d4fbdaa63eddb8250f54d695497bb27b23a3b15f8d`.
- Unchanged Gilneas PNG SHA-256: `0aaeb453e3475503e9260f33b5dce1158bc087138a01cf07e7018f2b2d9798c3`.

The external art remains its credited creators'/Blizzard's property; `canonical-stylized` describes visual provenance, not newly official arms or an expanded reuse license.

The stock citation verifier truncates closing parentheses in two real wiki URLs. The mechanically generated Sources block keeps the exact retrieved URLs; task-local verification uses a parentheses-aware URL parser in memory, checks every source mapping against the ledger, and retains all attached verbatim quotes. No ledger IDs or source URLs were changed to appease that parser.

## Parent integration contract

`docs/faction-heraldry.json` contains `{factions:[{id,heraldry,origin,note,sourceUrls,sourceFiles,...}],assets:[...]}`. Copy each record's **`heraldry` only** onto its matching faction. `fieldColor` is a preservation assertion, not a change payload. Add the nine new symbol files to the parent-owned runtime export manifest. The existing root PNG is already a runtime asset.

- Every `heraldry.symbol` is a nonempty literal string; optional colors are exact `#RRGGBB`, and `origin`/`note` are strings.
- Nonroot shield fields always use their immediate faction's existing color. No house `field` override is supplied.
- For exact root ID `gilneas`, existing `meta.gilneasHeraldry` remains authoritative, including custom author symbol, field, edge and device. A new default faction record must not overwrite that metadata at migration.
- Direct `faction.heraldry.symbol` is the primary nonroot image source. Unknown/new factions with no record stay plain on their own field.
- Explicit invalid symbols fail plain: no alternate root/parent crest replaces an author's rejected URL.
- The sole compatibility fallback applies to known historical Gilnean IDs in an unmigrated snapshot containing no direct heraldry records. Cycle and missing-parent guards prevent unsafe ancestor traversal.
- URLs are assigned only to an SVG `<image href>` after validation. No image markup is inserted with `innerHTML`, no source is evaluated, and standalone SVG assets contain no scripts, active elements or external references.

## Visual and test verification

Shared geometry is exactly `M1 1H59V46.4L30 71 1 46.4Z`, `viewBox="0 0 60 72"`; each image occupies `x=10`, `y=8`, `width=40`, `height=44`. All fields remain exact, with `#65707b` rim and `#9aa8b6` silver-device treatment. There are no banner poles, cloth, white cards or alternate shield silhouettes.

`tests/court-heraldry.test.mjs` was built through observed red→green behavior slices, including direct custom devices, no borrowing, independent foreign crests, invalid URLs, root custom metadata, cycle/missing-parent guards, all-ten manifest and source-image hash preservation. Actual browser verification uses the real module and `royal-windows.css`, a scratch-only merged fixture, live HTTP at `/` and `/gilneas-atlas/`, and all dossier/object/noble sizes. It checks ten decoded images, exact SVG attributes, script-shaped URL failures, an actual external SVG script remaining inert in image context, and zero HTTP/page/console errors. Pillow rereads all ten real-render screenshots. Source-image and final-screen vision inspections are separate evidence, not fabricated previews.

Scratch verification artifacts: `heraldry-preview.html`, `heraldry-verify-visual.py`, `heraldry-visual-results.json`, `heraldry-review-desktop.png`, `heraldry-review-portrait-subpath.png`, `heraldry-contact-sheet.png`, and ten `heraldry-render-<id>.png` files.

This child task does not edit the publication data, model, parent UI or export manifest. Full production migration is parent-owned; success of the scratch merged fixture is not a claim that the unmodified data has already adopted these records.

## Sources

[1] https://wowpedia.fandom.com/wiki/Lordaeron_(kingdom)
[2] https://wowpedia.fandom.com/wiki/Kirin_Tor
[3] https://wowpedia.fandom.com/wiki/Darius_Crowley
[5] https://wowpedia.fandom.com/wiki/Lord_Marley
[6] https://wowpedia.fandom.com/wiki/Baron_Silverlaine
[7] https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack
[8] https://wowpedia.fandom.com/wiki/File:Lordaeron-flag.jpg
[10] https://wowpedia.fandom.com/wiki/Lord_Walden
[11] https://wowpedia.fandom.com/wiki/Leader_of_the_Pack_(quest)
[13] https://wowpedia.fandom.com/wiki/File:Human_Crest.jpg
[15] https://wowpedia.fandom.com/wiki/File:Dalaran-flag.jpg
