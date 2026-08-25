"""Final grouped-connection UI polish for HA Remote Bridge."""

from ui_shell_v6 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

# Group cards remain stacked containers in list mode rather than inheriting the
# older two-column single-resource card layout.
INDEX_HTML = INDEX_HTML.replace(
    "    .device-grid.list .device-card { display:grid; grid-template-columns:minmax(220px,1fr) auto; }",
    "    .device-grid.list .device-card { display:grid; grid-template-columns:minmax(220px,1fr) auto; }\n"
    "    .device-grid.list .connection-group-card { display:block; }",
)

# Let the global search match the friendly Group / Host name too.
INDEX_HTML = INDEX_HTML.replace(
    "const text=(r.name+' '+r.url+' '+kind).toLowerCase();",
    "const text=(r.name+' '+(r.group_name||'')+' '+r.url+' '+kind).toLowerCase();",
)
