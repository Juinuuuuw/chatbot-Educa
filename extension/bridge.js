/* Executado no WhatsApp por scripting.executeScript; não depende do service worker. */
async function whatsappBridge(operation, ...args) {
  try {
    let value;
    switch(operation) {
      case 'exists': value=!!window.WPP; break;
      case 'ready': value=!!window.WPP?.isReady; break;
      case 'individuals': {
        const chats=await WPP.chat.list({onlyUsers:true,ignoreGroupMetadata:true});
        if(!Array.isArray(chats))throw new Error('O WhatsApp não retornou a lista de conversas individuais.');
        const myId=WPP.conn.getMyUserId();
        const me=myId?.toString();
        if(!me)throw new Error('Entre na sua conta no WhatsApp Web antes de conectar o painel.');
        value=chats.filter(c=>{
          const jid=c.id?.toString();
          return /@(c\.us|lid)$/.test(jid||'') && !c.isGroup && !c.isBroadcast && !c.isNewsletter && c.isSelf!==true && c.contact?.isMe!==true && jid!==me && c.id.equals?.(myId)!==true;
        }).map(c=>({jid:c.id.toString(),label:c.formattedTitle || c.name || c.contact?.name || c.id.toString(),t:Number(c.t||0),marker:JSON.stringify([c.lastReceivedKey?._serialized || c.lastReceivedKey?.toString?.() || '',Number(c.t||0),Number(c.unreadCount||0)])}));
        break;
      }
      case 'active': {
        const c=WPP.chat.getActiveChat();
        value=c?{jid:c.id.toString(),label:c.formattedTitle || c.name || 'Conversa de teste',isSelf:c.isSelf===true || c.contact?.isMe===true || c.id.equals?.(WPP.conn.getMyUserId())===true}:null;
        break;
      }
      case 'messages': {
        const msgs=await WPP.chat.getMessages(args[0],{count:args[1]===100?100:40});
        if(!Array.isArray(msgs)) throw new Error('O WhatsApp não retornou uma lista de mensagens válida.');
        value=msgs.map(m=>({id:m.id?._serialized || String(m.id),token:m.id?.id || '',fromMe:!!m.id?.fromMe,body:typeof m.body==='string'?m.body:'',type:m.type,t:Number(m.t||m.timestamp||0)}));
        break;
      }
      case 'media': {
        const blob=await WPP.chat.downloadMedia(args[0]);
        if(!blob || typeof blob.size!=='number') throw new Error('O WhatsApp não retornou o arquivo de áudio.');
        if(blob.size>12*1024*1024) throw new Error('Áudio maior que 12 MB.');
        value=await new Promise((resolve,reject)=>{
          const reader=new FileReader();
          reader.onload=()=>resolve(String(reader.result).split(',')[1]);
          reader.onerror=()=>reject(new Error('Não foi possível ler o áudio recebido.'));
          reader.readAsDataURL(blob);
        });
        break;
      }
      case 'prepare': {
        const key=await WPP.chat.generateMessageID(args[0]);
        const id=key?._serialized || key?.toString?.();
        if(typeof id!=='string' || !id || id==='undefined' || id==='[object Object]') throw new Error('Não foi possível preparar a identificação antes do envio.');
        window.__educaOutgoingKeys ||= new Map();
        window.__educaOutgoingKeys.set(id,key);
        value={id,token:key.id || ''};
        break;
      }
      case 'send': {
        const [jid,r,preparedId,self]=args;
        const outgoingKey=window.__educaOutgoingKeys?.get(preparedId);
        if(!outgoingKey) throw new Error('A identificação preparada se perdeu. Reative o atendimento.');
        const options={messageId:outgoingKey,waitForAck:false};
        let result;
        try {
          if(r.audio_base64) result=await WPP.chat.sendFileMessage(jid,`data:${r.audio_mime};base64,${r.audio_base64}`,{...options,type:'audio',isPtt:true,filename:r.audio_mime.startsWith('audio/ogg')?'lia.ogg':'lia.wav',mimetype:r.audio_mime});
          else result=await WPP.chat.sendTextMessage(jid,(self?'[Lia · teste]\n':'')+r.text,{...options,detectMentioned:false});
        } finally {
          window.__educaOutgoingKeys.delete(preparedId);
        }
        const key=result?.id || result?.message?.id;
        value={id:key?._serialized || (key?String(key):null) || preparedId};
        break;
      }
      default: throw new Error('Operação de integração desconhecida.');
    }
    return {ok:true,value};
  } catch(error) {
    // Erros rejeitados no MAIN world podem perder os detalhes ao cruzar para a extensão.
    let message;
    if(typeof error==='string') message=error;
    else if(typeof error?.message==='string' && error.message.trim()) message=error.message;
    else if(typeof error?.reason==='string') message=error.reason;
    else {try {message=JSON.stringify(error);} catch {}}
    if(!message || ['{}','null','undefined'].includes(message)) message='O WhatsApp falhou nesta operação sem informar o motivo.';
    // Esta falha acontece na preparação da mídia, antes de criar/enviar a mensagem.
    const missingMediaPrep=operation==='send' && args[1]?.audio_base64 &&
      /Cannot read properties of undefined \(reading ['"]prepRawMedia['"]\)/.test(message);
    return {ok:false,error:{name:error?.name || 'WhatsAppError',message:message.slice(0,500),code:missingMediaPrep?'MEDIA_PREP_UNAVAILABLE':String(error?.code || '')}};
  }
}
