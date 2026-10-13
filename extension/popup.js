const status = document.getElementById('status');
let acting=false;
let activationError='';
let restoredMode=false;
async function render() {
  const s = await chrome.runtime.sendMessage({type:'status'});
  const panel = await chrome.storage.local.get(['panelEnabled','panelAuto','panelError','panelContacts']);
  document.getElementById('panel-status').textContent = `${panel.panelEnabled?(panel.panelAuto?'Conectado a todas as conversas individuais':'Conectado em seleção manual'):'Pausado'} · ${Object.keys(panel.panelContacts||{}).length} conversa(s) no painel${panel.panelError?'\n'+panel.panelError:''}`;
  if(!restoredMode) {document.getElementById('self').checked=!!s.self;restoredMode=true;}
  status.textContent = `${s.enabled ? 'Ativo' : 'Pausado'}\n${s.label || 'Nenhuma conversa autorizada'}\n${activationError || s.lastStatus || ''}`;
  if(panel.panelEnabled)status.textContent='Modo painel ativo. Use o painel para assumir conversas e responder.';
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
for(const type of ['panel-start','panel-add','panel-open','panel-stop'])document.getElementById(type).onclick=async()=>{
  const button=document.getElementById(type);button.disabled=true;
  try {const r=await chrome.runtime.sendMessage({type});if(!r.ok)throw new Error(r.error);document.getElementById('panel-status').textContent=type==='panel-stop'?'Conexão pausada.': 'Painel pronto.';}
  catch(e){document.getElementById('panel-status').textContent=e.message;}
  finally{button.disabled=false;}
};
