# Version 0.2.2

- Move scrolling from the centered application Column to the page's viewport. A single scrollbar is explicitly placed at the window's right edge.
- Give every content Column minimum-height sizing, including colored selection panels. Inner screens no longer have expanding vertical Columns in the scrolling page.
- Categories uses bounded-height responsive search and filter controls. Phone layouts stack category and dictionary details/actions; wider layouts keep compact rows.
- Recalculate content width on every viewport size change, including resizing within the same desktop/phone breakpoint. Dialogs fit shorter viewports and narrow fields stay within available space.
- Learning content, storage keys, question memberships and trophy fingerprints are unchanged.

The automated checks validate mounting, serialization and layout constraints at phone, tablet, laptop and wide desktop sizes. The attempted local browser preview timed out; rendered Safari/browser UI verification remains outstanding.

Verification: Python compilation and all 107 tests pass. Layout checks cover 320×568, 390×844, 768×1024, 1024×768, 1440×900 and 1920×1080 viewports, plus resizing during practice. The static build and packaged runtime dependency/source checks pass.
