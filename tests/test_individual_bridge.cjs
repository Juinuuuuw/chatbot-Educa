// Verifica o filtro da integração real contra modelos simulados do WhatsApp.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
(async()=>{
 const wid=id=>({toString:()=>id,equals:other=>id===other.toString()});
 const entries=[{id:wid('friend@c.us'),t:100,formattedTitle:'Contato',lastReceivedKey:{_serialized:'key-1'}},{id:wid('new@lid'),t:101},{id:wid('self@c.us')},{id:wid('alias-self@lid'),contact:{isMe:true}},{id:wid('group@g.us'),isGroup:true},{id:wid('channel@newsletter'),isNewsletter:true},{id:wid('status@broadcast'),isBroadcast:true}];
 let options;
 const WPP={conn:{getMyUserId:()=>wid('self@c.us')},chat:{list:async o=>{options=o;return entries;}}};
 const context=vm.createContext({WPP,window:{WPP},Map,JSON});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/bridge.js'),'utf8'),context);
 const result=await vm.runInContext("whatsappBridge('individuals')",context);
 assert.equal(result.ok,true);assert.equal(options.onlyUsers,true);assert.equal(options.ignoreGroupMetadata,true);
 assert.deepEqual(Array.from(result.value,c=>c.jid),['friend@c.us','new@lid']);
 console.log('OK: descoberta individual exclui grupos, canais, status e a própria conta. Nenhuma mensagem real enviada.');
})().catch(e=>{console.error(e);process.exit(1);});
