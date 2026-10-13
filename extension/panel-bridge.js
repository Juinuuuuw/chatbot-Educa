/* Transporte do painel: detecção automática de conversas individuais ou seleção manual. */
let panelBusy=false;
const panelJobs=new Map();
function individualJid(jid) {return typeof jid==='string' && /@(c\.us|lid)$/.test(jid);}
async function panelActive(s) {
  const current=await chrome.storage.local.get(['panelEnabled','panelEpoch']);
  return current.panelEnabled && current.panelEpoch===s.panelEpoch;
}
async function panelStop() {
  await chrome.storage.local.set({panelEnabled:false,panelEpoch:crypto.randomUUID()});
  try {await api('/panel/bridge/connect',{mode:'off'});} catch(e){await chrome.storage.local.set({panelError:errorText(e)});}
}
async function panelStart() {
  await pause('Preparando atendimento automático pelo painel…');
  const epoch=crypto.randomUUID();
  await chrome.storage.local.set({panelEnabled:false,panelEpoch:epoch});
  const tabs=await chrome.tabs.query({active:true,currentWindow:true});
  const tab=tabs[0];
  if(!tab?.url?.startsWith('https://web.whatsapp.com/'))throw new Error('Abra a aba do WhatsApp Web para conectar o painel. Não precisa selecionar uma conversa.');
  await ensure(tab.id);
  const health=await api('/health');
  if(!health.supports_panel_auto)throw new Error('Reinicie a API desta branch antes de conectar todas as conversas.');
  const started=Math.floor(Date.now()/1000);
  const chats=(await page(tab.id,'individuals')).filter(c=>individualJid(c.jid));
  const state=await chrome.storage.local.get('panelContacts');
  const contacts=state.panelContacts || {},markers={},baseline={},readTimes={};
  for(const chat of chats) {
    markers[chat.jid]=chat.marker;
    readTimes[chat.jid]=Date.now();
    // IDs recentes distinguem mensagens antigas enviadas no mesmo segundo da ativação.
    if(!chat.t || chat.t>=started-5) {
      const old=await page(tab.id,'messages',[chat.jid,100]);
      baseline[chat.jid]=old.map(m=>m.id);
      if(contacts[chat.jid])contacts[chat.jid].seen=[...new Set([...contacts[chat.jid].seen,...baseline[chat.jid]])].slice(-2000);
    }
  }
  if((await chrome.storage.local.get('panelEpoch')).panelEpoch!==epoch)throw new Error('Conexão cancelada pela pausa.');
  await api('/panel/bridge/connect',{mode:'all'});
  if((await chrome.storage.local.get('panelEpoch')).panelEpoch!==epoch)throw new Error('Conexão cancelada pela pausa.');
  await chrome.storage.local.set({panelEnabled:true,panelAuto:true,panelStarted:started,panelMarkers:markers,panelReadTimes:readTimes,panelBaseline:baseline,panelTab:tab.id,panelContacts:contacts,panelError:'',lastStatus:'Ativo para novas mensagens de todas as conversas individuais. Grupos excluídos.'});
  await chrome.alarms.create('educa-tick',{periodInMinutes:0.5});
  await panelOpen();
}
async function panelOpen() {
  const {ticket}=await api('/panel/bridge/ticket',{});
  await chrome.tabs.create({url:BASE+'/panel/#ticket='+encodeURIComponent(ticket)});
}
async function panelAdd() {
  const tabs=await chrome.tabs.query({active:true,currentWindow:true});
  const tab=tabs[0];
  if(!tab?.url?.startsWith('https://web.whatsapp.com/'))throw new Error('Abra uma conversa no WhatsApp Web.');
  await ensure(tab.id);
  const chat=await page(tab.id,'active');
  if(!chat || !/@(c\.us|lid)$/.test(chat.jid) || chat.isSelf)throw new Error('Selecione uma conversa individual com outra pessoa.');
  await pause('A conversa será atendida pelo painel.');
  const state=await chrome.storage.local.get('panelContacts');
  const contacts=state.panelContacts || {};
  if(!contacts[chat.jid])contacts[chat.jid]={seen:(await messages(tab.id,chat.jid)).map(m=>m.id),pending:null};
  await api('/panel/bridge/register',{chat:chat.jid,label:chat.label});
  await api('/panel/bridge/connect',{mode:'selected'});
  await chrome.storage.local.set({panelEnabled:true,panelAuto:false,panelTab:tab.id,panelContacts:contacts,lastStatus:'Conversa adicionada ao painel: '+chat.label});
  await chrome.alarms.create('educa-tick',{periodInMinutes:0.5});
  await panelOpen();
}
async function updatePanelContact(jid, mutate) {
  const state=await chrome.storage.local.get('panelContacts');
  const contacts=state.panelContacts || {};
  if(!contacts[jid])return;
  mutate(contacts[jid]);
  await chrome.storage.local.set({panelContacts:contacts});
}
async function discoverPanel(s) {
  const cache=new Map(), discovered=[];
  if(!s.panelAuto)return {cache,discovered};
  const chats=await page(s.panelTab,'individuals');
  for(const chat of chats) {
    if(!individualJid(chat.jid))continue;
    const state=await chrome.storage.local.get(['panelEnabled','panelEpoch','panelContacts','panelMarkers','panelBaseline','panelReadTimes']);
    if(!state.panelEnabled || state.panelEpoch!==s.panelEpoch)break;
    const local=state.panelContacts?.[chat.jid];
    if(!local && chat.marker && state.panelMarkers?.[chat.jid]===chat.marker)continue;
    if(local && chat.marker && state.panelMarkers?.[chat.jid]===chat.marker && Date.now()-(state.panelReadTimes?.[chat.jid]||0)<30000) {cache.set(chat.jid,[]);continue;}
    let messagesFromChat;try{messagesFromChat=await page(s.panelTab,'messages',[chat.jid,100]);}catch(e){cache.set(chat.jid,{error:e});continue;}
    const msgs=messagesFromChat.sort((a,b)=>a.t-b.t);
    await chrome.storage.local.set({panelReadTimes:{...(state.panelReadTimes||{}),[chat.jid]:Date.now()}});
    cache.set(chat.jid,msgs);
    const seen=local?.seen || state.panelBaseline?.[chat.jid] || [];
    const fresh=msgs.filter(m=>m.t>=s.panelStarted && !seen.includes(m.id) && ['chat','ptt','audio'].includes(m.type));
    if(!local && fresh.length) {
      await api('/panel/bridge/register',{chat:chat.jid,label:chat.label});
      const current=await chrome.storage.local.get('panelContacts');
      const contacts=current.panelContacts || {};
      contacts[chat.jid]={seen:[...seen,...msgs.filter(m=>m.t<s.panelStarted).map(m=>m.id)],pending:null};
      await chrome.storage.local.set({panelContacts:contacts});
      discovered.push({id:chat.jid});
    }
    // Sem novas mensagens, não se cadastra nem se importa o histórico dessa pessoa.
    const current=await chrome.storage.local.get('panelMarkers');
    await chrome.storage.local.set({panelMarkers:{...(current.panelMarkers||{}),[chat.jid]:chat.marker}});
  }
  return {cache,discovered};
}
async function panelTick() {
  if(panelBusy)return;
  panelBusy=true;
  try {
    const s=await chrome.storage.local.get(['panelEnabled','panelEpoch','panelTab','panelContacts','panelAuto','panelStarted']);
    if(!s.panelEnabled)return;
    await ensure(s.panelTab);
    const {cache,discovered}=await discoverPanel(s);
    if(!await panelActive(s))return;
    const remote=await api('/panel/bridge/poll',{});
    const chats=[...new Map([...remote.chats,...discovered].map(c=>[c.id,c])).values()];
    const errors=[];
    for(const chat of chats) {
      if(!individualJid(chat.id))continue;
      if(!await panelActive(s))break;
      const local=(await chrome.storage.local.get('panelContacts')).panelContacts?.[chat.id];
      if(!local)continue;
      try {
      const cached=cache.get(chat.id);if(cached?.error)throw cached.error;
      const incoming=(cached||await messages(s.panelTab,chat.id)).filter(m=>!local.seen.includes(m.id) && (!s.panelAuto || m.t>=s.panelStarted) && ['chat','ptt','audio'].includes(m.type)).sort((a,b)=>a.t-b.t);
      for(const m of incoming) {
        if(!await panelActive(s))break;
        const audio=['ptt','audio'].includes(m.type)?await page(s.panelTab,'media',[m.id]):'';
        await api('/panel/bridge/incoming',{chat:chat.id,id:m.id,text:m.body,audio_base64:audio,from_me:m.fromMe});
        await updatePanelContact(chat.id,c=>{
          c.seen=[...new Set([...c.seen,m.id])].slice(-2000);
          if(!m.fromMe)c.pending={ids:[...(c.pending?.ids || []),m.id],at:Date.now()};
        });
      }
      if(!await panelActive(s))break;
      const current=(await chrome.storage.local.get('panelContacts')).panelContacts?.[chat.id];
      if(current?.pending && Date.now()-current.pending.at>=BATCH_WAIT_MS && !panelJobs.has(chat.id)) {
        const ids=current.pending.ids.slice(0,20);
        await updatePanelContact(chat.id,c=>{const rest=c.pending.ids.slice(ids.length);c.pending=rest.length?{ids:rest,at:Date.now()}:null;});
        const task=(async()=>{
          try {await api('/panel/bridge/batch',{chat:chat.id,id:await batchId(ids),ids});}
          catch(e){await chrome.storage.local.set({panelError:errorText(e)});}
        })().finally(()=>panelJobs.delete(chat.id));
        panelJobs.set(chat.id,task);
      }
      } catch(e) {
        errors.push(errorText(e));
        try {await api('/panel/bridge/error',{chat:chat.id,detail:errorText(e)});}catch{}
      }
    }
    for(const queued of remote.queued) {
      if(!await panelActive(s))break;
      if(!individualJid(queued.chat) || !(await chrome.storage.local.get('panelContacts')).panelContacts?.[queued.chat])continue;
      const r=await api('/panel/bridge/claim',{id:queued.id});
      if(r.cancelled)continue;
      try {
        const prepared=await page(s.panelTab,'prepare',[r.chat]);
        await updatePanelContact(r.chat,c=>{c.seen=[...new Set([...c.seen,prepared.id])].slice(-2000);});
        if(!await panelActive(s))throw new Error('Conexão pausada antes de enviar.');
        const sent=await page(s.panelTab,'send',[r.chat,r,prepared.id,false]);
        if(!sent?.id)throw new Error('Não foi possível confirmar o envio.');
        await updatePanelContact(r.chat,c=>{c.seen=[...new Set([...c.seen,sent.id])].slice(-2000);});
        await api('/panel/bridge/ack',{id:r.id,ok:true});
      } catch(e) {
        await api('/panel/bridge/ack',{id:r.id,ok:false,error:errorText(e)});
      }
    }
    await chrome.storage.local.set({panelError:errors.join(' · ').slice(0,500)});
  } catch(e) {await chrome.storage.local.set({panelError:errorText(e)});}
  finally {panelBusy=false;}
}
