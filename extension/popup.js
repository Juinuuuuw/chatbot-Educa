const status = document.getElementById('status');
let acting=false;
let activationError='';
let restoredMode=false;
async function render() {
  const s = await chrome.runtime.sendMessage({type:'status'});
  if(!restoredMode) {document.getElementById('self').checked=!!s.self;restoredMode=true;}
  status.textContent = `${s.enabled ? 'Ativo' : 'Pausado'}\n${s.label || 'Nenhuma conversa autorizada'}\n${activationError || s.lastStatus || ''}`;
}
document.getElementById('start').onclick = async () => {
  const b=document.getElementById('start'); b.disabled=true;acting=true;activationError='';status.textContent='Ativando…';
  try {
    const r=await chrome.runtime.sendMessage({type:'start',self:document.getElementById('self').checked});
    if (!r.ok) throw new Error(r.error);
    await render();
  } catch(e) {activationError=e.message;status.textContent=e.message;} finally {b.disabled=false;acting=false;}
};
document.getElementById('stop').onclick = async () => {activationError='';await chrome.runtime.sendMessage({type:'stop'});await render();};
render().catch(e=>status.textContent=e.message);
setInterval(()=>{if(!acting)render().catch(()=>{});},1500);
