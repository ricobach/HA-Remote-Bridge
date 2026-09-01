"""SSH terminal type selector for HA Remote Bridge."""

from dashboard_virtual_host_persistence import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

TERMINAL_TYPE_JS = r'''
<script>
(function installSSHTerminalTypeUI(){
  const form=document.getElementById('ssh-form');
  const user=document.getElementById('ssh-user');
  if(!form||!user)return;

  const authRow=user.closest('.ssh-auth-row')||user.closest('.two-column');
  if(!authRow)return;

  const terminalLabel=document.createElement('label');
  terminalLabel.textContent='Terminal type';
  const terminal=document.createElement('select');
  terminal.id='ssh-terminal-type';
  for(const [value,label] of [
    ['auto','Current / automatic'],
    ['xterm-256color','xterm-256color'],
    ['xterm','xterm'],
    ['vt100','vt100']
  ]){
    const option=document.createElement('option');
    option.value=value;
    option.textContent=label;
    terminal.appendChild(option);
  }
  terminalLabel.appendChild(terminal);
  authRow.insertAdjacentElement('afterend',terminalLabel);

  const help=document.createElement('div');
  help.className='ssh-password-state';
  help.textContent='Current / automatic keeps the existing terminal behaviour. Use xterm-256color for systems that do not understand tmux-256color, such as some Synology shells.';
  terminalLabel.insertAdjacentElement('afterend',help);

  function terminalType(resource){
    const value=String(resource?.ssh_terminal_type||'auto').toLowerCase();
    return ['auto','xterm-256color','xterm','vt100'].includes(value)?value:'auto';
  }

  const originalShow=window.showSSHResource;
  if(typeof originalShow==='function'){
    window.showSSHResource=function(resource){
      originalShow(resource);
      terminal.value=terminalType(resource);
    };
  }

  terminal.value='auto';
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", TERMINAL_TYPE_JS + "\n</body>", 1)

old_payload = "      ssh_user:user.value,\n      ssh_auth_mode:mode,"
new_payload = "      ssh_user:user.value,\n      ssh_terminal_type:document.getElementById('ssh-terminal-type').value,\n      ssh_auth_mode:mode,"
if old_payload not in INDEX_HTML:
    raise RuntimeError("SSH terminal type composition failed: submit payload changed")
INDEX_HTML = INDEX_HTML.replace(old_payload, new_payload, 1)

for required in (
    "ssh-terminal-type",
    "Current / automatic",
    "xterm-256color",
    "ssh_terminal_type:document.getElementById('ssh-terminal-type').value",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SSH terminal type composition failed: missing {required}")
