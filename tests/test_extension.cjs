// Simula o navegador e o WhatsApp: nenhum envio ou acesso à API real.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const root=path.join(__dirname,'..','extension');

function harness({self=false,fromMe=false,errorAt=null,error=null,httpStatus=200,voiceUnavailable=false,deferResponse=false,waitingUnavailable=false,waitingSendError=null}={}) {
  const state={enabled:true,run:'sessao-teste',tabId:1,jid:self?'self-test@c.us':'friend-test@lid',self,started:0,seen:[],ownTokens:[]};
  const sends=[];const bodies=[];let requests=0;let clock=Date.now();let nextTimer=0;let nextMessage=0;let releaseResponse;let waitingRequests=0;
  const timers=new Map();
  let incoming=[{id:{_serialized:'incoming-test',id:'incoming-token',fromMe},body:'Oi',type:'chat',t:clock/1000}];
  class ClockDate extends Date {constructor(...args){super(...(args.length?args:[clock]));}static now(){return clock;}}
  const fail=stage=>{if(errorAt===stage) throw error;};
  const wpp={isReady:true,chat:{
    getMessages:async()=>{fail('messages');return incoming;},
    generateMessageID:async()=>{fail('prepare');nextMessage++;return {_serialized:'outgoing-test-'+nextMessage,id:'outgoing-token-'+nextMessage};},
    sendTextMessage:async(jid,text,options)=>{fail('send');sends.push({jid,text,options});return {id:{_serialized:'outgoing-test'}};},
    downloadMedia:async()=>({size:10}),
    sendFileMessage:async(jid,data,options)=>{if(waitingSendError && data.endsWith('aviso-falso'))throw waitingSendError;fail('send');sends.push({jid,data,options});return {id:{_serialized:options.messageId._serialized}};},
  }};
  const browserPage=vm.createContext({WPP:wpp,window:{WPP:wpp},Map,FileReader:class{readAsDataURL(){this.result='data:audio/ogg;base64,YXVkaW8=';this.onload();}}});
  let context;
  const sandbox={AbortController,AbortSignal,crypto:webcrypto,TextEncoder,Date:ClockDate,setTimeout:(callback,delay)=>{const id=++nextTimer;timers.set(id,{callback,at:clock+delay});return id;},clearTimeout:id=>timers.delete(id),console,
    fetch:async(url,options)=>{
      if(url.includes('/waiting-audio')) {
        waitingRequests++;if(waitingUnavailable)throw new Error('Aviso indisponível');
        return {ok:true,json:async()=>({id:'wait-01',text:'Um momento',audio_base64:'aviso-falso',audio_mime:'audio/ogg'})};
      }
      requests++;const body=JSON.parse(options.body);bodies.push(body);
      if(deferResponse)await new Promise(resolve=>{releaseResponse=resolve;});
      return {ok:httpStatus===200,status:httpStatus,json:async()=>httpStatus===200?{text:'Sou a Lia',mode:'menu',handoff:false,...(body.reply_audio?(voiceUnavailable?{audio_warning:'O serviço de voz está indisponível. A resposta foi enviada por texto.'}:{audio_base64:'resposta-falsa',audio_mime:'audio/ogg'}):{})}:{detail:[{loc:['body','text'],msg:'Campo inválido'}]}};
    },
    chrome:{
      storage:{local:{get:async keys=>keys===null?{...state}:Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(key=>[key,state[key]])),set:async values=>Object.assign(state,values)}},
      tabs:{get:async()=>({url:'https://web.whatsapp.com/'}),query:async()=>[{id:1,url:'https://web.whatsapp.com/'}]},
      scripting:{executeScript:async({func,args})=>{
        browserPage.__args=structuredClone(args);
        // A função injetada é serializada: não pode usar variáveis do service worker.
        const result=await vm.runInContext(`(${func.toString()})(...__args)`,browserPage);
        return [{result:structuredClone(result)}];
      }},
      alarms:{create:async()=>{},onAlarm:{addListener:()=>{}}},
      runtime:{onMessage:{addListener:()=>{}},getURL:file=>'chrome-extension://teste/'+file},
    },
    importScripts:file=>vm.runInContext(file==='config.js'?"const EDUCA_TOKEN='chave-apenas-do-teste';":fs.readFileSync(path.join(root,file),'utf8'),context),
  };
  context=vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(root,'background.js'),'utf8'),context);
  const tick=()=>vm.runInContext('tick()',context);
  return {state,sends,bodies,requests:()=>requests,waitingRequests:()=>waitingRequests,tick,advance:ms=>{clock+=ms;},fireTimers:()=>{for(const [id,t] of timers)if(t.at<=clock){timers.delete(id);t.callback();}},releaseResponse:()=>releaseResponse(),setMessages:msgs=>{incoming=msgs;},pause:()=>vm.runInContext('pause()',context),
    flush:async()=>{await tick();clock+=5000;await tick();}};
}

(async()=>{
  const third=harness();
  await third.flush();
  assert.equal(third.requests(),1);
  assert.equal(third.sends.length,1);
  assert.equal(third.sends[0].jid,'friend-test@lid');
  assert.equal(third.sends[0].text,'Sou a Lia');
  assert.equal(third.state.enabled,true);
  await third.tick();
  assert.equal(third.sends.length,1,'Não deve duplicar a resposta');

  const ownMessage=harness({fromMe:true});
  await ownMessage.flush();
  assert.equal(ownMessage.requests(),0,'Em chat de terceiro, só responde ao que o contato envia');
  assert.equal(ownMessage.sends.length,0);

  const self=harness({self:true,fromMe:true});
  await self.flush();
  assert.equal(self.sends[0].text,'[Lia · teste]\nSou a Lia');

  for(const [stage,error,expected] of [
    ['messages',new Error('Lista de mensagens indisponível'),'Lista de mensagens indisponível'],
    ['prepare',{code:'ID_TEST',reason:'Identificador indisponível'},'Identificador indisponível'],
    ['send','Sessão de envio desconectada','Sessão de envio desconectada'],
    ['send',{},'sem informar o motivo'],
  ]) {
    const failure=harness({errorAt:stage,error});
    await failure.flush();
    assert.equal(failure.state.enabled,false);
    assert.ok(failure.state.lastStatus.includes(expected));
    assert.ok(failure.state.lastError.stage.length>0);
    assert.ok(!failure.state.lastStatus.includes('undefined'));
    if(stage==='send') {
      assert.ok(failure.state.seen.includes('incoming-test'),'Envio incerto não deve ser repetido');
      failure.state.enabled=true;
      await failure.tick();
      assert.equal(failure.requests(),1);
    }
  }
  const apiFailure=harness({httpStatus:422});
  await apiFailure.flush();
  assert.ok(apiFailure.state.lastStatus.includes('HTTP 422'));
  assert.ok(apiFailure.state.lastStatus.includes('body.text: Campo inválido'));
  assert.equal(apiFailure.state.lastError.stage,'Consultar a API da Lia');
  const sequence=harness();
  await sequence.tick();
  assert.equal(sequence.requests(),0,'Não deve responder antes da espera');
  sequence.advance(4000);
  sequence.setMessages([
    {id:{_serialized:'first',fromMe:false},body:'Boa noite',type:'chat',t:1},
    {id:{_serialized:'second',fromMe:false},body:'Os cursos são gratuitos?',type:'chat',t:2},
    {id:{_serialized:'third',fromMe:false},body:'Tenho 60 anos, posso fazer teatro?',type:'chat',t:3},
  ]);
  await sequence.tick();
  sequence.advance(4999);await sequence.tick();
  assert.equal(sequence.requests(),0,'Nova mensagem deve renovar a espera');
  sequence.advance(1);await sequence.tick();
  assert.equal(sequence.requests(),1);
  assert.equal(sequence.sends.length,1);
  assert.equal(sequence.bodies[0].parts.length,3);
  assert.ok(sequence.bodies[0].message_id.startsWith('batch:'));
  assert.ok(['first','second','third'].every(id=>sequence.state.seen.includes(id)));
  await sequence.tick();assert.equal(sequence.requests(),1);

  const voices=harness();
  voices.setMessages([{id:{_serialized:'voice1'},type:'ptt',t:1},{id:{_serialized:'voice2'},type:'ptt',t:2}]);
  await voices.flush();
  assert.equal(voices.requests(),1);
  assert.equal(voices.bodies[0].reply_audio,true);
  assert.equal(voices.bodies[0].parts.length,2);
  assert.ok(voices.bodies[0].parts.every(p=>p.audio_base64));
  assert.equal(voices.sends.length,1);
  assert.equal(voices.sends[0].options.type,'audio');

  const fallback=harness({voiceUnavailable:true});
  fallback.setMessages([{id:{_serialized:'voice-fallback'},type:'ptt',t:1}]);
  await fallback.flush();
  assert.equal(fallback.state.enabled,true,'Falha de voz não deve pausar atendimento');
  assert.equal(fallback.sends.length,1);
  assert.equal(fallback.sends[0].text,'Sou a Lia');
  assert.ok(fallback.state.lastStatus.includes('enviada por texto'));
  await fallback.tick();assert.equal(fallback.sends.length,1);

  const paused=harness();
  await paused.tick();await paused.pause();paused.advance(5000);await paused.tick();
  assert.equal(paused.requests(),0,'Pausar deve cancelar o grupo pendente');
  assert.equal(paused.state.pendingBatch,null);
  const microtasks=async()=>{for(let i=0;i<70;i++)await Promise.resolve();};
  const slow=harness({deferResponse:true});
  slow.setMessages([{id:{_serialized:'slow-voice'},type:'ptt',t:1}]);
  await slow.tick();slow.advance(5000);const processing=slow.tick();await microtasks();
  assert.equal(slow.sends.length,0);
  slow.advance(1500);slow.fireTimers();await microtasks();
  assert.equal(slow.sends.length,1,'Deve enviar o aviso enquanto a resposta está sendo gerada');
  assert.ok(slow.sends[0].data.includes('aviso-falso'));
  assert.ok(!slow.state.seen.includes('slow-voice'),'Aviso não deve consumir a pergunta');
  slow.releaseResponse();await processing;
  assert.equal(slow.sends.length,2,'Aviso e resposta final devem ser enviados uma vez cada');
  assert.ok(slow.sends[1].data.includes('resposta-falsa'));
  assert.ok(slow.state.seen.includes('slow-voice'));
  await slow.tick();assert.equal(slow.sends.length,2);
  assert.equal(voices.waitingRequests(),0,'Resposta rápida não precisa de aviso');

  const cancelled=harness({deferResponse:true});
  cancelled.setMessages([{id:{_serialized:'cancelled-voice'},type:'ptt',t:1}]);
  await cancelled.tick();cancelled.advance(5000);const pending=cancelled.tick();await microtasks();
  await cancelled.pause();cancelled.advance(1500);cancelled.fireTimers();await microtasks();
  cancelled.releaseResponse();await pending;
  assert.equal(cancelled.sends.length,0,'Pausa deve impedir aviso e resposta');

  const noClip=harness({deferResponse:true,waitingUnavailable:true});
  noClip.setMessages([{id:{_serialized:'no-clip'},type:'ptt',t:1}]);
  await noClip.tick();noClip.advance(5000);const noClipJob=noClip.tick();await microtasks();
  noClip.advance(1500);noClip.fireTimers();await microtasks();
  noClip.releaseResponse();await noClipJob;
  assert.equal(noClip.sends.length,1,'Falha ao buscar aviso não deve impedir a resposta final');
  assert.equal(noClip.state.enabled,true);

  for(const safe of [true,false]) {
    const broken=harness({deferResponse:true,waitingSendError:safe?new TypeError("Cannot read properties of undefined (reading 'prepRawMedia')"):new Error('Conexão perdida após envio')});
    broken.setMessages([{id:{_serialized:'prep-issue'},type:'ptt',t:1}]);
    await broken.tick();broken.advance(5000);const work=broken.tick();await microtasks();
    broken.advance(1500);broken.fireTimers();await microtasks();
    broken.releaseResponse();await work;
    assert.equal(broken.state.enabled,safe,'Somente falha comprovada de preparação permite continuar');
    assert.equal(broken.sends.length,safe?1:0);
    await broken.tick();assert.equal(broken.sends.length,safe?1:0,'Não repete aviso nem resposta');
  }

  const waited=harness({deferResponse:true});
  waited.setMessages([{id:{_serialized:'already-waited'},type:'ptt',t:1}]);
  waited.state.waitingBatches=['already-waited'];
  await waited.tick();waited.advance(5000);const waitedJob=waited.tick();await microtasks();
  waited.advance(1500);waited.fireTimers();await microtasks();
  waited.releaseResponse();await waitedJob;
  assert.equal(waited.waitingRequests(),0,'Retomar processamento não deve repetir aviso já enviado');
  assert.equal(waited.sends.length,1);
  console.log('OK: chat de terceiro, modo pessoal, filtros, duplicação e falhas nas etapas de leitura, preparação, envio e API. Nenhuma mensagem real foi enviada.');
})().catch(error=>{console.error(error);process.exitCode=1;});
