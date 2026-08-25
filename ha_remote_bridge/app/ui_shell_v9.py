"""Final SSH editor control styling for HA Remote Bridge."""

from ui_shell_v8 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

INDEX_HTML = INDEX_HTML.replace(
    "    #ssh-dialog input, #ssh-dialog select { width:100%; max-width:100%; }",
    "    #ssh-dialog input, #ssh-dialog select { width:100%; max-width:100%; }\n"
    "    #ssh-dialog input[type=number], #ssh-dialog select { min-height:36px; padding:7px 9px; border:1px solid var(--border); border-radius:4px; background:var(--surface); color:var(--text); }\n"
    "    #ssh-dialog select { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
)
