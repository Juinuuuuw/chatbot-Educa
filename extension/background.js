/* A chave local fica no service worker, nunca no contexto da página. */
importScripts('config.js');
importScripts('bridge.js');
let activeJob=null;
const BASE='http://127.0.0.1:8765';
async function api(path,data,signal) {
  const timeout=AbortSignal.timeout(data?360000:8000);
  const r=await fetch(BASE+path,{method:data?'POST':'GET',headers:{'X-Educa-Token':EDUCA_TOKEN,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:signal?AbortSignal.any([signal,timeout]):timeout});
  if(!r.ok) {
    let detail;try {detail=(await r.json()).detail;}catch{}
    if(Array.isArray(detail)) detail=detail.map(d=>`${(d.loc||[]).join('.')}: ${d.msg||'Campo inválido'}`).join('; ');
    throw new Error(`API HTTP ${r.status}: ${typeof detail==='string'?detail:'Não foi possível processar a solicitação.'}`);
  }
  return r.json();
}
function errorText(error) {
  if(typeof error==='string' && error.trim()) return error.slice(0,500);
  if(typeof error?.message==='string' && error.message.trim()) return error.message.slice(0,500);
  try {const text=JSON.stringify(error);if(text && !['{}','null'].includes(text))return text.slice(0,500);} catch {}
  return 'A operação falhou sem informar o motivo.';
}
async function page(tabId,operation,args=[]) {
  const r=await chrome.scripting.executeScript({target:{tabId},world:'MAIN',func:whatsappBridge,args:[operation,...args]});
  const result=r[0]?.result;
  if(!result || typeof result.ok!=='boolean') throw new Error('Não foi possível obter o resultado do WhatsApp. Recarregue a aba e a extensão.');
  if(!result.ok) throw new Error(errorText(result.error)+(result.error?.code?` (código ${result.error.code})`:''));
  return result.value;
}
async function ensure(tabId) {
  const exists=await page(tabId,'exists');
  if(!exists) await chrome.scripting.executeScript({target:{tabId},world:'MAIN',files:['wppconnect-wa.js']});
  const ready=await page(tabId,'ready');
  if(!ready) throw new Error('O WhatsApp está carregando. Aguarde alguns segundos e tente ativar novamente.');
}
async function messages(tabId,jid) {
  return page(tabId,'messages',[jid]);
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
  const active=await page(tab.id,'active');
  if(!active || !/@(c\.us|lid)$/.test(active.jid)) throw new Error('Selecione uma conversa individual. Grupos não são aceitos.');
  if(self && !active.isSelf) throw new Error('O modo “Mensagem para você” só pode ser usado na sua própria conversa.');
  if(active.isSelf && !self) throw new Error('Marque “Testar em Mensagem para você” para testar na sua própria conversa.');
  const baseline=await messages(tab.id,active.jid);
  if((await chrome.storage.local.get('run')).run!==preparingRun) throw new Error('Ativação cancelada pela pausa. Clique em Ativar quando quiser retomar.');
  await chrome.storage.local.set({enabled:true,tabId:tab.id,jid:active.jid,label:active.label,self,started:Math.floor(Date.now()/1000),seen:baseline.map(m=>m.id),run:crypto.randomUUID(),lastStatus:self?'Ativo. Envie uma mensagem normal ou um áudio nesta conversa.':'Ativo. Aguardando uma mensagem enviada pelo contato para você.'});
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
  let stage='Verificar atendimento';
  try {
    const s=await chrome.storage.local.get(null);
    job.run=s.run;
    if(!s.enabled) return;
    const tab=await chrome.tabs.get(s.tabId);
    if(!tab.url?.startsWith('https://web.whatsapp.com/')) return pause('A aba do WhatsApp foi fechada ou mudou de endereço.');
    stage='Conectar ao WhatsApp';
    await ensure(s.tabId);
    stage='Ler mensagens recebidas';
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
        stage='Baixar áudio recebido';
        await chrome.storage.local.set({lastStatus:'Baixando o áudio recebido…'});
        body.audio_base64=await page(s.tabId,'media',[m.id]);
        if(!body.audio_base64) throw new Error('O download do áudio retornou vazio.');
        await chrome.storage.local.set({lastStatus:'Transcrevendo o áudio e preparando a resposta falada…'});
      }
      stage=audio?'Transcrever e gerar resposta falada':'Consultar a API da Lia';
      const response=await api('/message',body,job.controller.signal);
      const now=await chrome.storage.local.get(['enabled','run']);
      if(!now.enabled || now.run!==s.run) return;
      stage='Preparar envio no WhatsApp';
      const prepared=await page(s.tabId,'prepare',[s.jid]);
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
      stage=audio?'Enviar resposta em áudio':'Enviar resposta em texto';
      const sent=await page(s.tabId,'send',[s.jid,response,prepared.id,s.self]);
      if(sent?.id) await remember(sent.id);
      else throw new Error('Não foi possível confirmar o resultado do envio.');
      const afterSend=await chrome.storage.local.get(['enabled','run']);
      if(!afterSend.enabled || afterSend.run!==s.run) return;
      if(response.handoff) {await pause('Atendimento humano solicitado. Bot pausado nesta conversa.');return;}
      await chrome.storage.local.set({lastStatus:`Resposta enviada (${response.mode}).`});
    }
  } catch(e) {
    const current=await chrome.storage.local.get(['enabled','run']);
    if(current.enabled && current.run===job.run) {
      const detail=errorText(e);
      await chrome.storage.local.set({lastError:{stage,detail,at:new Date().toISOString()}});
      await pause(`Erro ao ${stage.toLowerCase()}: ${detail}\nReative após conferir a conversa. Um envio incerto não será repetido automaticamente.`);
    }
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
    const detail=errorText(e);
    await chrome.storage.local.set({enabled:false,lastError:{stage:'Ativar atendimento',detail,at:new Date().toISOString()},lastStatus:'Não foi possível ativar: '+detail});
    reply({ok:false,error:detail});
  });
  return true;
});
