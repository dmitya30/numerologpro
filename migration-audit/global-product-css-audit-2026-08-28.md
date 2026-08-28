# Global product CSS consolidation - 28.08.2026

Source checkpoint: `ea58e93be2121d56a1a4cda79c27bc705e70ab96`.

## Read-only classification

- The normalized global prefixes of all three product-specific stylesheets were identical.
- Each prefix defined 27 custom properties; 21 had no reference in the effective product bundle.
- Six to eight simple element selector branches per page referenced tags absent from that page.
- Each prefix contained an empty `max-width: 720px` media block.
- Active layout, typography, focus and light-theme normalization rules require preservation.

## Consolidation checkpoint

- The identical prefix was moved once to `assets/css/products.css`.
- Product-specific stylesheets now begin with their actual product wrapper selector.
- Normalized effective CSS was compared before and after for every product and remained identical.
- Shared CSS cache version changed from `v=4` to `v=5`.
- Product-specific CSS cache versions changed from `v=3` to `v=4`.

## Deferred cleanup

- Unused custom properties, absent element branches, empty media blocks and historical comments were not removed in this checkpoint.
- Their deletion requires a separate patch followed by visual QA.
