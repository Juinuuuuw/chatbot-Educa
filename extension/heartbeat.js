// Mantém a verificação frequente enquanto a aba do WhatsApp estiver aberta.
setInterval(() => chrome.runtime.sendMessage({type: 'tick'}).catch(() => {}), 5000);
