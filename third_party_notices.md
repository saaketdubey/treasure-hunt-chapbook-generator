# Third-party notices

This repository bundles font files and cached map data from other projects. Each is listed below with its copyright holder, source and licence. The project's own code is licensed separately; see `LICENSE`.

## Fonts

All six font files in `chapbook_skill/assets/fonts/` are licensed under the SIL Open Font License, Version 1.1 (OFL). The full licence text is in `licenses/ofl_1.1.txt` and at https://openfontlicense.org/open-font-license-official-text/. The files are unmodified upstream builds; only the filenames differ from the upstream releases. Each file also carries its copyright and licence in its embedded metadata.

| File | Font | Version | Copyright | Upstream |
| --- | --- | --- | --- | --- |
| `Cormorant.ttf` | Cormorant Light | 4.000 | Copyright 2015 The Cormorant Project Authors | https://github.com/CatharsisFonts/Cormorant |
| `CormorantItalic.ttf` | Cormorant Light Italic | 4.000 | Copyright 2015 The Cormorant Project Authors | https://github.com/CatharsisFonts/Cormorant |
| `EBGaramond.ttf` | EB Garamond Regular | 1.003 | Copyright 2017 The EB Garamond Project Authors | https://github.com/octaviopardo/EBGaramond12 |
| `EBGaramondItalic.ttf` | EB Garamond Italic | 1.003 | Copyright 2017 The EB Garamond Project Authors | https://github.com/octaviopardo/EBGaramond12 |
| `SourceSerif.ttf` | Source Serif 4 Regular | 4.004 | © 2014–2021 Adobe Systems Incorporated, with Reserved Font Name "Source" | https://github.com/adobe-fonts/source-serif |
| `SourceSerifItalic.ttf` | Source Serif 4 Italic | 4.004 | © 2014–2021 Adobe Systems Incorporated, with Reserved Font Name "Source" | https://github.com/adobe-fonts/source-serif |

Upstream licence files: [Cormorant OFL.txt](https://github.com/CatharsisFonts/Cormorant/blob/master/OFL.txt), [EB Garamond OFL.txt](https://github.com/octaviopardo/EBGaramond12/blob/master/OFL.txt), [Source Serif LICENSE.md](https://github.com/adobe-fonts/source-serif/blob/release/LICENSE.md).

Under the OFL, the fonts may not be sold on their own, and any modified version must not use the Reserved Font Names. Documents produced with the fonts are not subject to the OFL.

## OpenStreetMap data

The `map_tests/*/data/` folders contain extracts of OpenStreetMap data (`*.osm.gz`) cached so that each test map can be rebuilt exactly. The maps themselves are drawn from this data.

- Data © OpenStreetMap contributors
- Licence: Open Database License (ODbL) 1.0, https://opendatacommons.org/licenses/odbl/1-0/
- Copyright and attribution: https://www.openstreetmap.org/copyright
- Attribution guidance followed: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines

Every generated map prints "Map data © OpenStreetMap contributors, ODbL · openstreetmap.org/copyright" in its corner. Each data folder's `manifest.json` records the source, licence and attribution alongside the file hashes.

## Python dependencies

The scripts use reportlab, Pillow and shapely, which are not bundled here. Install them from PyPI; each carries its own licence.
