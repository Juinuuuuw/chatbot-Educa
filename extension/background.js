/* A chave local fica no service worker, nunca no contexto da página. */
importScripts('config.js');
importScripts('bridge.js');
let activeJob=null;
let batchTimer=null;
const BATCH_WAIT_MS=5000;
const BASE=typeof EDUCA_BASE==='string'?EDUCA_BASE:'http://127.0.0.1:8765';
async function api(path,data,signal) {
  const timeout=AbortSignal.timeout(data?360000:8000);
  let r;
  try {r=await fetch(BASE+path,{method:data?'POST':'GET',headers:{'X-Educa-Token':EDUCA_TOKEN,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:signal?AbortSignal.any([signal,timeout]):timeout});}
  catch(e) {
    if(e.name==='AbortError')throw e;
    throw new Error(e.name==='TimeoutError'?'A API demorou para responder. Confira a janela de inicialização e tente novamente.':'A API da Lia está desligada ou inacessível. Abra INICIAR.cmd na pasta do painel e mantenha a janela aberta. Depois clique em Conectar todas as conversas. O botão da extensão não inicia a API.');
  }
  if(!r.ok) {
    let detail;try {detail=(await r.json()).detail;}catch{}
    if(Array.isArray(detail)) detail=detail.map(d=>`${(d.loc||[]).join('.')}: ${d.msg||'Campo inválido'}`).join('; ');
    throw new Error(r.status===401?'A chave da extensão não corresponde à API. Use a extensão da mesma pasta da API, execute configurar.py e recarregue a extensão.':`API HTTP ${r.status}: ${typeof detail==='string'?detail:'Não foi possível processar a solicitação.'}`);
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
  if(!result.ok) {const error=new Error(errorText(result.error)+(result.error?.code?` (código ${result.error.code})`:''));error.code=result.error?.code;throw error;}
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
  if((await chrome.storage.local.get('panelEnabled')).panelEnabled)throw new Error('Pause a conexão do painel antes de usar o teste individual.');
  // Cancelar a consulta antiga libera a retomada; o resultado antigo não pode alterar a nova sessão.
  await pause('Preparando ativação…');
  const preparingRun=(await chrome.storage.local.get('run')).run;
  if(activeJob) {
    await Promise.race([activeJob.promise, new Promise(resolve=>setTimeout(resolve,3000))]);
    if(activeJob) throw new Error('O envio anterior ainda está terminando. Aguarde alguns segundos e clique em Ativar novamente.');
  }
  const health=await api('/health');
  if(!health.supports_batches) throw new Error('A API ainda está na versão anterior. Reinicie a API da Lia antes de ativar.');
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
  await chrome.storage.local.set({enabled:true,tabId:tab.id,jid:active.jid,label:active.label,self,started:Math.floor(Date.now()/1000),seen:baseline.map(m=>m.id),run:crypto.randomUUID(),pendingBatch:null,lastStatus:self?'Ativo. Envie uma mensagem normal ou um áudio nesta conversa.':'Ativo. Aguardando uma mensagem enviada pelo contato para você.'});
  await chrome.alarms.create('educa-tick',{periodInMinutes:0.5});
}
async function pause(reason='Pausado por você.') {
  clearTimeout(batchTimer);batchTimer=null;
  await chrome.storage.local.set({enabled:false,run:crypto.randomUUID(),pendingBatch:null,lastStatus:reason});
  activeJob?.controller.abort();
}
async function remember(id) {
  return rememberMany([id]);
}
async function rememberMany(ids) {
  const s=await chrome.storage.local.get('seen');
  await chrome.storage.local.set({seen:[...new Set([...(s.seen||[]),...ids])].slice(-2000)});
}
function scheduleBatch(delay) {
  clearTimeout(batchTimer);
  batchTimer=setTimeout(()=>{batchTimer=null;tick();},Math.max(1,delay));
}
async function batchId(ids) {
  if(ids.length===1) return ids[0];
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(ids)));
  return 'batch:'+Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
}
function tick() {
  if(activeJob) return activeJob.promise;
  const job={controller:new AbortController(),run:null,promise:null};
  activeJob=job;
  job.promise=processTick(job).finally(()=>{if(activeJob===job) activeJob=null;});
  return job.promise;
}
async function sendTracked(s,response,beforeSend=async()=>{}) {
  const prepared=await page(s.tabId,'prepare',[s.jid]);
  if(!prepared?.id)throw new Error('O WhatsApp não retornou a identificação preparada.');
  await remember(prepared.id);
  if(prepared.token) {
    const prev=await chrome.storage.local.get('ownTokens');
    await chrome.storage.local.set({ownTokens:[...new Set([...(prev.ownTokens||[]),prepared.token])].slice(-2000)});
  }
  const current=await chrome.storage.local.get(['enabled','run']);
  if(!current.enabled || current.run!==s.run)return null;
  await beforeSend();
  const finalGuard=await chrome.storage.local.get(['enabled','run']);
  if(!finalGuard.enabled || finalGuard.run!==s.run)return null;
  const sent=await page(s.tabId,'send',[s.jid,response,prepared.id,s.self]);
  if(sent?.id)await remember(sent.id);
  else throw new Error('Não foi possível confirmar o resultado do envio.');
  return sent;
}
async function responseWithWaiting(s,body,job) {
  let finished=false;
  const result=api('/message',body,job.controller.signal).then(response=>({response}),error=>({error})).then(value=>{finished=true;return value;});
  let timer;
  if(body.reply_audio) {
    const first=await Promise.race([result,new Promise(resolve=>{timer=setTimeout(()=>resolve(null),1500);})]);
    clearTimeout(timer);
    if(first) {if(first.error)throw first.error;return first.response;}
    const state=await chrome.storage.local.get(['enabled','run','waitingBatches','lastWaitingAudio']);
    if(state.enabled && state.run===s.run && !state.waitingBatches?.includes(body.message_id)) {
      let clip;
      try {clip=await api('/waiting-audio?exclude='+encodeURIComponent(state.lastWaitingAudio || ''),undefined,job.controller.signal);}
      catch {
        const active=await chrome.storage.local.get(['enabled','run']);
        if(active.enabled && active.run===s.run)await chrome.storage.local.set({lastStatus:'Preparando resposta. O áudio de espera não está disponível.'});
      }
      if(clip && !finished) {
        await chrome.storage.local.set({lastStatus:'Enviando um áudio curto enquanto preparo a resposta…'});
        try {
          await sendTracked(s,clip,async()=>{
            const previous=await chrome.storage.local.get('waitingBatches');
            await chrome.storage.local.set({waitingBatches:[...new Set([...(previous.waitingBatches||[]),body.message_id])].slice(-2000),lastWaitingAudio:clip.id});
          });
        } catch(error) {
          if(error.code==='MEDIA_PREP_UNAVAILABLE') {
            await chrome.storage.local.set({lastStatus:'O aviso de espera não pôde ser preparado. Continuo preparando a resposta.',lastAudioWarning:'Recarregue a extensão e o WhatsApp Web para atualizar o envio de áudio.'});
          } else {const failure=new Error(errorText(error));failure.liaStage='Enviar áudio de espera';throw failure;}
        }
      }
    }
  }
  const value=await result;
  if(value.error)throw value.error;
  return value.response;
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
    const incoming=[];
    for(const m of msgs) {
      const state=await chrome.storage.local.get(['enabled','run','seen','ownTokens']);
      if(!state.enabled || state.run!==s.run) return;
      if(state.seen?.includes(m.id)) continue;
      if(m.fromMe && m.token && state.ownTokens?.includes(m.token)) {await remember(m.id);continue;}
      if(m.t<s.started || !['chat','ptt','audio'].includes(m.type)) {await remember(m.id);continue;}
      if(m.fromMe && !s.self) {await remember(m.id);continue;}
      if(!m.fromMe && s.self) {await remember(m.id);continue;}
      if(s.self && (m.body.startsWith('[Lia · teste]\n') || m.body.startsWith('[Educa · teste]\n'))) {await remember(m.id);continue;}
      incoming.push(m);
    }
    if(!incoming.length) return;
    if(incoming.length>20) throw new Error('Recebi mais de 20 mensagens na sequência. Divida o envio em grupos menores.');
    const ids=incoming.map(m=>m.id);
    const current=await chrome.storage.local.get(['enabled','run','pendingBatch']);
    if(!current.enabled || current.run!==s.run) return;
    const previous=current.pendingBatch;
    if(previous?.run!==s.run || JSON.stringify(previous.ids)!==JSON.stringify(ids)) {
      await chrome.storage.local.set({pendingBatch:{run:s.run,ids,lastObservedAt:Date.now()},lastStatus:`Reunindo ${incoming.length} mensagem(ns). Aguardando 5 segundos após a última…`});
      scheduleBatch(BATCH_WAIT_MS);
      return;
    }
    const remaining=BATCH_WAIT_MS-(Date.now()-previous.lastObservedAt);
    if(remaining>0) {scheduleBatch(remaining);return;}
    clearTimeout(batchTimer);batchTimer=null;
    const audio=incoming.some(m=>['ptt','audio'].includes(m.type));
    const body={chat_id:s.jid,message_id:await batchId(ids),reply_audio:audio,parts:[]};
    await chrome.storage.local.set({lastStatus:`Preparando uma resposta para ${incoming.length} mensagem(ns)…`});
    for(const m of incoming) {
      const part={text:m.body};
      if(['ptt','audio'].includes(m.type)) {
        stage='Baixar áudio recebido';
        await chrome.storage.local.set({lastStatus:'Baixando o áudio recebido…'});
        part.audio_base64=await page(s.tabId,'media',[m.id]);
        part.text='';
        if(!part.audio_base64) throw new Error('O download do áudio retornou vazio.');
        await chrome.storage.local.set({lastStatus:'Transcrevendo o áudio e preparando a resposta falada…'});
      }
      body.parts.push(part);
    }
      stage=audio?'Transcrever e gerar resposta falada':'Consultar a API da Lia';
      const response=await responseWithWaiting(s,body,job);
      const now=await chrome.storage.local.get(['enabled','run']);
      if(!now.enabled || now.run!==s.run) return;
      await chrome.storage.local.set({lastStatus:response.audio_base64?'Enviando resposta em áudio…':'Enviando resposta em texto…'});
      stage=response.audio_base64?'Enviar resposta em áudio':'Enviar resposta em texto';
      const sent=await sendTracked(s,response,async()=>{
        // O aviso de espera não consome a pergunta; só o envio da resposta final faz isso.
        await rememberMany(ids);
        await chrome.storage.local.set({pendingBatch:null});
      });
      if(!sent)return;
      const afterSend=await chrome.storage.local.get(['enabled','run']);
      if(!afterSend.enabled || afterSend.run!==s.run) return;
      if(response.handoff) {await pause('Atendimento humano solicitado. Bot pausado nesta conversa.');return;}
      await chrome.storage.local.set({lastStatus:response.audio_warning || `Resposta enviada (${response.mode}).`});
  } catch(e) {
    const current=await chrome.storage.local.get(['enabled','run']);
    if(current.enabled && current.run===job.run) {
      const detail=errorText(e);
      stage=e.liaStage || stage;
      await chrome.storage.local.set({lastError:{stage,detail,at:new Date().toISOString()}});
      await pause(`Erro ao ${stage.toLowerCase()}: ${detail}\nReative após conferir a conversa. Um envio incerto não será repetido automaticamente.`);
    }
  }
}
importScripts('panel-bridge.js');
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='educa-tick'){tick();panelTick();}});
chrome.runtime.onMessage.addListener((m,sender,reply)=> {
  const fromPopup=!sender.tab && sender.url===chrome.runtime.getURL('popup.html');
  if(m.type==='tick' && sender.tab?.url?.startsWith('https://web.whatsapp.com/')) {tick();panelTick();reply({ok:true});return;}
  if(!fromPopup) {reply({ok:false,error:'Origem não autorizada'});return;}
  (async()=> {
    if(m.type==='status') {const s=await chrome.storage.local.get(['enabled','label','lastStatus','self']);reply(s);}
    else if(m.type==='api-status') {try {const health=await api('/health');reply({ok:true,panel:!!health.supports_panel_auto});}catch(e){reply({ok:false,error:errorText(e)});}}
    else if(m.type==='start') {await start(!!m.self);reply({ok:true});}
    else if(m.type==='stop') {await pause();reply({ok:true});}
    else if(m.type==='panel-add') {await panelAdd();reply({ok:true});}
    else if(m.type==='panel-start') {await panelStart();reply({ok:true});}
    else if(m.type==='panel-open') {await panelOpen();reply({ok:true});}
    else if(m.type==='panel-stop') {await panelStop();reply({ok:true});}
    else reply({ok:false,error:'Ação desconhecida'});
  })().catch(async e=>{
    const detail=errorText(e);
    await chrome.storage.local.set({enabled:false,...(m.type?.startsWith('panel-')?{panelError:detail}:{}),lastError:{stage:'Ativar atendimento',detail,at:new Date().toISOString()},lastStatus:'Não foi possível ativar: '+detail});
    reply({ok:false,error:detail});
  });
  return true;
});
