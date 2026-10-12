# Version 0.2.1

Fix Categories search layout: the expanding TextField was inside a wrapping Row, where Flutter cannot apply its flex sizing normally. It now uses a non-wrapping Row and a bounded single-line field. Category and dictionary text columns fit their contents. All learning content, storage keys, scores, and trophies remain unchanged. Rendered Safari UI has not been verified here.
