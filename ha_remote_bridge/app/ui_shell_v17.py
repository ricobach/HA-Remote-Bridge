"""Proxy-safe session reload handling for HA Remote Bridge 0.4.12."""

from ui_shell_v16 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

OLD_NAVIGATE = "function navigate(kind){const s=currentSession();if(!s)return;try{if(kind==='back')s.frame.contentWindow.history.back();if(kind==='forward')s.frame.contentWindow.history.forward();if(kind==='reload')s.frame.contentWindow.location.reload();}catch(_){if(kind==='reload')s.frame.src=s.frame.src;}}"

NEW_NAVIGATE = """function navigate(kind){
    const s=currentSession();if(!s)return;
    try{
      if(kind==='back'){s.frame.contentWindow.history.back();return;}
      if(kind==='forward'){s.frame.contentWindow.history.forward();return;}
      if(kind==='reload'){
        const resource=s.resource||{};
        const rk=resourceKind(resource);
        // Web SPAs (notably RutOS) can replace iframe history with a synthetic
        // root-relative route. Browser-native location.reload() then reloads
        // that synthetic Ingress URL and can forward the HA proxy path to the
        // upstream device. Re-enter Web/ESPHome sessions through the canonical
        // configured bridge URL instead. Other session types retain native
        // reload semantics so SMB folder state and terminal/viewer state are
        // not unnecessarily reset.
        if(rk==='http'||rk==='https'||rk==='esphome'){
          const base=sessionUrl(resource);
          const sep=base.includes('?')?'&':'?';
          s.frame.src=base+sep+'_hrb_reload='+Date.now();
        }else{
          s.frame.contentWindow.location.reload();
        }
      }
    }catch(_){
      if(kind==='reload'){
        try{s.frame.src=sessionUrl(s.resource);}catch(__){s.frame.src=s.frame.src;}
      }
    }
  }"""

if OLD_NAVIGATE not in INDEX_HTML:
    raise RuntimeError("Proxy-safe reload UI composition failed: navigate() signature changed")

INDEX_HTML = INDEX_HTML.replace(OLD_NAVIGATE, NEW_NAVIGATE, 1)

for required in ("_hrb_reload=", "sessionUrl(resource)", "rk==='http'||rk==='https'||rk==='esphome'"):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Proxy-safe reload UI composition failed: missing {required}")
