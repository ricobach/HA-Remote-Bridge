"""Responsive desktop card layout for HA Remote Bridge 0.4.1."""

from ui_shell_v13 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

RESPONSIVE_CARD_CSS = r'''
    /* 0.4.1: use the available desktop width instead of forcing a narrow list. */
    @media (min-width: 900px) {
      .home { max-width:1680px; padding-left:20px; padding-right:20px; }
      .device-grid { grid-template-columns:repeat(auto-fill,minmax(330px,1fr)) !important; gap:12px !important; align-items:start; }
      .device-grid.list { grid-template-columns:1fr !important; }
      .device-card.connection-group-card { height:auto; min-width:0; }
      .connection-row { grid-template-columns:32px minmax(0,1fr) auto; padding:10px 11px; gap:9px; }
      .connection-actions .mini-button.primary { min-width:58px; }
    }

    @media (min-width: 1300px) {
      .home { max-width:1800px; }
      .device-grid { grid-template-columns:repeat(auto-fill,minmax(360px,1fr)) !important; gap:14px !important; }
    }

    @media (min-width: 1750px) {
      .device-grid { grid-template-columns:repeat(auto-fill,minmax(390px,1fr)) !important; }
    }

    @media (max-width:899px) {
      .device-grid,.device-grid.list { grid-template-columns:1fr !important; }
    }
'''

INDEX_HTML = INDEX_HTML.replace("  </style>", RESPONSIVE_CARD_CSS + "\n  </style>", 1)

if "minmax(330px,1fr)" not in INDEX_HTML or "max-width:1680px" not in INDEX_HTML:
    raise RuntimeError("Responsive desktop card layout composition failed")
