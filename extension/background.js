/* A chave local fica no service worker, nunca no contexto da página. */
importScripts('config.js');
let activeJob=null;
const BASE='http://127.0.0.1:8765';
async function api(path,data,signal) {
  const timeout=AbortSignal.timeout(data?360000:8000);
  const r=await fetch(BASE+path,{method:data?'POST':'GET',headers:{'X-Educa-Token':EDUCA_TOKEN,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:signal?AbortSignal.any([signal,timeout]):timeout});
  if(!r.ok) {let detail;try {detail=(await r.json()).detail;}catch{} throw new Error(detail || `API: ${r.status}`);}
  return r.json();
}
async function page(tabId,func,args=[]) {
  const r=await chrome.scripting.executeScript({target:{tabId},world:'MAIN',func,args});
  if(r[0]?.error) throw new Error(r[0].error.message);
  return r[0]?.result;
}
async function ensure(tabId) {
  const exists=await page(tabId,()=>!!window.WPP);
  if(!exists) await chrome.scripting.executeScript({target:{tabId},world:'MAIN',files:['wppconnect-wa.js']});
  const ready=await page(tabId,()=>!!window.WPP?.isReady);
  if(!ready) throw new Error('O WhatsApp está carregando. Aguarde alguns segundos e tente ativar novamente.');
}
async function messages(tabId,jid) {
  return page(tabId,async target=> {
    const msgs=await WPP.chat.getMessages(target,{count:40});
    return msgs.map(m=>({id:m.id?._serialized || String(m.id),token:m.id?.id || '',fromMe:!!m.id?.fromMe,body:typeof m.body==='string'?m.body:'',type:m.type,t:Number(m.t||m.timestamp||0)}));
  },[jid]);
}
async function start(self) {
  // Cancelar a consulta antiga libera a retomada; o resultado antigo não pode alterar a nova sessão.
  await pause('Preparando ativação…');
  const preparingRun=(await chrome.storage.local.get('run')).run;
  if(activeJob) {
    await Promise.race([activeJob.promise, new Promise(resolve=>setTimeout(resolve,3000))]);
    if(activeJob) throw new Error('O envio anterior ainda está terminando. Aguarde alguns segundos e clique em Ativar novamente.');
  }
  await api('/health');
  const tabs=await chrome.tabs.query({active:true,currentWindow:true});
  const tab=tabs[0];
  if(!tab?.url?.startsWith('https://web.whatsapp.com/')) throw new Error('Abra o WhatsApp Web na aba atual e selecione a conversa de teste.');
  await ensure(tab.id);
  const active=await page(tab.id,()=> {
    const c=WPP.chat.getActiveChat();
    return c?{jid:c.id.toString(),label:c.formattedTitle || c.name || 'Conversa de teste',isSelf:c.isSelf===true || c.contact?.isMe===true || c.id.equals?.(WPP.conn.getMyUserId())===true}:null;
  });
  if(!active || !/@(c\.us|lid)$/.test(active.jid)) throw new Error('Selecione uma conversa individual. Grupos não são aceitos.');
  if(self && !active.isSelf) throw new Error('O modo “Mensagem para você” só pode ser usado na sua própria conversa.');
  if(active.isSelf && !self) throw new Error('Marque “Testar em Mensagem para você” para testar na sua própria conversa.');
  const baseline=await messages(tab.id,active.jid);
  if((await chrome.storage.local.get('run')).run!==preparingRun) throw new Error('Ativação cancelada pela pausa. Clique em Ativar quando quiser retomar.');
  await chrome.storage.local.set({enabled:true,tabId:tab.id,jid:active.jid,label:active.label,self,started:Math.floor(Date.now()/1000),seen:baseline.map(m=>m.id),run:crypto.randomUUID(),lastStatus:'Ativo. Envie uma mensagem normal ou um áudio; não precisa de comando.'});
  await chrome.alarms.create('educa-tick',{periodInMinutes:0.5});
}
async function pause(reason='Pausado por você.') {
  await chrome.storage.local.set({enabled:false,run:crypto.randomUUID(),lastStatus:reason});
  activeJob?.controller.abort();
}
async function remember(id) {
  const s=await chrome.storage.local.get('seen');
  await chrome.storage.local.set({seen:[...new Set([...(s.seen||[]),id])].slice(-2000)});
}
function tick() {
  if(activeJob) return activeJob.promise;
  const job={controller:new AbortController(),run:null,promise:null};
  activeJob=job;
  job.promise=processTick(job).finally(()=>{if(activeJob===job) activeJob=null;});
  return job.promise;
}
async function processTick(job) {
  try {
    const s=await chrome.storage.local.get(null);
    job.run=s.run;
    if(!s.enabled) return;
    const tab=await chrome.tabs.get(s.tabId);
    if(!tab.url?.startsWith('https://web.whatsapp.com/')) return pause('A aba do WhatsApp foi fechada ou mudou de endereço.');
    await ensure(s.tabId);
    const msgs=(await messages(s.tabId,s.jid)).sort((a,b)=>a.t-b.t);
    for(const m of msgs) {
      const state=await chrome.storage.local.get(['enabled','run','seen','ownTokens']);
      if(!state.enabled || state.run!==s.run) return;
      if(state.seen?.includes(m.id)) continue;
      if(m.fromMe && m.token && state.ownTokens?.includes(m.token)) {await remember(m.id);continue;}
      if(m.t<s.started || !['chat','ptt','audio'].includes(m.type)) {await remember(m.id);continue;}
      if(m.fromMe && !s.self) {await remember(m.id);continue;}
      if(!m.fromMe && s.self) {await remember(m.id);continue;}
      if(s.self && (m.body.startsWith('[Lia · teste]\n') || m.body.startsWith('[Educa · teste]\n'))) {await remember(m.id);continue;}
      await chrome.storage.local.set({lastStatus:'Preparando resposta…'});
      const audio=['ptt','audio'].includes(m.type);
      const body={chat_id:s.jid,message_id:m.id,text:m.body,reply_audio:audio};
      if(audio) {
        await chrome.storage.local.set({lastStatus:'Baixando o áudio recebido…'});
        body.audio_base64=await page(s.tabId,async id=> {
          const blob=await WPP.chat.downloadMedia(id);
          if(blob.size>12*1024*1024) throw new Error('Áudio maior que 12 MB.');
          return await new Promise((resolve,reject)=>{
            const reader=new FileReader();
            reader.onload=()=>resolve(String(reader.result).split(',')[1]);
            reader.onerror=()=>reject(new Error('Não foi possível ler o áudio recebido.'));
            reader.readAsDataURL(blob);
          });
        },[m.id]);
        if(!body.audio_base64) throw new Error('O download do áudio retornou vazio.');
        await chrome.storage.local.set({lastStatus:'Transcrevendo o áudio e preparando a resposta falada…'});
      }
      const response=await api('/message',body,job.controller.signal);
      const now=await chrome.storage.local.get(['enabled','run']);
      if(!now.enabled || now.run!==s.run) return;
      const prepared=await page(s.tabId,async jid=>{
        const key=await WPP.chat.generateMessageID(jid);
        const id=key?._serialized || key?.toString?.();
        if(typeof id!=='string' || !id || id==='undefined' || id==='[object Object]') throw new Error('Não foi possível preparar a identificação antes do envio.');
        window.__educaOutgoingKeys ||= new Map();
        window.__educaOutgoingKeys.set(id,key);
        return {id,token:key.id || ''};
      },[s.jid]);
      if(!prepared?.id) throw new Error('O WhatsApp não retornou a identificação preparada.');
      await remember(prepared.id);
      if(prepared.token) {
        const prev=await chrome.storage.local.get('ownTokens');
        await chrome.storage.local.set({ownTokens:[...new Set([...(prev.ownTokens||[]),prepared.token])].slice(-2000)});
      }
      const beforeSend=await chrome.storage.local.get(['enabled','run']);
      if(!beforeSend.enabled || beforeSend.run!==s.run) return;
      // Marcar antes do envio evita reenvio automático se a confirmação do WhatsApp se perder.
      await remember(m.id);
      await chrome.storage.local.set({lastStatus:audio?'Enviando resposta em áudio…':'Enviando resposta em texto…'});
      const sent=await page(s.tabId,async (jid,r,preparedId)=> {
        const outgoingKey=window.__educaOutgoingKeys?.get(preparedId);
        if(!outgoingKey) throw new Error('A identificação preparada se perdeu. Reative o teste.');
        let result;
        const options={messageId:outgoingKey,waitForAck:false};
        if(r.audio_base64) result=await WPP.chat.sendFileMessage(jid,`data:${r.audio_mime};base64,${r.audio_base64}`,{...options,type:'audio',isPtt:true,filename:r.audio_mime.startsWith('audio/ogg')?'educa.ogg':'educa.wav',mimetype:r.audio_mime});
        else result=await WPP.chat.sendTextMessage(jid,'[Lia · teste]\n'+r.text,{...options,detectMentioned:false});
        window.__educaOutgoingKeys.delete(preparedId);
        const key=result?.id || result?.message?.id;
        return {id:key?._serialized || (key?String(key):null) || preparedId};
      },[s.jid,response,prepared.id]);
      if(sent?.id) await remember(sent.id);
      else throw new Error('Não foi possível confirmar o resultado do envio.');
      const afterSend=await chrome.storage.local.get(['enabled','run']);
      if(!afterSend.enabled || afterSend.run!==s.run) return;
      if(response.handoff) {await pause('Atendimento humano solicitado. Bot pausado nesta conversa.');return;}
      await chrome.storage.local.set({lastStatus:`Resposta enviada (${response.mode}).`});
    }
  } catch(e) {
    const current=await chrome.storage.local.get(['enabled','run']);
    if(current.enabled && current.run===job.run) await pause('Erro: '+e.message+' Reative após conferir a conversa; não haverá reenvio automático.');
  }
}
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='educa-tick')tick();});
chrome.runtime.onMessage.addListener((m,sender,reply)=> {
  const fromPopup=!sender.tab && sender.url===chrome.runtime.getURL('popup.html');
  if(m.type==='tick' && sender.tab?.url?.startsWith('https://web.whatsapp.com/')) {tick();reply({ok:true});return;}
  if(!fromPopup) {reply({ok:false,error:'Origem não autorizada'});return;}
  (async()=> {
    if(m.type==='status') {const s=await chrome.storage.local.get(['enabled','label','lastStatus','self']);reply(s);}
    else if(m.type==='start') {await start(!!m.self);reply({ok:true});}
    else if(m.type==='stop') {await pause();reply({ok:true});}
    else reply({ok:false,error:'Ação desconhecida'});
  })().catch(async e=>{
    await chrome.storage.local.set({enabled:false,lastStatus:'Não foi possível ativar: '+e.message});
    reply({ok:false,error:e.message});
  });
  return true;
});
