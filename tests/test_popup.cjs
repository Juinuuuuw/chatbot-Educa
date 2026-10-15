// Diagnóstico e erros persistentes, sem navegador, API ou WhatsApp reais.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'../extension');
const flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 const nodes=new Map(),timers=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',disabled:false,checked:false});return nodes.get(id);};
 let online=false;
 const state={panelEnabled:false,panelAuto:false,panelContacts:{},panelError:''};
 const error='A API está desligada. Abra INICIAR.cmd.';
 const context=vm.createContext({document:{getElementById:node},setInterval:(fn,ms)=>timers.push({fn,ms}),chrome:{
  storage:{local:{get:async keys=>Object.fromEntries(keys.map(k=>[k,state[k]]))}},
  runtime:{sendMessage:async m=>{
   if(m.type==='status')return {enabled:false};
   if(m.type==='api-status')return online?{ok:true,panel:true}:{ok:false,error};
   if(m.type==='panel-start'){if(!online)return {ok:false,error};state.panelEnabled=true;state.panelAuto=true;}
   return {ok:true};
  }}
 }});
 vm.runInContext(fs.readFileSync(path.join(root,'popup.js'),'utf8'),context);
 await flush();assert.match(node('api-status').textContent,/INICIAR/);
 await node('panel-start').onclick();
 assert.equal(node('panel-status').textContent,error);
 timers.find(t=>t.ms===1500).fn();await flush();
 assert.equal(node('panel-status').textContent,error,'A atualização periódica não pode apagar o erro');
 assert.equal(node('panel-start').disabled,false);
 online=true;await node('panel-start').onclick();
 assert.match(node('panel-status').textContent,/Conectado a todas/);
 await vm.runInContext('checkApi()',context);
 assert.match(node('api-status').textContent,/API disponível/);
 const worker=fs.readFileSync(path.join(root,'background.js'),'utf8').split('function errorText')[0];
 const network=vm.createContext({importScripts:()=>{},EDUCA_BASE:'http://127.0.0.1:8766',EDUCA_TOKEN:'teste-ficticio',AbortSignal,fetch:async()=>{throw new TypeError('Failed to fetch');}});
 vm.runInContext(worker,network);
 await assert.rejects(vm.runInContext("api('/health')",network),/INICIAR.cmd/);
 console.log('OK: API desligada explicada, erro preservado no popup e nova conexão após recuperação.');
})().catch(e=>{console.error(e);process.exitCode=1;});
