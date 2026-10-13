// Integração simulada: não abre nem envia mensagens a nenhum WhatsApp.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
function harness(){
 let clock=10000,next=0;
 const state={panelEnabled:true,panelTab:1,panelContacts:{'a@c.us':{seen:[],pending:null},'b@lid':{seen:[],pending:null}}};
 const inbox={'a@c.us':[],'b@lid':[]},sent=[],requests=[],queue=[];
 const sandbox={console,Map,Date:class extends Date{static now(){return clock;}},BATCH_WAIT_MS:5000,BASE:'http://127.0.0.1:8766',errorText:e=>e.message,
   chrome:{storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,structuredClone(state[k])])),set:async values=>Object.assign(state,structuredClone(values))}}},
   ensure:async()=>{},messages:async(tab,jid)=>structuredClone(inbox[jid]),batchId:async ids=>'batch:'+ids.join(','),
   page:async(tab,operation,args)=>{
     if(operation==='media')return 'dGVzdA==';
     if(operation==='prepare')return {id:'out-'+(++next)};
     if(operation==='send'){sent.push(args);inbox[args[0]].push({id:args[2],fromMe:true,type:'chat',body:args[1].text,t:clock/1000});return {id:args[2]};}
     throw Error(operation);
   },
   api:async(url,body)=>{
     requests.push({url,body});
     if(url.endsWith('/poll'))return {chats:Object.keys(inbox).map(id=>({id,state:'lia'})),queued:queue.map(r=>({id:r.id,chat:r.chat}))};
     if(url.endsWith('/claim')){const i=queue.findIndex(r=>r.id===body.id);return queue.splice(i,1)[0];}
     return {ok:true};
   }
 };
 const context=vm.createContext(sandbox);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/panel-bridge.js'),'utf8'),context);
 return {state,inbox,sent,requests,queue,tick:()=>vm.runInContext('panelTick()',context),advance:ms=>clock+=ms};
}
(async()=>{
 const h=harness();
 h.inbox['a@c.us'].push({id:'m1',fromMe:false,type:'chat',body:'Boa noite!',t:1});
 await h.tick();assert.equal(h.requests.filter(r=>r.url.endsWith('/batch')).length,0);
 h.advance(4000);h.inbox['a@c.us'].push({id:'m2',fromMe:false,type:'ptt',body:'',t:2});
 await h.tick();h.advance(4000);await h.tick();assert.equal(h.requests.filter(r=>r.url.endsWith('/batch')).length,0);
 h.advance(1000);await h.tick();await new Promise(r=>setImmediate(r));
 const batches=h.requests.filter(r=>r.url.endsWith('/batch'));
 assert.equal(batches.length,1);assert.deepEqual(Array.from(batches[0].body.ids),['m1','m2']);
 assert.equal(h.requests.filter(r=>r.url.endsWith('/incoming')).length,2);
 await h.tick();assert.equal(h.requests.filter(r=>r.url.endsWith('/batch')).length,1);
 h.queue.push({id:'reply-1',chat:'a@c.us',text:'Resposta'});
 await h.tick();await h.tick();assert.equal(h.sent.length,1);
 assert.equal(h.requests.filter(r=>r.url.endsWith('/incoming')).length,2,'Não pode interpretar a própria resposta como intervenção humana');
 h.inbox['b@lid'].push({id:'operator',fromMe:true,type:'chat',body:'Vou atender',t:3});await h.tick();
 assert.equal(h.requests.find(r=>r.url.endsWith('/incoming')&&r.body.id==='operator').body.from_me,true);
 h.state.panelEnabled=false;h.queue.push({id:'reply-2',chat:'b@lid',text:'Não enviar'});await h.tick();assert.equal(h.sent.length,1);
 console.log('OK: painel com múltiplos chats, texto/áudio agrupados, deduplicação, envio, intervenção direta e pausa. Nenhuma mensagem real enviada.');
})().catch(e=>{console.error(e);process.exit(1);});
