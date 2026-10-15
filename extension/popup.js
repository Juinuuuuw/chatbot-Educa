const status = document.getElementById('status');
let acting=false;
let activationError='';
let restoredMode=false;
let panelActionError='';
let panelActing=false;
async function checkApi(){
  const target=document.getElementById('api-status');
  try{const r=await chrome.runtime.sendMessage({type:'api-status'});if(!r?.ok)throw new Error(r?.error||'A API não respondeu.');target.textContent=r.panel===false?'API encontrada, mas esta versão não oferece o painel. Inicie a API da pasta do painel.':'API disponível. Abra o WhatsApp Web e conecte as conversas.';}
  catch(e){target.textContent=e.message;}
}
async function render() {
  const s = await chrome.runtime.sendMessage({type:'status'});
  const panel = await chrome.storage.local.get(['panelEnabled','panelAuto','panelError','panelContacts']);
  document.getElementById('panel-status').textContent = `${panel.panelEnabled?(panel.panelAuto?'Conectado a todas as conversas individuais':'Conectado em seleção manual'):'Pausado'} · ${Object.keys(panel.panelContacts||{}).length} conversa(s) no painel${panel.panelError?'\n'+panel.panelError:''}`;
  if(panelActing)document.getElementById('panel-status').textContent='Conectando… Aguarde a verificação da API e do WhatsApp.';
  else if(panelActionError)document.getElementById('panel-status').textContent=panelActionError;
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
checkApi();setInterval(checkApi,10000);
setInterval(()=>{if(!acting)render().catch(()=>{});},1500);
for(const type of ['panel-start','panel-add','panel-open','panel-stop'])document.getElementById(type).onclick=async()=>{
  if(panelActing)return;
  const button=document.getElementById(type);button.disabled=true;panelActing=true;panelActionError='';
  try {await render();const r=await chrome.runtime.sendMessage({type});if(!r?.ok)throw new Error(r?.error||'A extensão não respondeu. Recarregue a extensão e o WhatsApp Web.');}
  catch(e){panelActionError=e.message;}
  finally{button.disabled=false;panelActing=false;await render().catch(e=>document.getElementById('panel-status').textContent=panelActionError||e.message);}
};
