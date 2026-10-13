/* Transporte do painel: múltiplas conversas individuais adicionadas pelo operador. */
let panelBusy=false;
const panelJobs=new Map();
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
  await chrome.storage.local.set({panelEnabled:true,panelTab:tab.id,panelContacts:contacts,lastStatus:'Conversa adicionada ao painel: '+chat.label});
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
async function panelTick() {
  if(panelBusy)return;
  panelBusy=true;
  try {
    const s=await chrome.storage.local.get(['panelEnabled','panelTab','panelContacts']);
    if(!s.panelEnabled)return;
    await ensure(s.panelTab);
    const remote=await api('/panel/bridge/poll',{});
    for(const chat of remote.chats) {
      const local=(await chrome.storage.local.get('panelContacts')).panelContacts?.[chat.id];
      if(!local)continue;
      const incoming=(await messages(s.panelTab,chat.id)).filter(m=>!local.seen.includes(m.id) && ['chat','ptt','audio'].includes(m.type)).sort((a,b)=>a.t-b.t);
      for(const m of incoming) {
        const audio=['ptt','audio'].includes(m.type)?await page(s.panelTab,'media',[m.id]):'';
        await api('/panel/bridge/incoming',{chat:chat.id,id:m.id,text:m.body,audio_base64:audio,from_me:m.fromMe});
        await updatePanelContact(chat.id,c=>{
          c.seen=[...new Set([...c.seen,m.id])].slice(-2000);
          if(!m.fromMe)c.pending={ids:[...(c.pending?.ids || []),m.id],at:Date.now()};
        });
      }
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
    }
    for(const queued of remote.queued) {
      if(!(await chrome.storage.local.get('panelEnabled')).panelEnabled)break;
      if(!s.panelContacts?.[queued.chat])continue;
      const r=await api('/panel/bridge/claim',{id:queued.id});
      if(r.cancelled)continue;
      try {
        const prepared=await page(s.panelTab,'prepare',[r.chat]);
        await updatePanelContact(r.chat,c=>{c.seen=[...new Set([...c.seen,prepared.id])].slice(-2000);});
        const sent=await page(s.panelTab,'send',[r.chat,r,prepared.id,false]);
        if(!sent?.id)throw new Error('Não foi possível confirmar o envio.');
        await updatePanelContact(r.chat,c=>{c.seen=[...new Set([...c.seen,sent.id])].slice(-2000);});
        await api('/panel/bridge/ack',{id:r.id,ok:true});
      } catch(e) {
        await api('/panel/bridge/ack',{id:r.id,ok:false,error:errorText(e)});
      }
    }
    await chrome.storage.local.set({panelError:''});
  } catch(e) {await chrome.storage.local.set({panelError:errorText(e)});}
  finally {panelBusy=false;}
}
