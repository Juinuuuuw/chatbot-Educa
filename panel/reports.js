/* Relatórios agregados: não exibem nomes, números ou mensagens de pessoas. */
let currentReport=null,reportRequest=0;
function demoReport(days){
  const now=new Date(),end=new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,10);
  const startDate=new Date(now);startDate.setDate(now.getDate()-days+1);
  const start=new Date(startDate.getTime()-startDate.getTimezoneOffset()*60000).toISOString().slice(0,10);
  const contacts=Object.entries(demoMessages).flatMap(([chat,messages])=>messages.filter(m=>m.role==='contact').map(m=>({...m,chat})));
  const rank=patterns=>patterns.map(([name,pattern])=>({name,count:contacts.filter(m=>pattern.test(m.text)).length})).filter(r=>r.count).sort((a,b)=>b.count-a.count);
  return {days,start,end,demo:true,totals:{messages:contacts.length,contacts:new Set(contacts.map(m=>m.chat)).size,audio:0,text:contacts.length,handoffs:2},
    topics:rank([['Inscrição e matrícula',/inscri|matrícula/i],['Participação e idade',/anos|participar/i],['Gratuidade e valores',/gratuit/i],['Atendimento da equipe',/falar com alguém/i]]),
    courses:rank([['Teatro · turma não identificada',/teatro/i]]),handoff_reasons:[{name:'Pedido de atendente',count:1},{name:'Avaliação da equipe',count:1}],daily:Array.from({length:days},(_,i)=>{const d=new Date(startDate);d.setDate(d.getDate()+i);return {day:new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10),count:i===days-1?contacts.length:0};})};
}
function reportRanking(title,rows,empty){
  const maximum=Math.max(1,...rows.map(r=>r.count));
  return `<section class="report-section"><h3>${title}</h3>${rows.length?'<ol class="ranking">'+rows.slice(0,10).map((row,i)=>`<li><div><span><i>${i+1}</i>${escape(row.name)}</span><strong>${row.count}</strong></div><div class="rank-track" aria-hidden="true"><span style="width:${row.count/maximum*100}%"></span></div></li>`).join('')+'</ol>':`<p class="report-empty">${empty}</p>`}</section>`;
}
function renderReport(data){
  const totals=data.totals,percent=totals.messages?Math.round(totals.audio/totals.messages*100):0;
  const max=Math.max(1,...data.daily.map(d=>d.count));
  const pretty=day=>new Date(day+'T12:00:00').toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric'});
  $('#report-content').setAttribute('aria-busy','false');
  $('#report-content').innerHTML=`${data.demo?'<div class="report-demo">Dados fictícios da demonstração. Não representam atendimentos reais.</div>':''}<div class="report-date">${pretty(data.start)} a ${pretty(data.end)}</div><div class="report-metrics"><article><span>Mensagens recebidas</span><strong>${totals.messages}</strong><small>${totals.text} por texto · ${totals.audio} por áudio</small></article><article><span>Pessoas atendidas</span><strong>${totals.contacts}</strong><small>Contatos distintos no período</small></article><article><span>Uso de áudio</span><strong>${percent}<em>%</em></strong><small>Das mensagens recebidas</small></article><article><span>Encaminhamentos</span><strong>${totals.handoffs}</strong><small>Pedidos, avaliação ou falhas</small></article></div><div class="report-columns">${reportRanking('Assuntos mais procurados',data.topics,'Nenhum assunto identificado neste período.')}${reportRanking('Cursos e atividades mais buscados',data.courses,'Ainda não há menções identificadas a cursos.')}</div><section class="report-section"><h3>Mensagens ao longo do período</h3><div class="daily-chart" role="img" aria-label="${totals.messages} mensagens recebidas entre ${pretty(data.start)} e ${pretty(data.end)}"><div class="daily-bars">${data.daily.map(d=>`<div class="daily-bar" title="${pretty(d.day)}: ${d.count} mensagem(ns)"><span style="height:${d.count/max*100}%"></span></div>`).join('')}</div><div class="chart-range"><span>${pretty(data.start)}</span><span>${pretty(data.end)}</span></div></div><details class="report-data"><summary>Ver dados por dia</summary><table><thead><tr><th>Dia</th><th>Mensagens</th></tr></thead><tbody>${data.daily.map(d=>`<tr><td>${pretty(d.day)}</td><td>${d.count}</td></tr>`).join('')}</tbody></table></details></section>${reportRanking('Motivos de encaminhamento',data.handoff_reasons,'Nenhum encaminhamento registrado neste período.')}<p class="report-method">Contagens de mensagens, não de matrículas ou de vagas. Uma mensagem pode mencionar vários assuntos ou cursos. Os temas são identificados por palavras-chave no texto e nas transcrições disponíveis. Menções a cursos não confirmam que eles sejam oferecidos. Indicadores são mantidos por até 90 dias, sem textos, áudios ou telefones neste relatório.</p>`;
  $('#report-export').disabled=false;
}
async function loadReport(){
  const request=++reportRequest,days=Number($('#report-period').value);
  currentReport=null;$('#report-export').disabled=true;$('#report-content').setAttribute('aria-busy','true');$('#report-content').innerHTML='<div class="report-skeleton"><div class="skeleton-line"></div><div class="skeleton-line"></div><div class="skeleton-line"></div></div>';
  try{const data=demo?demoReport(days):await api('/api/reports?days='+days);if(request!==reportRequest)return;currentReport=data;renderReport(data);}
  catch(error){if(request!==reportRequest)return;$('#report-content').setAttribute('aria-busy','false');$('#report-content').innerHTML=`<p class="report-empty">${escape(error.message)}</p>`;}
}
for(const id of ['reports-open','reports-mobile'])$('#'+id).onclick=()=>{$('#reports-dialog').showModal();loadReport();};
$('#report-period').onchange=loadReport;
$('#reports-dialog').addEventListener('close',()=>reportRequest++);
$('#report-export').onclick=()=>{
  if(!currentReport)return;
  const r=currentReport,rows=[['Relatório EdUCA',r.demo?'Demonstração — dados fictícios':'Dados locais'],['Período',r.start,r.end],[],['Indicador','Quantidade'],['Mensagens recebidas',r.totals.messages],['Contatos distintos',r.totals.contacts],['Mensagens de texto',r.totals.text],['Mensagens de áudio',r.totals.audio],['Encaminhamentos',r.totals.handoffs],[],['Assunto','Menções'],...r.topics.map(x=>[x.name,x.count]),[],['Curso ou atividade','Menções'],...r.courses.map(x=>[x.name,x.count]),[],['Motivo de encaminhamento','Quantidade'],...r.handoff_reasons.map(x=>[x.name,x.count]),[],['Dia','Mensagens'],...r.daily.map(x=>[x.day,x.count])];
  const csv='\uFEFF'+rows.map(row=>row.map(value=>'"'+String(value).replace(/"/g,'""')+'"').join(';')).join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=`educa-relatorio-${r.demo?'demonstracao-':''}${r.start}-${r.end}.csv`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
