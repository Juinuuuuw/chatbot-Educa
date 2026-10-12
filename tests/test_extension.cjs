// Simula o navegador e o WhatsApp: nenhum envio ou acesso à API real.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const root=path.join(__dirname,'..','extension');

function harness({self=false,fromMe=false,errorAt=null,error=null,httpStatus=200}={}) {
  const state={enabled:true,run:'sessao-teste',tabId:1,jid:self?'self-test@c.us':'friend-test@lid',self,started:0,seen:[],ownTokens:[]};
  const sends=[];let requests=0;
  const fail=stage=>{if(errorAt===stage) throw error;};
  const wpp={isReady:true,chat:{
    getMessages:async()=>{fail('messages');return [{id:{_serialized:'incoming-test',id:'incoming-token',fromMe},body:'Oi',type:'chat',t:Date.now()/1000}];},
    generateMessageID:async()=>{fail('prepare');return {_serialized:'outgoing-test',id:'outgoing-token'};},
    sendTextMessage:async(jid,text,options)=>{fail('send');sends.push({jid,text,options});return {id:{_serialized:'outgoing-test'}};},
  }};
  const browserPage=vm.createContext({WPP:wpp,window:{WPP:wpp},Map,FileReader:class{}});
  let context;
  const sandbox={AbortController,AbortSignal,crypto:webcrypto,setTimeout,clearTimeout,console,
    fetch:async()=>{requests++;return {ok:httpStatus===200,status:httpStatus,json:async()=>httpStatus===200?{text:'Sou a Lia',mode:'menu',handoff:false}:{detail:[{loc:['body','text'],msg:'Campo inválido'}]}};},
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
  return {state,sends,requests:()=>requests,tick:()=>vm.runInContext('tick()',context)};
}

(async()=>{
  const third=harness();
  await third.tick();
  assert.equal(third.requests(),1);
  assert.equal(third.sends.length,1);
  assert.equal(third.sends[0].jid,'friend-test@lid');
  assert.equal(third.sends[0].text,'Sou a Lia');
  assert.equal(third.state.enabled,true);
  await third.tick();
  assert.equal(third.sends.length,1,'Não deve duplicar a resposta');

  const ownMessage=harness({fromMe:true});
  await ownMessage.tick();
  assert.equal(ownMessage.requests(),0,'Em chat de terceiro, só responde ao que o contato envia');
  assert.equal(ownMessage.sends.length,0);

  const self=harness({self:true,fromMe:true});
  await self.tick();
  assert.equal(self.sends[0].text,'[Lia · teste]\nSou a Lia');

  for(const [stage,error,expected] of [
    ['messages',new Error('Lista de mensagens indisponível'),'Lista de mensagens indisponível'],
    ['prepare',{code:'ID_TEST',reason:'Identificador indisponível'},'Identificador indisponível'],
    ['send','Sessão de envio desconectada','Sessão de envio desconectada'],
    ['send',{},'sem informar o motivo'],
  ]) {
    const failure=harness({errorAt:stage,error});
    await failure.tick();
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
  await apiFailure.tick();
  assert.ok(apiFailure.state.lastStatus.includes('HTTP 422'));
  assert.ok(apiFailure.state.lastStatus.includes('body.text: Campo inválido'));
  assert.equal(apiFailure.state.lastError.stage,'Consultar a API da Lia');
  console.log('OK: chat de terceiro, modo pessoal, filtros, duplicação e falhas nas etapas de leitura, preparação, envio e API. Nenhuma mensagem real foi enviada.');
})().catch(error=>{console.error(error);process.exitCode=1;});
