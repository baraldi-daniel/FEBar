"use strict";
const { useState, useEffect, useRef, Fragment } = React;
const html = htm.bind(React.createElement);

/* ============ helpers ============ */
const fmt  = (n) => new Intl.NumberFormat("pt-BR").format(Math.round(n||0));
const fmt1 = (n) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(n||0);
const brl  = (n) => n>=1e9 ? "R$ "+fmt1(n/1e9)+" bi" : n>=1e6 ? "R$ "+fmt1(n/1e6)+" mi" : "R$ "+fmt(n);
const fmtK = (n) => n>=1e6 ? fmt1(n/1e6)+"M" : n>=1e4 ? Math.round(n/1e3)+"k" : fmt(n);
const un   = (n) => fmt(n)+" un";
const cssv = (v) => getComputedStyle(document.body).getPropertyValue(v).trim();
async function api(path, opts){ const r=await fetch(path,opts); const j=await r.json().catch(()=>({})); if(!r.ok) throw new Error(j.erro||r.statusText); return j; }
async function apiForm(path, fd, ms=150000){ const ac=new AbortController(); const t=setTimeout(()=>ac.abort(),ms);
  try{ const r=await fetch(path,{method:"POST",body:fd,signal:ac.signal}); const j=await r.json().catch(()=>({})); if(!r.ok) throw new Error(j.erro||("HTTP "+r.status)); return j; }
  catch(e){ if(e.name==="AbortError") throw new Error("a análise demorou demais — tente novamente"); throw e; }
  finally{ clearTimeout(t); } }
function mdInline(t){
  if(t==null) return t;
  return String(t).split(/(\*\*[^*]+\*\*)/g).map((p,i)=>
    (p.startsWith("**")&&p.endsWith("**")) ? html`<b key=${i}>${p.slice(2,-2)}</b>` : p);
}
function tabelasDeSql(sql){
  const s=String(sql||""); const out=[]; const re=/(?:from|join)\s+([a-zA-Z0-9_.`]+)/gi; let m;
  while((m=re.exec(s))){ let t=m[1].replace(/`/g,"").split(".").pop(); if(t&&!out.includes(t)) out.push(t); }
  if(!out.length) return "dados de vendas (Genie)";
  return (out.length>1?"tabelas ":"tabela ")+out.join(", ");
}
const tipEl=()=>document.getElementById("tip");
function showTip(inner,x,y){ const t=tipEl(); t.innerHTML=inner; t.style.opacity=1; const w=t.offsetWidth,h=t.offsetHeight;
  t.style.left=Math.min(window.innerWidth-w-8,Math.max(8,x-w/2))+"px"; t.style.top=Math.max(8,y-h-14)+"px"; }
const hideTip=()=>{ tipEl().style.opacity=0; };

/* ============ gráficos ============ */
function Bars({ items, colorVar }){
  if(!items||!items.length) return html`<p class="muted">Sem dados.</p>`;
  const max=Math.max(...items.map(i=>i.valor))||1, rowH=32, lblW=124, col=cssv(colorVar||"--brand");
  return html`<svg viewBox="0 0 320 ${items.length*rowH+4}" width="100%" style=${{display:"block",maxWidth:"460px"}}>
    ${items.map((it,i)=>{const y=i*rowH+4,bw=310-lblW-40,wv=Math.max(4,bw*it.valor/max),
      lbl=(""+it.rotulo).length>17?(""+it.rotulo).slice(0,16)+"…":it.rotulo;
      return html`<g key=${i}>
        <text x="0" y=${y+18} font-size="12" fill=${cssv("--text-secondary")}>${lbl}</text>
        <rect x=${lblW} y=${y+6} width=${bw} height="15" rx="7" fill=${cssv("--grid")}/>
        <rect x=${lblW} y=${y+6} width=${wv} height="15" rx="7" fill=${col}/>
        <text x=${lblW+wv+5} y=${y+18} font-size="11.5" font-weight="700" fill=${cssv("--text-primary")}>${fmt1(it.valor)}</text>
      </g>`;})}
  </svg>`;
}
function Donut({ items, colorFn }){
  if(!items||!items.length) return html`<p class="muted">Sem dados.</p>`;
  const PAL=["--s1","--s2","--s3","--s5","--s7","--s4","--s6","--s8"];
  const cf=colorFn||((r,i)=>cssv(PAL[i%PAL.length]));
  const total=items.reduce((a,b)=>a+b.valor,0)||1; const cx=90,cy=90,r=72,rin=46; let ang=-Math.PI/2;
  const arcs=items.map((it,i)=>{const frac=it.valor/total,a2=ang+frac*2*Math.PI,lg=frac>.5?1:0;
    const P=(a,rad)=>[cx+rad*Math.cos(a),cy+rad*Math.sin(a)];
    const[x1,y1]=P(ang,r),[x2,y2]=P(a2,r),[x3,y3]=P(a2,rin),[x4,y4]=P(ang,rin);
    const d=`M${x1},${y1} A${r},${r} 0 ${lg} 1 ${x2},${y2} L${x3},${y3} A${rin},${rin} 0 ${lg} 0 ${x4},${y4} Z`; ang=a2;
    return {d,it,frac,c:cf(it.rotulo,i)};});
  return html`<div style=${{display:"flex",gap:"14px",alignItems:"center",flexWrap:"wrap"}}>
    <svg viewBox="0 0 180 180" width="150" style=${{flex:"none"}}>
      ${arcs.map((a,i)=>html`<path key=${i} d=${a.d} fill=${a.c} stroke=${cssv("--surface-1")} stroke-width="2"
        onTouchStart=${(e)=>{const t=e.touches[0];showTip(`<div class="tt">${a.it.rotulo}</div><div class="tr"><span>${fmt1(a.it.valor)}</span><b>${Math.round(a.frac*100)}%</b></div>`,t.clientX,t.clientY);}}
        onMouseMove=${(e)=>showTip(`<div class="tt">${a.it.rotulo}</div><div class="tr"><span>${fmt1(a.it.valor)}</span><b>${Math.round(a.frac*100)}%</b></div>`,e.clientX,e.clientY)} onMouseLeave=${hideTip}/>`)}
      <text x="90" y="88" text-anchor="middle" font-size="19" font-weight="800" fill=${cssv("--text-primary")}>${fmtK(total)}</text>
      <text x="90" y="105" text-anchor="middle" font-size="10">total</text>
    </svg>
    <div class="legend" style=${{flex:1}}>${arcs.map((a,i)=>html`<span key=${i}><i class="dot" style=${{background:a.c}}></i>${a.it.rotulo} · ${fmt1(a.it.valor)}</span>`)}</div>
  </div>`;
}

/* ============ mapa do Brasil ============ */
function MapaBR({ ufs, foco }){
  const M=window.MAPA_BR; const [sel,setSel]=useState(foco||null);
  if(!M) return html`<p class="muted">Mapa indisponível.</p>`;
  const by={}; (ufs||[]).forEach(u=>by[u.uf]=u);
  const max=Math.max(1,...(ufs||[]).map(u=>u.receita_mi||0));
  const fill=(uf)=>{ const d=by[uf]; if(!d||!d.receita_mi) return cssv("--grid");
    const t=0.18+0.82*Math.min(1,d.receita_mi/max); return `color-mix(in srgb, ${cssv("--brand")} ${Math.round(t*100)}%, var(--surface-2))`; };
  const tipHtml=(e)=>{const x=by[e.uf];return `<div class="tt">${e.nome} (${e.uf})</div><div class="tr"><span>Receita</span><b>${x?"R$ "+fmt1(x.receita_mi)+" mi":"—"}</b></div><div class="tr"><span>Exportação</span><b>${x?fmt(x.ecommerce_pct)+"%":"—"}</b></div><div class="tr"><span>Produtos</span><b>${x?fmt(x.produtos):0}</b></div>`;};
  const d=sel?by[sel]:null;
  return html`<div>
    <div class="mapwrap"><svg viewBox=${M.viewBox} role="img" aria-label="Mapa do Brasil por receita">
      ${M.estados.map(e=>html`<path key=${e.uf} d=${e.d} fill=${fill(e.uf)}
        stroke=${sel===e.uf?cssv("--brand-2"):cssv("--surface-1")} stroke-width=${sel===e.uf?2.2:0.7}
        onClick=${()=>setSel(e.uf)}
        onTouchStart=${(ev)=>{const t=ev.touches[0];showTip(tipHtml(e),t.clientX,t.clientY);}}
        onMouseMove=${(ev)=>showTip(tipHtml(e),ev.clientX,ev.clientY)}
        onMouseLeave=${hideTip}/>`)}
    </svg></div>
    <div class="maplegend"><span>menor</span><div class="bar"></div><span>maior receita</span></div>
    ${d?html`<${MapaUFDetalhe} uf=${sel} resumo=${d}/>`:html`<p class="cap center" style=${{marginTop:"8px"}}>Clique num estado para ver os produtos vendidos</p>`}
  </div>`;
}
function MapaUFDetalhe({ uf, resumo }){
  const [cs,setCs]=useState(null);
  useEffect(()=>{ setCs(null); api("/api/mapa/uf?uf="+encodeURIComponent(uf)).then(r=>setCs(r.produtos||[])).catch(()=>setCs([])); },[uf]);
  return html`<div class="mapdetail">
    <div class="h">${uf} · ${brl((resumo.receita_mi||0)*1e6)} · ${fmt(resumo.ecommerce_pct)}% exportação · ${fmt(resumo.produtos)} produtos</div>
    ${cs==null?html`<span class="spin"></span>`
      :cs.length?html`<div class="tscroll"><table><thead><tr><th>Produto</th><th>Receita(mi)</th><th>Qtd</th></tr></thead>
        <tbody>${cs.map((e,i)=>html`<tr key=${i}><td>${e.produto}</td><td>${fmt1(e.receita_mi)}</td><td>${fmt(e.volume)}</td></tr>`)}</tbody></table></div>`
      :html`<p class="muted">Sem vendas.</p>`}
  </div>`;
}

/* ============ cards de resposta do chat ============ */
function ResCard({ c }){
  if(c.tipo==="mapa") return html`<div class="rescard"><div class="rt">🗺️ Mapa · receita por estado</div><${MapaBR} ufs=${c.ufs} foco=${c.foco}/></div>`;
  if(c.tipo==="tabela") return html`<div class="rescard"><div class="rt">📊 Dados</div>
    <div class="tscroll"><table><thead><tr>${c.colunas.map((h,i)=>html`<th key=${i}>${h}</th>`)}</tr></thead>
      <tbody>${c.linhas.map((r,i)=>html`<tr key=${i}>${r.map((v,j)=>html`<td key=${j}>${String(v??"")}</td>`)}</tr>`)}</tbody></table></div></div>`;
  return null;
}

/* ============ resultado da inspeção de peça (aba Diagnóstico + chat) ============ */
function EquipResultado({ r }){
  const ok = r.cultura && r.cultura!=="Não identificado";
  return html`<div class="card" style=${{marginTop:"10px"}}>
    <div style=${{minWidth:0}}>
      <div style=${{fontWeight:800,fontSize:"19px"}}>${r.cultura}</div>
      <div class="cap">Diagnóstico por IA${r.estagio?" · "+r.estagio:""}</div>
    </div>
    ${r.sanidade?html`<div style=${{marginTop:"10px",display:"flex",gap:"8px",alignItems:"flex-start"}}>
      <span class="badge b-warm">Diagnóstico</span><span style=${{fontSize:"13.5px",flex:1}}>${r.sanidade}</span></div>`:null}
    ${r.justificativa?html`<p class="cap" style=${{marginTop:"10px"}}>${r.justificativa}</p>`:null}
    ${r.recomendacao?html`<div style=${{marginTop:"10px",padding:"11px 13px",borderRadius:"12px",background:"var(--brand-soft)",fontSize:"13.5px",color:"var(--text-primary)"}}>
      <b style=${{color:"var(--brand-dark)"}}>🔧 Recomendação Fundalis:</b> ${r.recomendacao}</div>`:null}
    ${r.relacionados&&r.relacionados.length?html`<div style=${{marginTop:"12px"}}>
      <div class="cap" style=${{fontWeight:700,marginBottom:"7px"}}>Peças Fundalis relacionadas</div>
      ${r.relacionados.map((p,i)=>html`<div key=${i} style=${{border:"1px solid var(--card-b)",borderRadius:"12px",padding:"9px 12px",marginBottom:"7px",background:"var(--surface-2)",display:"flex",justifyContent:"space-between",gap:"8px",alignItems:"center"}}>
        <span style=${{fontSize:"13.5px"}}><b>${p.nome}</b>${p.marca?html` <span class="cap">· ${p.marca}</span>`:""}</span><span class="cap">${brl(p.preco)}</span></div>`)}</div>`:null}
  </div>`;
}

const SUGEST = [
  "Qual o desconto para 8 mil peças por ano?",
  "Qual o critério de aceitação de porosidade em peças classe B?",
  "Quais os 5 produtos que mais vendem?",
  "Quantos leads quentes temos por segmento?",
  "Qual a fundição com maior refugo no 3T26?",
  "O que causa rechupe e como controlar?",
  "A Fundalis é melhor que as concorrentes?",
  "Me passe o telefone e o CNPJ dos clientes quentes",
];
const novoConv=()=> (crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random());

/* ============ ABA — Agente (chat) ============ */
function StepMark({ estado }){
  if(estado==="run") return html`<span class="mkspin"></span>`;
  if(estado==="done") return html`<span>✓</span>`;
  if(estado==="block") return html`<span>🛡️</span>`;
  return html`<span>·</span>`;
}
function AgentSteps({ steps }){
  if(!steps||!steps.length) return html`<div class="steps"><div class="sh"><span class="mkspin"></span>O agente está pensando…</div></div>`;
  const bloq=steps.some(s=>s.estado==="block");
  return html`<div class=${"steps"+(bloq?" blocked":"")}><div class="sh">${bloq?"🛡️ Bloqueado pelo guardrail":html`<span class="mkspin"></span>O agente está trabalhando`}</div>
    ${steps.map((s,i)=>html`<div key=${i} class=${"stp "+s.estado}><span class="mk"><${StepMark} estado=${s.estado}/></span>${s.label}</div>`)}
  </div>`;
}
/* processamento que gerou a resposta: vermelho e aberto quando o guardrail bloqueou, recolhido nos demais casos */
function PassosResposta({ passos, bloqueado }){
  if(!passos||!passos.length) return null;
  const lst=passos.map((s,i)=>html`<div key=${i} class=${"stp "+s.estado}><span class="mk"><${StepMark} estado=${s.estado}/></span>${s.label}</div>`);
  if(bloqueado||passos.some(s=>s.estado==="block")) return html`<div class="steps past blocked"><div class="sh">🛡️ ${bloqueado?"Bloqueado pelo guardrail":"Resposta ajustada pelo guardrail"}</div>${lst}</div>`;
  return html`<details class="steps past"><summary>ver processamento (${passos.length} passos)</summary>${lst}</details>`;
}
function DocsPainel({ rk }){
  const [d,setD]=useState(null); const [m,setM]=useState(null);
  useEffect(()=>{ api("/api/docs/lista").then(setD).catch(()=>setD({documentos:[]})); api("/api/memoria").then(setM).catch(()=>{}); },[rk]);
  const docs=(d&&d.documentos)||[];
  return html`<${Fragment}>
    <div class="blk"><h4>Memória do agente · Lakebase</h4>
      <div style=${{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:"8px"}}>
        <div class="kpi" style=${{padding:"9px 10px"}}><div class="lbl">Vetores</div><div class="val" style=${{fontSize:"18px"}}>${m&&m.rag?fmt(m.rag.trechos):"…"}</div></div>
        <div class="kpi" style=${{padding:"9px 10px"}}><div class="lbl">Cache</div><div class="val" style=${{fontSize:"18px"}}>${m&&m.cache?fmt(m.cache.entradas):"…"}</div></div>
        <div class="kpi" style=${{padding:"9px 10px"}}><div class="lbl">Hits</div><div class="val accent" style=${{fontSize:"18px"}}>${m&&m.cache?fmt(m.cache.hits):"…"}</div></div>
      </div>
      <p class="cap" style=${{marginTop:"6px",fontSize:"11.5px"}}>pgvector/HNSW · limiar de distância ${m?m.limiar_distancia:"—"} · TTL ${m?m.ttl_h:"—"}h</p></div>
    <div class="blk"><h4>Documentos indexados (${docs.length})</h4>
      ${docs.map((x,i)=>html`<div key=${i} style=${{padding:"7px 0",borderBottom:"1px solid var(--grid)",fontSize:"12.5px"}}>
        <div>📄 <b>${x.arquivo}</b></div><div class="cap" style=${{fontSize:"11px"}}>${x.paginas||"?"} pág · ${x.trechos} trechos (Delta) · ${x.vetores_lakebase} vetores (Lakebase)</div></div>`)}
      <p class="cap" style=${{marginTop:"6px",fontSize:"11.5px"}}>PDFs lidos com <b>ai_parse_document</b>; o Genie também consulta os trechos.</p></div>
  </${Fragment}>`;
}
/* grafo do agente: Mermaid gerado pelo LangGraph (agente.py) no backend */
let _mmdN=0;
function MermaidSvg({ code }){
  const [svg,setSvg]=useState(null); const [erro,setErro]=useState(null);
  useEffect(()=>{ if(!code||!window.mermaid) return; let vivo=true;
    try{ window.mermaid.initialize({startOnLoad:false,securityLevel:"strict",theme:document.body.classList.contains("dark")?"dark":"neutral",flowchart:{curve:"basis"}}); }catch(_){}
    window.mermaid.render("mmd"+(++_mmdN),code).then(r=>{ if(vivo) setSvg(r.svg); }).catch(e=>{ if(vivo) setErro(String(e.message||e)); });
    return ()=>{ vivo=false; }; },[code]);
  if(erro) return html`<pre class="cap" style=${{whiteSpace:"pre-wrap"}}>${code}</pre>`;
  return svg?html`<div class="grafo" dangerouslySetInnerHTML=${{__html:svg}}></div>`:html`<span class="spin"></span>`;
}
function GrafoAgente(){
  const [g,setG]=useState(null); const [modal,setModal]=useState(null); const [cod,setCod]=useState(null);
  useEffect(()=>{ api("/api/agente/grafo").then(setG).catch(()=>setG({})); },[]);
  const verCodigo=()=>{ setModal("codigo"); if(cod==null) fetch("/api/agente/codigo").then(r=>r.text()).then(setCod).catch(()=>setCod("(não consegui carregar o código)")); };
  return html`<div class="blk"><h4>Grafo do agente · LangGraph</h4>
    ${g==null?html`<span class="spin"></span>`:g.mermaid?html`<div style=${{cursor:"zoom-in"}} title="Ampliar" onClick=${()=>setModal("grafo")}><${MermaidSvg} code=${g.mermaid}/></div>`:html`<p class="cap">Grafo indisponível.</p>`}
    <div style=${{display:"flex",gap:"6px",marginTop:"8px"}}>
      <button class="restart" onClick=${()=>setModal("grafo")}>⤢ Ampliar</button>
      <button class="restart" onClick=${()=>setModal("mermaid")}>Mermaid</button>
      <button class="restart" onClick=${verCodigo}>Código (agente.py)</button></div>
    <p class="cap" style=${{marginTop:"6px",fontSize:"11.5px"}}>StateGraph executado a cada pergunta: genie ∥ rag rodam em paralelo; os passos ao vivo vêm dos nós.</p>
    ${modal?html`<div class="grafo-modal" onClick=${()=>setModal(null)}><div onClick=${(e)=>e.stopPropagation()}>
      <div style=${{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"10px",marginBottom:"10px"}}>
        <b>${modal==="codigo"?"agente.py — orquestração em LangGraph":modal==="mermaid"?"Mermaid gerado por grafo.get_graph().draw_mermaid()":"Grafo do agente (LangGraph)"}</b>
        <button class="restart" onClick=${()=>setModal(null)}>Fechar</button></div>
      ${modal==="grafo"?html`<div style=${{minWidth:"min(700px,85vw)"}}><${MermaidSvg} code=${g&&g.mermaid}/></div>`
        :modal==="mermaid"?html`<pre>${g&&g.mermaid}</pre>`
        :html`<pre>${cod==null?"carregando…":cod}</pre>`}
    </div></div>`:null}
  </div>`;
}
const SAUDACAO={who:"ai",texto:"Olá! Sou o assistente de IA da **Fundalis** (Opus 4.8 com guardrails). ⚙️\nPergunte sobre vendas, leads, produtos e qualidade — eu consulto o **Genie** (tabelas e PDFs) e os **documentos** indexados no Lakebase. Use o 📎 para enviar um PDF (ele é lido com ai_parse_document) ou o 📷 para inspecionar a foto de uma peça. Todos os dados são fictícios."};
function Assistente(){
  const [msgs,setMsgs]=useState([SAUDACAO]);
  const [q,setQ]=useState(""); const [busy,setBusy]=useState(false); const [steps,setSteps]=useState([]);
  const [rk,setRk]=useState(0);
  const endRef=useRef(null); const convRef=useRef(novoConv()); const genieRef=useRef(null); const abortRef=useRef(null);
  const imgFileRef=useRef(null); const [imgAtiva,setImgAtiva]=useState(false); const [pendingImg,setPendingImg]=useState(null);
  const scrollDown=()=>setTimeout(()=>endRef.current&&endRef.current.scrollIntoView({behavior:"smooth"}),60);
  const reiniciar=()=>{ if(busy)return; setMsgs([SAUDACAO]); convRef.current=novoConv(); genieRef.current=null; setSteps([]); setQ(""); imgFileRef.current=null; setImgAtiva(false); setPendingImg(null); };
  const parar=()=>{ if(abortRef.current) abortRef.current.abort(); };
  const enviarDoc=async(file)=>{
    if(!file||busy) return;
    setMsgs(m=>[...m,{who:"me",texto:"📎 "+file.name}]); setBusy(true);
    setSteps([{id:"up",label:"Enviando para o Volume do Unity Catalog",estado:"run"}]); scrollDown();
    try{
      const fd=new FormData(); fd.append("file",file);
      const j=await apiForm("/api/docs/upload",fd);
      let st=null;
      for(let i=0;i<120;i++){
        await new Promise(r=>setTimeout(r,2500));
        const s=await api("/api/docs/status"); st=(s.processos||{})[j.arquivo];
        if(st) setSteps([{id:"up",label:"Upload no Volume",estado:"done"},{id:"p",label:st.etapa,estado:st.estado==="processando"?"run":(st.estado==="ok"?"done":"block")}]);
        if(st&&st.estado!=="processando") break;
      }
      if(st&&st.estado==="ok") setMsgs(m=>[...m,{who:"ai",texto:`Pronto! Li **${j.arquivo}** com **ai_parse_document**, separei **${st.trechos} trechos** por seção (tabela documentos_chunks, usada pelo Genie) e gravei os embeddings no **Lakebase** para a busca vetorial. Pode perguntar sobre ele.`,ferramentas:["Documentos (RAG)"]}]);
      else setMsgs(m=>[...m,{who:"ai",texto:"Não consegui processar o documento: "+((st&&st.erro)||"tempo esgotado")}]);
    }catch(e){ setMsgs(m=>[...m,{who:"ai",texto:"Falha no upload: "+e.message}]); }
    setBusy(false); setSteps([]); setRk(x=>x+1); scrollDown();
  };
  const conversarFoto=async(p)=>{
    const hist=msgs.map(m=>({who:m.who,texto:m.texto})).slice(-8);
    setMsgs(m=>[...m,{who:"me",texto:p}]); setBusy(true);
    setSteps([{id:"vis",label:"Analisando a foto para responder",estado:"run"}]); scrollDown();
    try{ const fd=new FormData(); fd.append("file",imgFileRef.current); fd.append("pergunta",p); fd.append("historico",JSON.stringify(hist));
      const j=await apiForm("/api/cultura/conversar",fd);
      setMsgs(m=>[...m,{who:"ai",texto:j.resposta,ferramentas:[j.bloqueado?"Guardrail":"Visão"]}]);
    }catch(e){ setMsgs(m=>[...m,{who:"ai",texto:"Não consegui analisar a imagem: "+e.message}]); }
    setBusy(false); setSteps([]); scrollDown();
  };
  const enviar=async(texto)=>{ const p=(texto??q).trim(); if(busy)return;
    if(pendingImg){ const pi=pendingImg; setPendingImg(null); setQ(""); return mandarFoto(pi.file, p, pi.url); }
    if(!p)return; setQ("");
    if(imgAtiva && imgFileRef.current){ return conversarFoto(p); }
    setMsgs(m=>[...m,{who:"me",texto:p}]); setBusy(true); setSteps([]); scrollDown();
    const ac=new AbortController(); abortRef.current=ac;
    let passos=[];   // cópia local p/ anexar à resposta final
    const junta=(cur,o)=>{ const i=cur.findIndex(s=>s.id===o.id);
      if(i<0) return [...cur,{id:o.id,label:o.label,estado:o.estado}];
      const n=cur.slice(); n[i]={id:o.id,label:o.label,estado:o.estado}; return n; };
    const upd=(o)=>{ passos=junta(passos,o); setSteps(cur=>junta(cur,o)); };
    try{
      const r=await fetch("/api/chat/stream",{method:"POST",headers:{"Content-Type":"application/json"},signal:ac.signal,
        body:JSON.stringify({pergunta:p,conv_id:convRef.current,genie_conv:genieRef.current})});
      if(!r.ok||!r.body) throw new Error("HTTP "+r.status);
      const reader=r.body.getReader(); const dec=new TextDecoder(); let buf=""; let done=false;
      while(!done){
        const {value,done:dn}=await reader.read(); done=dn;
        buf+=dec.decode(value||new Uint8Array(),{stream:!dn});
        let nl; while((nl=buf.indexOf("\n"))>=0){
          const line=buf.slice(0,nl).trim(); buf=buf.slice(nl+1);
          if(!line) continue;
          let o; try{o=JSON.parse(line);}catch(_){continue;}
          if(o.tipo==="passo"){ upd(o); scrollDown(); }
          else if(o.tipo==="final"){
            if(o.genie_conv) genieRef.current=o.genie_conv;
            setMsgs(m=>[...m,{who:"ai",texto:o.resposta,cards:o.cards,fontes:o.fontes,ferramentas:o.ferramentas,sql:o.sql,
              assunto:o.assunto,cache:o.cache,bloqueado:o.bloqueado,ms:o.ms,passos}]);
          }
        }
      }
    }catch(e){ if(e.name==="AbortError") setMsgs(m=>[...m,{who:"ai",texto:"Resposta interrompida."}]);
               else setMsgs(m=>[...m,{who:"ai",texto:"Ops, algo falhou: "+e.message}]); }
    setBusy(false); setSteps([]); abortRef.current=null; setRk(x=>x+1); scrollDown();
  };
  const mandarFoto=async(file,pergunta,url)=>{
    if(!file||busy) return;
    imgFileRef.current=file;
    const hist=msgs.map(m=>({who:m.who,texto:m.texto})).slice(-8);
    setMsgs(m=>[...m,{who:"me",img:url,texto:(pergunta||null)}]); setBusy(true);
    setSteps([{id:"vis",label:(pergunta?"Analisando a foto para responder":"Analisando a foto e inspecionando a peça"),estado:"run"}]); scrollDown();
    try{
      if(pergunta){
        const fd=new FormData(); fd.append("file",file); fd.append("pergunta",pergunta); fd.append("historico",JSON.stringify(hist));
        const j=await apiForm("/api/cultura/conversar",fd);
        setMsgs(m=>[...m,{who:"ai",texto:j.resposta,ferramentas:[j.bloqueado?"Guardrail":"Visão"]}]);
      } else {
        const fd=new FormData(); fd.append("file",file);
        const j=await apiForm("/api/cultura/identificar",fd);
        const ok=j.cultura&&j.cultura!=="Não identificado";
        const txt=ok?("Identifiquei: **"+j.cultura+"**"+(j.sanidade?" · "+j.sanidade:"")+". "+(j.recomendacao||"Posso recomendar a ação de processo/inspeção."))
          :"Não identifiquei uma peça fundida nesta foto. Tente uma imagem mais próxima da peça ou da região do defeito.";
        setMsgs(m=>[...m,{who:"ai",texto:txt,equip:(ok?j:null),ferramentas:["Visão"]}]);
      }
      setImgAtiva(true);
    }catch(e){ setMsgs(m=>[...m,{who:"ai",texto:"Não consegui analisar a imagem: "+e.message}]); }
    setBusy(false); setSteps([]); scrollDown();
  };
  const toolIcon=(t)=>({Web:"🌐",Mapa:"🗺️",Genie:"✨",Guardrail:"🛡️","Visão":"📷","Cache Lakebase":"⚡","Documentos (RAG)":"📄"})[t]||"📚";
  return html`<div class="agent">
    <div class="col">
      <div class="msgs"><div class="chat">
      ${msgs.map((m,i)=> m.who==="me"
        ? html`<div key=${i} class="bubble me">${m.img?html`<img src=${m.img} class="chatimg"/>`:null}${m.texto?html`<div style=${{marginTop:m.img?"6px":0}}>${m.texto}</div>`:null}</div>`
        : html`<div key=${i} class="ai-row">
            <img src="/static/avatar.svg" class="avatar" alt="Fundalis"/>
            <div class="ai-wrap" style=${{flex:1,minWidth:0}}>
              <${PassosResposta} passos=${m.passos} bloqueado=${m.bloqueado}/>
              <div class=${"bubble ai"+(m.bloqueado||(m.passos||[]).some(s=>s.estado==="block")?" blocked":"")} style=${{maxWidth:"100%"}}>${mdInline(m.texto)}
                ${m.ferramentas&&m.ferramentas.length?html`<div class="tools-row">${m.ferramentas.map((t,j)=>html`<span key=${j} class=${"toolpill"+(t==="Cache Lakebase"?" web":t==="Guardrail"?" guard":"")}>${toolIcon(t)} ${t}</span>`)}</div>`:null}
              </div>
              ${(m.cards||[]).map((c,j)=>html`<${ResCard} key=${j} c=${c}/>`)}
              ${m.equip?html`<${EquipResultado} r=${m.equip}/>`:null}
              ${m.fontes&&m.fontes.filter(f=>f.tipo==="DOC").length?html`<div class="src">📄 ${m.fontes.filter(f=>f.tipo==="DOC").map((f,j)=>html`<span key=${j}>${j?" · ":""}${f.arquivo} (p. ${f.pagina} · ${f.secao}) <span class="cap">${f.similaridade}</span></span>`)}</div>`:null}
              ${m.sql?html`<div class="src">📊 Fonte: ${tabelasDeSql(m.sql)} (Genie)</div>`:null}
              ${m.assunto||m.cache?html`<div class="src">${m.assunto?html`🏷️ ${m.assunto}`:null}${m.cache&&m.cache.hit?html` · ⚡ cache Lakebase (similaridade ${m.cache.similaridade})`:null}${m.ms?html` · ${(m.ms/1000).toFixed(1)}s`:null}</div>`:null}
            </div>
          </div>`)}
      ${busy&&html`<${AgentSteps} steps=${steps}/>`}
      <div ref=${endRef}></div>
      </div></div>
      <div class="composer"><div style=${{width:"100%"}}>
        ${pendingImg?html`<div class="imgctx">
          <img src=${pendingImg.url} style=${{width:"34px",height:"34px",borderRadius:"8px",objectFit:"cover",flex:"none"}}/>
          <span>Foto anexada — escreva sua pergunta (ou envie sem texto para inspecionar a peça)</span>
          <button onClick=${()=>setPendingImg(null)} title="Remover foto">✕</button></div>`
        :imgAtiva?html`<div class="imgctx">
          <span>📷 Conversando sobre a foto da peça — pergunte o que quiser sobre ela</span>
          <button onClick=${()=>{imgFileRef.current=null;setImgAtiva(false);}} title="Sair da foto">✕</button></div>`:null}
        <div class="in">
          <input id="chatFile" type="file" accept="image/*" style=${{position:"absolute",width:"1px",height:"1px",opacity:0,overflow:"hidden"}}
            onChange=${(e)=>{const f=e.target.files&&e.target.files[0]; if(f) setPendingImg({file:f,url:URL.createObjectURL(f)}); try{e.target.value="";}catch(_){}}}/>
          <input id="docFile" type="file" accept=".pdf,.docx,.pptx,application/pdf" style=${{position:"absolute",width:"1px",height:"1px",opacity:0,overflow:"hidden"}}
            onChange=${(e)=>{const f=e.target.files&&e.target.files[0]; if(f) enviarDoc(f); try{e.target.value="";}catch(_){}}}/>
          <label class="cam" htmlFor="docFile" style=${{pointerEvents:busy?"none":"auto",opacity:busy?.55:1}} title="Enviar PDF (ai_parse_document)">📎</label>
          <label class=${"cam"+(pendingImg?" on":"")} htmlFor="chatFile" style=${{pointerEvents:busy?"none":"auto",opacity:busy?.55:1}} title="Anexar foto da peça">📷</label>
          <input placeholder=${pendingImg?"Pergunte algo sobre a foto…":imgAtiva?"Pergunte sobre a foto…":"Pergunte à IA da Fundalis… (Enter para enviar)"} value=${q} onInput=${(e)=>setQ(e.target.value)}
            onKeyDown=${(e)=>e.key==="Enter"&&enviar()} autoFocus/>
          <button class=${"send"+(busy?" stop":"")} onClick=${()=>busy?parar():enviar()} title=${busy?"Interromper":"Enviar"}>${busy?"■":"➤"}</button>
        </div>
      </div></div>
    </div>
    <aside class="aside">
      <div class="blk" style=${{display:"flex",gap:"8px"}}>
        <button class="restart" disabled=${busy} onClick=${reiniciar}>↺ Nova conversa</button>
        <label class="restart" htmlFor="docFile" style=${{cursor:"pointer"}}>📎 Enviar PDF</label>
      </div>
      <div class="blk"><h4>Sugestões</h4>
        <div style=${{display:"flex",flexDirection:"column",gap:"6px"}}>
          ${SUGEST.map((s,i)=>html`<span key=${i} class="chip" style=${{whiteSpace:"normal",lineHeight:"1.35",borderRadius:"10px"}} onClick=${()=>enviar(s)}>${s}</span>`)}</div></div>
      <${GrafoAgente}/>
      <${DocsPainel} rk=${rk}/>
    </aside>
  </div>`;
}

/* ============ ABA — Assuntos (inference table do AI Gateway → perguntas clusterizadas por assunto) ============ */
function Assuntos(){
  const [d,setD]=useState(null); const [busy,setBusy]=useState(false); const [h,setH]=useState(24); const [sel,setSel]=useState(null);
  const [mem,setMem]=useState(null);
  const load=()=>{ setBusy(true); api("/api/memoria").then(setMem).catch(()=>{});
    return api("/api/assuntos?horas="+h).then(setD).catch(()=>setD({clusters:[],total:0})).finally(()=>setBusy(false)); };
  useEffect(()=>{ load(); const t=setInterval(load,20000); return ()=>clearInterval(t); },[h]);
  const cl=(d&&d.clusters)||[]; const max=Math.max(1,...cl.map(c=>c.n));
  const horas=[...new Set(((d&&d.serie)||[]).map(s=>s.k))];
  const porHora=horas.map(k=>({rotulo:k,valor:((d&&d.serie)||[]).filter(s=>s.k===k).reduce((a,s)=>a+s.n,0)}));
  return html`<div class="view">
    <div>
      <div style=${{display:"flex",alignItems:"center",justifyContent:"space-between",gap:"8px",flexWrap:"wrap",marginBottom:"12px"}}>
        <div class="chips">${[[24,"24h"],[168,"7 dias"],[720,"30 dias"]].map(([v,l])=>html`<span key=${v} class=${"chip"+(h===v?" on":"")} onClick=${()=>setH(v)}>${l}</span>`)}</div>
        <button class="refresh" disabled=${busy} onClick=${load}>${busy?html`<span class="spin"></span>`:"↻"} Atualizar</button>
      </div>
      ${!d?html`<p class="cap"><span class="spin"></span> Lendo a inference table…</p>`:html`<div class="kgrid" style=${{marginTop:"4px",marginBottom:0}}>
        <div class="kpi"><div class="lbl">Perguntas</div><div class="val accent">${fmt(d.total)}</div><div class="sub">no período</div></div>
        <div class="kpi"><div class="lbl">Bloqueadas</div><div class="val warm">${fmt(d.bloqueadas)}</div><div class="sub">pelo guardrail 🛡️</div></div>
        <div class="kpi"><div class="lbl">Assuntos</div><div class="val">${fmt(cl.length)}</div><div class="sub">clusters</div></div>
        <div class="kpi"><div class="lbl">Última</div><div class="val" style=${{fontSize:"14px"}}>${d.ultima?String(d.ultima).slice(11,16):"—"}</div><div class="sub">UTC</div></div>
      </div>`}
    </div>
    <div class="g g-21 fill">
    <div class="card pane"><div class="pane-h"><h3>Clusters por assunto</h3><span class="cnt">${cl.length}</span></div>
      <p class="cap" style=${{marginBottom:"6px",flex:"none"}}>Clique em um assunto para ver as perguntas do cluster.</p>
      <div class="body">
      ${!cl.length?html`<p class="cap">Ainda sem perguntas registradas. Pergunte algo no Agente — a inference table do AI Gateway costuma registrar em 1–2 min.</p>`:null}
      ${cl.map((c,i)=>html`<div key=${i} style=${{margin:"9px 0",cursor:"pointer"}} onClick=${()=>setSel(sel===c.assunto?null:c.assunto)}>
        <div style=${{display:"flex",justifyContent:"space-between",fontSize:"13px",marginBottom:"3px",gap:"8px"}}>
          <span>${c.bloqueio?"🛡️ ":""}<b>${c.assunto}</b> <span class="cap">· ${c.usuarios} usuário(s)</span></span><b>${c.n}</b></div>
        <div style=${{height:"8px",borderRadius:"5px",background:"var(--grid)"}}><div style=${{height:"8px",borderRadius:"5px",width:(100*c.n/max)+"%",background:c.bloqueio?"var(--critical)":"var(--grad)"}}></div></div>
        ${sel===c.assunto?html`<div style=${{marginTop:"7px",paddingLeft:"8px",borderLeft:"3px solid var(--brand-soft)"}}>
          ${c.exemplos.map((e,j)=>html`<div key=${j} style=${{fontSize:"12.5px",padding:"4px 0"}}>${e.permitido===false||e.permitido==="false"?"🛡️":"💬"} ${e.pergunta}
            <div class="cap" style=${{fontSize:"10.5px"}}>${e.requester||""} · ${String(e.ts||"").slice(0,16)}</div></div>`)}
        </div>`:null}
      </div>`)}
      </div>
      ${d&&d.tabela?html`<p class="cap" style=${{marginTop:"8px",flex:"none"}}>Fonte: <code>${d.fonte}</code> → persistido em <code>${d.tabela}</code> (MERGE incremental) — também disponível no Genie.</p>`:null}
    </div>
    <div class="stack">
    <div class="card pane fill"><div class="pane-h"><h3>Perguntas por ${h<=48?"hora (UTC)":"dia"}</h3></div>
      <div class="body">${porHora.length?html`<${Bars} items=${porHora} colorVar="--brand"/>`:html`<p class="cap">Sem perguntas no período.</p>`}</div></div>
    ${mem&&mem.cache?html`<div class="card pane fill"><div class="pane-h"><h3>🧠 Memória do agente · Lakebase</h3></div><div class="body">
      <div class="kgrid" style=${{marginTop:"6px",gridTemplateColumns:"1fr 1fr"}}>
        <div class="kpi"><div class="lbl">Cache</div><div class="val">${fmt(mem.cache.entradas)}</div><div class="sub">respostas</div></div>
        <div class="kpi"><div class="lbl">Hits de cache</div><div class="val accent">${fmt(mem.cache.hits)}</div><div class="sub">chamadas economizadas</div></div>
        <div class="kpi"><div class="lbl">Vetores RAG</div><div class="val">${fmt(mem.rag.trechos)}</div><div class="sub">${mem.rag.arquivos} documento(s)</div></div>
        <div class="kpi"><div class="lbl">Conversas</div><div class="val">${fmt(mem.conversas.conversas)}</div><div class="sub">${fmt(mem.conversas.mensagens)} mensagens</div></div>
      </div>
      ${mem.top&&mem.top.length?html`<div class="cap" style=${{fontWeight:700,margin:"10px 0 4px"}}>Perguntas mais reaproveitadas do cache</div>
        ${mem.top.map((t,i)=>html`<div key=${i} style=${{display:"flex",justifyContent:"space-between",gap:"8px",fontSize:"12.5px",padding:"3px 0"}}><span>${t.pergunta}</span><span class="cap">${t.hits}× · ${t.escopo}</span></div>`)}`:null}
    </div></div>`:null}
    </div></div>
  </div>`;
}

/* ============ helpers de formulário/ações ============ */
const jpost=(url,body,method="POST")=>api(url,{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
const kb=(n)=>n>=1048576?fmt1(n/1048576)+" MB":Math.max(1,Math.round((n||0)/1024))+" KB";
const dt=(s)=>s?String(s).slice(0,16).replace("T"," "):"—";
function Btn({ onClick, children, kind, disabled, title }){
  const st={border:"1px solid var(--card-b)",background:kind==="pri"?"var(--grad)":kind==="del"?"color-mix(in srgb,var(--critical) 10%,transparent)":"var(--surface-1)",
    color:kind==="pri"?"#fff":kind==="del"?"var(--critical)":"var(--text-primary)",borderColor:kind==="del"?"color-mix(in srgb,var(--critical) 40%,transparent)":kind==="pri"?"transparent":"var(--card-b)",
    font:"inherit",fontSize:"12.5px",fontWeight:600,padding:"6px 11px",borderRadius:"9px",cursor:disabled?"default":"pointer",opacity:disabled?.55:1,whiteSpace:"nowrap"};
  return html`<button style=${st} disabled=${disabled} onClick=${onClick} title=${title}>${children}</button>`;
}
function DropZone({ id, accept, onFile, label, sub, multiple, busy, erro }){
  const [over,setOver]=useState(false);
  const arquivos=(dt)=>{ if(!dt) return [];
    if(dt.files&&dt.files.length) return Array.from(dt.files);
    return Array.from(dt.items||[]).filter(i=>i.kind==="file").map(i=>i.getAsFile()).filter(Boolean); };
  const pick=(fs)=>{ const arr=Array.from(fs||[]); if(!arr.length||busy) return; multiple?arr.forEach(onFile):onFile(arr[0]); };
  const sobre=(e)=>{ e.preventDefault(); e.stopPropagation(); if(e.dataTransfer) e.dataTransfer.dropEffect="copy"; setOver(true); };
  return html`<${Fragment}><label htmlFor=${id} onDragEnter=${sobre} onDragOver=${sobre}
      onDragLeave=${(e)=>{ if(!e.currentTarget.contains(e.relatedTarget)) setOver(false); }}
      onDrop=${(e)=>{e.preventDefault();e.stopPropagation();setOver(false);pick(arquivos(e.dataTransfer));}}
      style=${{display:"block",border:"2px dashed var(--brand)",borderRadius:"14px",padding:"14px 16px",textAlign:"center",cursor:busy?"default":"pointer",
        background:over?"color-mix(in srgb,var(--brand) 22%,transparent)":"var(--brand-soft)",opacity:busy?.7:1,transition:"background .12s"}}>
    <input id=${id} type="file" accept=${accept} multiple=${!!multiple} style=${{display:"none"}} disabled=${busy}
      onChange=${(e)=>{pick(e.target.files); try{e.target.value="";}catch(_){}}}/>
    <div style=${{fontSize:"22px"}}>${busy?html`<span class="spin"></span>`:over?"📥":"📄"}</div>
    <div style=${{fontWeight:700,color:"var(--brand-dark)",marginTop:"4px"}}>${over?"Solte o arquivo aqui":label}</div>
    ${sub?html`<div class="cap">${sub}</div>`:null}
  </label>${erro?html`<p class="cap" style=${{color:"var(--critical)",marginTop:"8px"}}>⚠️ ${erro}</p>`:null}</${Fragment}>`;
}
/* soltar um arquivo fora da área não deve fazer o navegador abrir o PDF e sair do app */
window.addEventListener("dragover",(e)=>e.preventDefault()); window.addEventListener("drop",(e)=>e.preventDefault());

/* ============ ABA — Documentos (base de conhecimento do agente) ============ */
function Documentos(){
  const [d,setD]=useState(null); const [rk,setRk]=useState(0); const [proc,setProc]=useState({});
  const [meta,setMeta]=useState({titulo:"",categoria:"",descricao:""}); const [sel,setSel]=useState(null); const [erro,setErro]=useState(null);
  const [filtro,setFiltro]=useState("");
  useEffect(()=>{ api("/api/docs/lista").then(setD).catch(e=>setErro(e.message)); },[rk]);
  const algumProc=Object.values(proc).some(p=>p.estado==="processando");
  useEffect(()=>{ if(!algumProc) return; const t=setInterval(()=>api("/api/docs/status").then(s=>{ setProc(s.processos||{});
      if(!Object.values(s.processos||{}).some(p=>p.estado==="processando")) setRk(x=>x+1); }).catch(()=>{}),2500); return ()=>clearInterval(t); },[algumProc]);
  const enviar=async(f)=>{ setErro(null);
    const fd=new FormData(); fd.append("file",f); fd.append("titulo",meta.titulo); fd.append("categoria",meta.categoria); fd.append("descricao",meta.descricao);
    try{ const j=await apiForm("/api/docs/upload",fd); setProc(p=>({...p,[j.arquivo]:{estado:"processando",etapa:"upload"}})); setMeta({titulo:"",categoria:"",descricao:""}); }
    catch(e){ setErro(e.message); } };
  const reproc=async(a)=>{ await api("/api/docs/reprocessar?arquivo="+encodeURIComponent(a),{method:"POST"}); setProc(p=>({...p,[a]:{estado:"processando",etapa:"fila"}})); };
  const remover=async(a)=>{ if(!confirm(`Remover "${a}" do Volume, das tabelas Delta e dos vetores do Lakebase?`)) return;
    try{ await api("/api/docs?arquivo="+encodeURIComponent(a),{method:"DELETE"}); if(sel===a) setSel(null); setRk(x=>x+1);}catch(e){ setErro(e.message);} };
  const docs=((d&&d.documentos)||[]).filter(x=>!filtro||(x.arquivo+" "+(x.titulo||"")+" "+(x.categoria||"")).toLowerCase().includes(filtro.toLowerCase()));
  const cats=(d&&d.categorias)||[];
  const pend=Object.entries(proc).filter(([a,p])=>p.estado!=="ok"||!((d&&d.documentos)||[]).some(x=>x.arquivo===a));
  return html`<div class="view">
    <style>${`.inp{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:10px;border:1px solid var(--card-b);background:var(--surface-2);color:var(--text-primary);font-size:13.5px;margin-bottom:8px;font-family:inherit}`}</style>
    <div class="g g-12 stretch">
      <div class="card"><h3>Enviar documentos</h3>
        <p class="cap" style=${{marginBottom:"10px"}}>O arquivo vai para o Volume <code>${d?d.volume:"…"}</code>, é lido com <b>ai_parse_document</b>, dividido em trechos por seção (Delta, usado pelo Genie) e indexado com embeddings no <b>Lakebase</b> (RAG do agente).</p>
        <div style=${{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"0 8px"}}>
          <input class="inp" placeholder="Título (opcional — padrão: título do PDF)" value=${meta.titulo} onInput=${(e)=>setMeta({...meta,titulo:e.target.value})}/>
          <select class="inp" value=${meta.categoria} onChange=${(e)=>setMeta({...meta,categoria:e.target.value})}><option value="">Categoria</option>${cats.map(c=>html`<option key=${c}>${c}</option>`)}</select>
        </div>
        <input class="inp" placeholder="Descrição (opcional)" value=${meta.descricao} onInput=${(e)=>setMeta({...meta,descricao:e.target.value})}/>
        <${DropZone} id="kbFiles" accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg" multiple=${true} onFile=${enviar} label="Arraste arquivos aqui ou clique para escolher" sub="PDF, DOCX, PPTX ou imagem · até 40 MB · use apenas documentos fictícios" erro=${erro}/>
      </div>
      <div class="card"><h3>Processamento</h3>
        ${!pend.length?html`<p class="cap">Nenhum documento em processamento. Envie um arquivo para indexar.</p>`:pend.map(([a,p])=>html`<div key=${a} style=${{display:"flex",gap:"8px",alignItems:"center",padding:"6px 0",borderBottom:"1px solid var(--grid)",fontSize:"13px"}}>
          <span>${p.estado==="processando"?html`<span class="spin"></span>`:p.estado==="ok"?"✅":"⚠️"}</span><b style=${{flex:1}}>${a}</b>
          <span class="cap">${p.estado==="erro"?p.erro:p.etapa}</span></div>`)}
        <div class="kgrid" style=${{gridTemplateColumns:"1fr 1fr 1fr",marginTop:"12px",marginBottom:0}}>
          <div class="kpi"><div class="lbl">Documentos</div><div class="val">${d?fmt(d.documentos.length):"…"}</div></div>
          <div class="kpi"><div class="lbl">Trechos</div><div class="val">${d?fmt(d.documentos.reduce((a,x)=>a+Number(x.trechos||0),0)):"…"}</div></div>
          <div class="kpi"><div class="lbl">Vetores</div><div class="val accent">${d?fmt(d.documentos.reduce((a,x)=>a+Number(x.vetores_lakebase||0),0)):"…"}</div></div>
        </div>
      </div>
    </div>
    <div class="g g-doc fill">
      <div class="card pane">
        <div class="pane-h">
          <h3>Base de conhecimento ${d?html`<span class="cnt">${docs.length}</span>`:null}</h3>
          <input class="inp" style=${{maxWidth:"260px",margin:0}} placeholder="Filtrar…" value=${filtro} onInput=${(e)=>setFiltro(e.target.value)}/>
        </div>
        ${d==null?html`<span class="spin"></span>`:html`<div class="body"><table class="dtable">
          <thead><tr><th>Documento</th><th>Categoria</th><th>Trechos · vetores</th><th>Atualizado</th><th></th></tr></thead>
          <tbody>${docs.map(x=>html`<tr key=${x.arquivo} style=${{background:sel===x.arquivo?"var(--brand-soft)":""}}>
            <td style=${{cursor:"pointer"}} onClick=${()=>setSel(x.arquivo)}><b>${x.titulo||x.arquivo}</b><div class="cap" style=${{fontSize:"11px"}} title=${"enviado por "+(x.enviado_por||"")}>${x.arquivo} · ${x.paginas||"?"} pág · ${kb(Number(x.tamanho))}</div></td>
            <td>${x.categoria?html`<span class="badge b-cold">${x.categoria}</span>`:html`<span class="cap">—</span>`}</td>
            <td>${x.trechos} · ${Number(x.vetores_lakebase)===Number(x.trechos)?html`<span class="badge b-cold" title="todos os trechos têm vetor no Lakebase">${x.vetores_lakebase} ✓</span>`:html`<span class="badge b-warm">${x.vetores_lakebase}</span>`}</td>
            <td class="cap">${dt(x.atualizado_em||x.processado_em)}</td>
            <td style=${{width:"170px"}}><div style=${{display:"flex",gap:"4px",justifyContent:"flex-end"}}>
              <${Btn} onClick=${()=>setSel(x.arquivo)} title="Editar metadados e trechos">✎</${Btn}>
              <a href=${"/api/docs/arquivo?arquivo="+encodeURIComponent(x.arquivo)} target="_blank" rel="noopener" style=${{textDecoration:"none"}}><${Btn} title="Baixar / visualizar">⬇</${Btn}></a>
              <${Btn} onClick=${()=>reproc(x.arquivo)} title="Reprocessar (ai_parse_document de novo)">↻</${Btn}>
              <${Btn} kind="del" onClick=${()=>remover(x.arquivo)} title="Remover do Volume, Delta e Lakebase">🗑</${Btn}></div></td>
          </tr>`)}</tbody></table></div>`}
        ${d&&!docs.length?html`<p class="cap">Nenhum documento.</p>`:null}
      </div>
      <div class="stack">${sel?html`<${DocDetalhe} key=${sel} doc=${((d&&d.documentos)||[]).find(x=>x.arquivo===sel)||{arquivo:sel}} cats=${cats}
          onChange=${()=>setRk(x=>x+1)} onClose=${()=>setSel(null)}/>`
        :html`<div class="card"><p class="cap">Selecione um documento (✎) para editar os metadados e os trechos indexados.</p></div>`}</div>
    </div>
  </div>`;
}
function DocDetalhe({ doc, cats, onChange, onClose }){
  const [m,setM]=useState({titulo:doc.titulo||"",categoria:doc.categoria||"",descricao:doc.descricao||""});
  const [tr,setTr]=useState(null); const [ed,setEd]=useState(null); const [txt,setTxt]=useState(""); const [busy,setBusy]=useState(false);
  const [novo,setNovo]=useState(""); const [ok,setOk]=useState(null);
  const carregar=()=>api("/api/docs/trechos?arquivo="+encodeURIComponent(doc.arquivo)).then(r=>setTr(r.trechos||[])).catch(()=>setTr([]));
  useEffect(()=>{ carregar(); },[]);
  const flash=(t)=>{ setOk(t); setTimeout(()=>setOk(null),2500); };
  const salvarMeta=async()=>{ setBusy(true); try{ await jpost("/api/docs/meta",{arquivo:doc.arquivo,...m},"PATCH"); flash("Metadados salvos"); onChange(); }catch(e){ alert(e.message);} setBusy(false); };
  const salvarTrecho=async(id)=>{ setBusy(true); try{ await jpost("/api/docs/trecho",{chunk_id:id,trecho:txt},"PATCH"); setEd(null); flash("Trecho salvo e re-indexado no Lakebase"); carregar(); onChange(); }catch(e){ alert(e.message);} setBusy(false); };
  const removerTrecho=async(id)=>{ if(!confirm("Remover este trecho do Delta e do Lakebase?")) return; await api("/api/docs/trecho?chunk_id="+encodeURIComponent(id),{method:"DELETE"}); carregar(); onChange(); };
  const addTrecho=async()=>{ if(!novo.trim()) return; setBusy(true); try{ await jpost("/api/docs/trecho",{arquivo:doc.arquivo,trecho:novo,secao:"Nota manual"}); setNovo(""); flash("Nota adicionada e indexada"); carregar(); onChange(); }catch(e){ alert(e.message);} setBusy(false); };
  return html`<div class="card pane fill">
    <div class="pane-h"><h3 style=${{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>📄 ${doc.arquivo}</h3><${Btn} onClick=${onClose}>Fechar</${Btn}></div>
    ${ok?html`<p class="cap" style=${{color:"var(--good)",marginBottom:"6px",flex:"none"}}>✓ ${ok}</p>`:null}
    <div class="body"><div>
      <input class="inp" placeholder="Título" value=${m.titulo} onInput=${(e)=>setM({...m,titulo:e.target.value})}/>
      <select class="inp" value=${m.categoria} onChange=${(e)=>setM({...m,categoria:e.target.value})}><option value="">Categoria</option>${cats.map(c=>html`<option key=${c}>${c}</option>`)}</select>
      <textarea class="inp" rows="2" placeholder="Descrição" value=${m.descricao} onInput=${(e)=>setM({...m,descricao:e.target.value})}></textarea>
      <${Btn} kind="pri" disabled=${busy} onClick=${salvarMeta}>Salvar metadados</${Btn}>
    </div>
    <div class="cap" style=${{fontWeight:700,margin:"16px 0 6px"}}>Trechos indexados (${tr?tr.length:"…"}) — editar re-gera o embedding no Lakebase</div>
    <div>
    ${tr==null?html`<span class="spin"></span>`:tr.map(t=>html`<div key=${t.chunk_id} style=${{border:"1px solid var(--card-b)",borderRadius:"10px",padding:"9px 11px",marginBottom:"8px",background:"var(--surface-2)"}}>
      <div style=${{display:"flex",justifyContent:"space-between",gap:"6px",alignItems:"center"}}>
        <span style=${{fontSize:"12.5px"}}><b>${t.secao||"(sem seção)"}</b> <span class="cap">· p. ${t.pagina} · ${t.chunk_id.split("#")[1]}</span></span>
        ${ed===t.chunk_id?null:html`<span style=${{display:"flex",gap:"5px"}}><${Btn} onClick=${()=>{setEd(t.chunk_id);setTxt(t.trecho);}}>Editar</${Btn}><${Btn} kind="del" onClick=${()=>removerTrecho(t.chunk_id)}>✕</${Btn}></span>`}
      </div>
      ${ed===t.chunk_id?html`<div style=${{marginTop:"6px"}}><textarea class="inp" rows="7" value=${txt} onInput=${(e)=>setTxt(e.target.value)}></textarea>
          <div style=${{display:"flex",gap:"6px"}}><${Btn} kind="pri" disabled=${busy} onClick=${()=>salvarTrecho(t.chunk_id)}>${busy?"Salvando…":"Salvar e re-indexar"}</${Btn}><${Btn} onClick=${()=>setEd(null)}>Cancelar</${Btn}></div></div>`
        :html`<div style=${{fontSize:"12.5px",marginTop:"4px",whiteSpace:"pre-wrap",color:"var(--text-secondary)",maxHeight:"120px",overflow:"hidden"}}>${t.trecho}</div>`}
    </div>`)}
    </div>
    <div class="cap" style=${{fontWeight:700,margin:"10px 0 6px"}}>Adicionar nota/correção ao documento</div>
    <textarea class="inp" rows="3" placeholder="Ex.: A partir de nov/26 o prazo de amostra passou a ser de 10 semanas (fictício)." value=${novo} onInput=${(e)=>setNovo(e.target.value)}></textarea>
    <${Btn} disabled=${busy||!novo.trim()} onClick=${addTrecho}>Adicionar trecho</${Btn}>
  </div></div>`;
}

/* ============ Cadastro — editor do prompt de extração (versionado no Lakebase) ============ */
function PromptEditor({ onSaved, onTestar, podeTestar }){
  const [d,setD]=useState(null); const [cfg,setCfg]=useState(null); const [nota,setNota]=useState(""); const [aberta,setAberta]=useState(null);
  const [busy,setBusy]=useState(false); const [msg,setMsg]=useState(null);
  const carrega=(r,v)=>{ const h=(r.historico||[]).find(x=>x.versao===v);
    const src=h||r.ativo; setCfg({modo:src.modo,modelo:src.modelo,prompt:src.prompt}); setNota((h&&h.nota)||""); setAberta(h?h.versao:(r.ativo.versao||0)); };
  const recarregar=(v)=>api("/api/prompts/cadastro").then(r=>{ setD(r); carrega(r, v!=null?v:(r.ativo.versao||0)); });
  useEffect(()=>{ recarregar(); },[]);
  if(!d||!cfg) return html`<div class="card"><span class="spin"></span></div>`;
  const hist=d.historico||[]; const atual=hist.find(h=>h.versao===aberta);
  const ativaV=d.ativo.versao||0; const ehAtiva=aberta===ativaV;
  const base=atual||d.ativo; const mod=d.modelos.find(m=>m.id===cfg.modelo)||{};
  const mudou=cfg.modo!==base.modo||cfg.modelo!==base.modelo||cfg.prompt!==base.prompt||(atual&&nota!==(atual.nota||""));
  const corpo=()=>({...cfg,nota});
  const run=async(fn,ok)=>{ setBusy(true); setMsg(null); try{ const r=await fn(); setMsg(ok(r)); onSaved&&onSaved(); }catch(e){ setMsg("⚠️ "+e.message);} setBusy(false); };
  const salvarNesta=()=>run(async()=>{ await jpost("/api/prompts/cadastro/"+aberta,corpo(),"PUT"); await recarregar(aberta); },()=>`v${aberta} atualizada`);
  const salvarNova=()=>run(async()=>{ const r=await jpost("/api/prompts/cadastro",{...corpo(),ativar:true}); await recarregar(r.versao); return r; },(r)=>`Salva como v${r.versao} (ativa)`);
  const ativar=(v)=>run(async()=>{ await api(`/api/prompts/cadastro/${v}/ativar`,{method:"POST"}); await recarregar(v); },()=>`v${v} agora é a ativa`);
  const excluir=(v)=>{ if(!confirm(`Excluir a v${v}? (não dá para desfazer)`)) return;
    run(async()=>{ await api("/api/prompts/cadastro/"+v,{method:"DELETE"}); await recarregar(v===aberta?null:aberta); },()=>`v${v} excluída`); };
  const padrao=()=>run(async()=>{ const r=await api("/api/prompts/cadastro/restaurar?versao=0",{method:"POST"}); await recarregar(r.versao); return r; },(r)=>`Padrão restaurado como v${r.versao}`);
  return html`<div class="card">
    <div style=${{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"8px"}}>
      <h3 style=${{margin:0}}>⚙️ Prompt de extração do cadastro</h3>
      <span style=${{display:"flex",gap:"6px"}}>
        <span class="badge b-warm">editando: ${aberta?"v"+aberta:"padrão"}</span>
        <span class="badge b-cold">ativa: ${ativaV?"v"+ativaV:"padrão"}</span></span></div>
    <p class="cap" style=${{margin:"4px 0 10px"}}>Define como o PDF vira cadastro. Variáveis: ${d.placeholders.map(p=>html`<code key=${p} style=${{marginRight:"6px"}}>${p}</code>`)} (<code>{texto}</code> só no modo ai_parse_document). Clique em <b>Editar</b> numa versão do histórico para alterá-la.</p>
    <div style=${{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"0 8px"}}>
      <select class="inp" value=${cfg.modo} onChange=${(e)=>setCfg({...cfg,modo:e.target.value})}>${d.modos.map(m=>html`<option key=${m.id} value=${m.id}>${m.nome}</option>`)}</select>
      <select class="inp" value=${cfg.modelo} onChange=${(e)=>setCfg({...cfg,modelo:e.target.value})}>${d.modelos.map(m=>html`<option key=${m.id} value=${m.id} disabled=${cfg.modo==="direto"&&!m.pdf_direto}>${m.nome}</option>`)}</select>
    </div>
    ${cfg.modo==="direto"&&!mod.pdf_direto?html`<p class="cap" style=${{color:"var(--critical)"}}>Esse modelo não lê PDF direto — escolha um Claude ou use ai_parse_document.</p>`:null}
    <textarea class="inp" rows="13" style=${{fontFamily:"ui-monospace,Menlo,monospace",fontSize:"12.5px"}} value=${cfg.prompt} onInput=${(e)=>setCfg({...cfg,prompt:e.target.value})}></textarea>
    <input class="inp" placeholder="Nota da versão — ex.: inclui cargo do contato na mensagem" value=${nota} onInput=${(e)=>setNota(e.target.value)}/>
    <div style=${{display:"flex",gap:"6px",flexWrap:"wrap",alignItems:"center"}}>
      ${aberta?html`<${Btn} kind="pri" disabled=${busy||!mudou} onClick=${salvarNesta} title="Sobrescreve esta versão">Salvar na v${aberta}</${Btn}>`:null}
      <${Btn} kind=${aberta?"":"pri"} disabled=${busy} onClick=${salvarNova} title="Cria uma versão nova e a torna ativa">Salvar como nova versão</${Btn}>
      ${aberta&&!ehAtiva?html`<${Btn} disabled=${busy} onClick=${()=>ativar(aberta)}>Ativar v${aberta}</${Btn}>`:null}
      <${Btn} disabled=${busy||!podeTestar} onClick=${()=>onTestar(cfg)} title=${podeTestar?"Re-extrai o último PDF com o que está no editor (sem salvar)":"Envie um PDF primeiro"}>Testar no último PDF</${Btn}>
      <${Btn} disabled=${busy} onClick=${()=>setCfg({...cfg,prompt:d.padrao})}>Carregar texto padrão</${Btn}>
      ${mudou?html`<${Btn} onClick=${()=>carrega(d,aberta)}>Descartar</${Btn}>`:null}
      ${msg?html`<span class="cap">${msg}</span>`:null}
    </div>
    <div class="cap" style=${{fontWeight:700,margin:"14px 0 4px"}}>Versões (${hist.length})</div>
    ${hist.map(h=>html`<div key=${h.versao} style=${{display:"flex",gap:"8px",alignItems:"center",padding:"7px 8px",borderRadius:"8px",fontSize:"12px",
        background:h.versao===aberta?"var(--brand-soft)":"transparent",borderBottom:"1px solid var(--grid)"}}>
      <b style=${{minWidth:"28px"}}>v${h.versao}</b>
      <span class="cap" style=${{flex:1}}>${h.modo==="direto"?"PDF direto":"ai_parse_document"} · ${(h.modelo||"").replace("system.ai.","")}${h.nota?" · "+h.nota:""}
        <br/><span style=${{fontSize:"11px"}}>${h.criado_por} · ${dt(h.criado_em)}${h.atualizado_em?" · editada por "+h.atualizado_por+" em "+dt(h.atualizado_em):""}</span></span>
      ${h.ativo?html`<span class="badge b-cold">ativa</span>`:null}
      <${Btn} disabled=${busy} onClick=${()=>{carrega(d,h.versao);setMsg(null);}}>Editar</${Btn}>
      ${!h.ativo?html`<${Btn} disabled=${busy} onClick=${()=>ativar(h.versao)}>Ativar</${Btn}>`:null}
      ${!h.ativo?html`<${Btn} kind="del" disabled=${busy} onClick=${()=>excluir(h.versao)}>Excluir</${Btn}>`:null}
    </div>`)}
    <div style=${{marginTop:"8px"}}><${Btn} disabled=${busy} onClick=${padrao}>Restaurar padrão do app (nova versão)</${Btn}></div>
  </div>`;
}

/* ============ ABA — Cadastro (Lakebase → CDC → Unity Catalog mascarado) ============ */
function CdcStatus({ rk }){
  const [d,setD]=useState(null);
  useEffect(()=>{ api("/api/cdc/status").then(setD).catch(()=>{}); },[rk]);
  const ts=(d&&d.tabelas)||[];
  return html`<div class="card" style=${{padding:"11px 14px"}}>
    ${ts.length?ts.map((t,i)=>html`<div key=${i} style=${{display:"flex",alignItems:"center",gap:"8px",fontSize:"12.5px",flexWrap:"wrap",padding:"2px 0"}}>
      <span class="badge b-cold">Lakebase</span><span>cadastro.${t.postgres}</span><span>→</span>
      <span class=${"badge "+(t.estado==="STREAMING"?"b-hot":"b-warm")}>CDC ${t.estado}</span><span>→</span>
      <span class="badge b-cold">Unity Catalog</span><span>${t.uc}</span><span>→</span><span class="badge b-warm">view</span><span>fundalis_ia.${t.postgres==="leads"?"leads (PII mascarada)":"leads_anexos"}</span>
      <span class="cap" style=${{marginLeft:"auto"}}>último sync ${dt(t.ultimo_sync)} UTC</span></div>`)
      :html`<span class="cap"><span class="spin"></span> status do CDC…</span>`}
  </div>`;
}
const LEAD_VAZIO={cliente_nome:"",email:"",telefone:"",documento:"",empresa:"",segmento:"",produto_nome:"",cidade:"",uf:"",canal:"",mensagem:""};
function Cadastro(){
  const [f,setF]=useState(LEAD_VAZIO); const [op,setOp]=useState(null); const [busy,setBusy]=useState(false);
  const [res,setRes]=useState(null); const [sync,setSync]=useState(null); const [lista,setLista]=useState(null); const [rk,setRk]=useState(0); const [erro,setErro]=useState(null);
  const [edit,setEdit]=useState(null);           // {lead, anexos, pii_liberado} quando editando
  const [reav,setReav]=useState(false);
  const [ext,setExt]=useState(null); const [extBusy,setExtBusy]=useState(false); const [extErro,setExtErro]=useState(null); const ultimoPdf=useRef(null);
  const [busca,setBusca]=useState(""); const [verPrompt,setVerPrompt]=useState(false); const esqRef=useRef(null);
  useEffect(()=>{ api("/api/cadastro/opcoes").then(setOp).catch(()=>{}); },[]);
  useEffect(()=>{ api("/api/cadastro/recentes?limit=100&busca="+encodeURIComponent(busca)).then(r=>setLista(r.leads||[])).catch(()=>setLista([])); },[rk,busca]);
  const set=(k)=>(e)=>setF({...f,[k]:e.target.value});
  const acompanhar=async(id)=>{ const t0=Date.now();
    for(let i=0;i<40;i++){
      try{ const s=await api("/api/cadastro/sync/"+id); s.lag_s=Math.round((Date.now()-t0)/1000); setSync(s); if(s.sincronizado){ setRk(x=>x+1); return; } }catch(_){}
      await new Promise(r=>setTimeout(r,3000));
    } };
  const extrair=async(file,over)=>{ if(!file) return; ultimoPdf.current=file; setExtBusy(true); setErro(null); setExtErro(null);
    try{ const fd=new FormData(); fd.append("file",file);
      if(over){ fd.append("modo",over.modo); fd.append("modelo",over.modelo); fd.append("prompt",over.prompt); }
      const j=await apiForm("/api/cadastro/extrair",fd,240000); setExt(j); setEdit(null); setRes(null);
      const c={}; Object.keys(LEAD_VAZIO).forEach(k=>c[k]=(j.campos||{})[k]||""); setF(c);
    }catch(e){ setExtErro("Não consegui extrair de "+file.name+": "+e.message); } setExtBusy(false); };
  const salvar=async()=>{ if(busy) return; setErro(null);
    if(!edit&&!f.cliente_nome.trim()){ setErro("Informe o nome do contato."); return; }
    setBusy(true);
    try{
      if(edit){
        const body={reavaliar:reav}; Object.keys(LEAD_VAZIO).forEach(k=>{ if((f[k]??"")!==(edit.lead[k]??"")) body[k]=f[k]; });
        const r=await jpost("/api/cadastro/"+edit.lead.lead_id,body,"PUT");
        setRes({editado:true,lead_id:edit.lead.lead_id,...r,...(r.ia||{})}); acompanhar(edit.lead.lead_id); abrir(edit.lead.lead_id);
      } else {
        const r=await jpost("/api/cadastro",{...f,anexo_tmp:ext?ext.anexo_tmp:null});
        setRes(r); setF(LEAD_VAZIO); setExt(null); setRk(x=>x+1); acompanhar(r.lead_id);
      }
    }catch(e){ setErro(e.message); }
    setBusy(false); };
  const abrir=async(id)=>{ setErro(null); setExt(null);
    try{ const d=await api("/api/cadastro/"+id); setEdit(d); setReav(false);
      const c={}; Object.keys(LEAD_VAZIO).forEach(k=>c[k]=d.lead[k]??""); setF(c); esqRef.current&&esqRef.current.scrollTo({top:0,behavior:"smooth"});
    }catch(e){ setErro(e.message);} };
  const cancelar=()=>{ setEdit(null); setF(LEAD_VAZIO); setExt(null); };
  const remover=async(id)=>{ if(!confirm(`Remover ${id} do Lakebase? O CDC propaga a exclusão para o Unity Catalog e os anexos são apagados.`)) return;
    try{ await api("/api/cadastro/"+id,{method:"DELETE"}); if(edit&&edit.lead.lead_id===id) cancelar(); setRk(x=>x+1);}catch(e){ setErro(e.message);} };
  const mudaStatus=async(id,status)=>{ try{ await jpost("/api/cadastro/"+id,{status},"PATCH"); setRk(x=>x+1); acompanhar(id);}catch(e){ setErro(e.message);} };
  const anexar=async(file)=>{ if(!edit) return; const fd=new FormData(); fd.append("file",file);
    try{ await apiForm("/api/cadastro/"+edit.lead.lead_id+"/anexos",fd); abrir(edit.lead.lead_id); setRk(x=>x+1);}catch(e){ setErro(e.message);} };
  const tirarAnexo=async(aid)=>{ if(!confirm("Remover este anexo?")) return; await api("/api/cadastro/anexos/"+aid,{method:"DELETE"}); abrir(edit.lead.lead_id); setRk(x=>x+1); };
  const piiBloq=!!edit&&!edit.pii_liberado;
  const inp=(k,ph,extra)=>{ const pii=["cliente_nome","email","telefone","documento"].includes(k)&&piiBloq;
    return html`<input class="inp" placeholder=${ph} value=${f[k]} onInput=${set(k)} disabled=${pii} title=${pii?"Dado pessoal mascarado — libere o acesso a PII para editar":""} style=${pii?{opacity:.6}:{}} ...${extra||{}}/>`; };
  const sel=(k,ph,opts)=>html`<select class="inp" value=${f[k]} onChange=${set(k)}><option value="">${ph}</option>${(opts||[]).map(o=>html`<option key=${o} value=${o}>${o}</option>`)}</select>`;
  const cls=(c)=>c==="Quente"?"b-hot":c==="Morno"?"b-warm":"b-cold";
  return html`<div class="view">
    <style>${`.inp{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:10px;border:1px solid var(--card-b);background:var(--surface-2);color:var(--text-primary);font-size:13.5px;margin-bottom:8px;font-family:inherit}
      .fg2{display:grid;grid-template-columns:1fr 1fr;gap:0 8px}.btnp{width:100%;padding:11px;border-radius:11px;border:0;background:var(--grad);color:#fff;font-weight:800;font-size:14.5px;cursor:pointer}`}</style>
    <${CdcStatus} rk=${rk}/>
    <div class="g g-12 fill">
    <div class="stack vscroll" ref=${esqRef}>
      ${!edit?html`<div class="card">
        <div style=${{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"8px",marginBottom:"8px"}}>
          <h3 style=${{margin:0}}>Cadastrar a partir de PDF</h3>
          <${Btn} onClick=${()=>setVerPrompt(!verPrompt)}>${verPrompt?"Ocultar prompt":"⚙️ Editar prompt / modelo"}</${Btn}></div>
        <${DropZone} id="cadPdf" accept=".pdf,.png,.jpg,.jpeg" busy=${extBusy} onFile=${(fl)=>extrair(fl)} label=${extBusy?"Extraindo os dados de "+((ultimoPdf.current&&ultimoPdf.current.name)||"documento")+"…":"Arraste a ficha cadastral, RFQ ou e-mail (PDF) — ou clique"} sub="Os campos abaixo são preenchidos para você revisar · o PDF vira anexo do lead" erro=${extErro}/>
        ${ext?html`<div style=${{marginTop:"10px",padding:"9px 12px",borderRadius:"10px",background:"var(--surface-2)",fontSize:"12.5px"}}>
          ✅ <b>${ext.arquivo}</b> · ${ext.modo==="direto"?"PDF direto no modelo":"ai_parse_document → modelo"} · <code>${ext.modelo.replace("system.ai.","")}</code> · prompt ${ext.versao_prompt!=null?"v"+(ext.versao_prompt||"padrão"):"de teste (não salvo)"} · ${(ext.ms/1000).toFixed(1)}s
          ${ext.texto_extraido?html`<details style=${{marginTop:"6px"}}><summary class="cap" style=${{cursor:"pointer"}}>Texto extraído pelo ai_parse_document</summary><pre style=${{whiteSpace:"pre-wrap",fontSize:"11.5px",maxHeight:"180px",overflow:"auto"}}>${ext.texto_extraido}</pre></details>`:null}
        </div>`:null}
      </div>`:null}
      ${verPrompt&&!edit?html`<${PromptEditor} podeTestar=${!!ultimoPdf.current} onTestar=${(cfg)=>extrair(ultimoPdf.current,cfg)}/>`:null}
      <div class="card">
        <div style=${{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"8px"}}>
          <h3 style=${{margin:0}}>${edit?"Editar "+edit.lead.lead_id:ext?"Revise e confirme o cadastro":"Novo lead"}</h3>
          ${edit?html`<span style=${{display:"flex",gap:"6px"}}><${Btn} onClick=${cancelar}>Cancelar edição</${Btn}><${Btn} kind="del" onClick=${()=>remover(edit.lead.lead_id)}>Remover lead</${Btn}></span>`:null}</div>
        <p class="cap" style=${{margin:"4px 0 10px"}}>${edit?(piiBloq?"🔒 Dados pessoais mascarados para você: os campos de PII ficam bloqueados (libere o acesso a PII para editá-los).":"Alterações gravadas no Lakebase; o CDC propaga para o Unity Catalog.")
          :"Grava no Lakebase (Postgres). A IA (Opus 4.8) qualifica o lead e o CDC replica para o Unity Catalog. Use apenas dados fictícios."}</p>
        ${inp("cliente_nome","Nome do contato *")}
        <div class="fg2">${inp("email","E-mail",{type:"email"})}${inp("telefone","Telefone",{type:"tel"})}</div>
        <div class="fg2">${inp("documento","CPF/CNPJ (fictício)")}${inp("empresa","Empresa")}</div>
        <div class="fg2">${sel("segmento","Segmento",op&&op.segmentos)}${sel("canal","Canal",op&&op.canais)}</div>
        ${sel("produto_nome","Produto de interesse",op&&op.produtos)}
        <div class="fg2">${inp("cidade","Cidade")}${sel("uf","UF",op&&op.ufs)}</div>
        <textarea class="inp" rows="2" placeholder="Mensagem / necessidade do cliente" value=${f.mensagem} onInput=${set("mensagem")}></textarea>
        ${edit?html`<label class="cap" style=${{display:"flex",gap:"6px",alignItems:"center",marginBottom:"8px",cursor:"pointer"}}><input type="checkbox" checked=${reav} onChange=${(e)=>setReav(e.target.checked)}/> Reavaliar score e próxima ação com IA após salvar</label>`:null}
        ${ext&&!edit?html`<p class="cap" style=${{marginBottom:"8px"}}>📎 ${ext.arquivo} será anexado ao lead.</p>`:null}
        ${erro?html`<p class="cap" style=${{color:"var(--critical)"}}>${erro}</p>`:null}
        <button class="btnp" disabled=${busy} onClick=${salvar}>${busy?html`<span class="spin"></span> Gravando no Lakebase…`:edit?"Salvar alterações":"Cadastrar no Lakebase"}</button>
        ${!edit&&ext?html`<div style=${{marginTop:"6px"}}><${Btn} onClick=${cancelar}>Descartar extração</${Btn}></div>`:null}
      </div>
      ${edit?html`<div class="card"><h3>📎 Anexos de ${edit.lead.lead_id}</h3>
        <p class="cap" style=${{marginBottom:"8px"}}>Ficam no Volume <code>fundalis_ia.anexos</code> (não entram no RAG por conter PII). Download só para quem tem acesso a PII.</p>
        ${(edit.anexos||[]).map(a=>html`<div key=${a.anexo_id} style=${{display:"flex",gap:"8px",alignItems:"center",padding:"6px 0",borderBottom:"1px solid var(--grid)",fontSize:"13px"}}>
          <span style=${{flex:1}}>📄 <b>${a.arquivo}</b> <span class="cap">· ${kb(a.tamanho)} · ${a.origem} · ${dt(a.criado_em)}</span></span>
          ${edit.pii_liberado?html`<a href=${"/api/cadastro/anexos/"+a.anexo_id+"/arquivo"} target="_blank" rel="noopener"><${Btn}>Baixar</${Btn}></a>`:html`<span class="cap" title="libere o acesso a PII">🔒</span>`}
          <${Btn} kind="del" onClick=${()=>tirarAnexo(a.anexo_id)}>Remover</${Btn}></div>`)}
        ${!(edit.anexos||[]).length?html`<p class="cap">Sem anexos.</p>`:null}
        <div style=${{marginTop:"10px"}}><${DropZone} id="anexoNovo" accept=".pdf,.png,.jpg,.jpeg,.docx" onFile=${anexar} label="Anexar arquivo a este lead"/></div>
      </div>`:null}
      ${res?html`<div class="card">
        <div style=${{display:"flex",justifyContent:"space-between",alignItems:"center",gap:"8px"}}><b>✅ ${res.lead_id} ${res.editado?"atualizado":"gravado"} no Lakebase</b>${res.classificacao_ia?html`<span class=${"badge "+cls(res.classificacao_ia)}>${res.classificacao_ia} · ${res.score_ia}</span>`:null}</div>
        ${res.ignorados_pii&&res.ignorados_pii.length?html`<p class="cap" style=${{color:"var(--warning)"}}>Campos de PII não alterados (sem permissão): ${res.ignorados_pii.join(", ")}</p>`:null}
        ${res.resumo_ia?html`<div class="rz" style=${{marginTop:"6px",fontSize:"13px"}}>${res.resumo_ia}</div>`:null}
        ${res.proxima_acao_ia?html`<div class="ac" style=${{fontSize:"13px"}}><b>Próxima ação:</b> ${res.proxima_acao_ia}</div>`:null}
        <div style=${{marginTop:"10px",padding:"10px 12px",borderRadius:"12px",background:"var(--surface-2)",fontSize:"12.5px"}}>
          ${!sync||!sync.sincronizado?html`<span><span class="spin"></span> Aguardando o CDC replicar para o Unity Catalog…</span>`
            :html`<div><b>🔄 Replicado no Lakehouse (visto pelo app em ~${sync.lag_s}s).</b> Como o Unity Catalog mostra para você:</div>
              <div style=${{marginTop:"5px",fontFamily:"monospace",fontSize:"12px"}}>${sync.lakehouse.cliente_nome} · ${sync.lakehouse.email||"—"} · ${sync.lakehouse.telefone||"—"} · ${sync.lakehouse.documento||"—"} · ${sync.lakehouse.status}</div>`}
        </div>
      </div>`:null}
    </div>
    <div class="card pane">
      <div class="pane-h"><h3>Leads cadastrados ${lista?html`<span class="cnt">${lista.length}</span>`:null}</h3>
        <span style=${{display:"flex",gap:"10px",alignItems:"center"}}><span class="cap">lidos do Unity Catalog (mascarado) · <button class="lnk" style=${{color:"var(--brand)",fontWeight:600,background:"none",border:0,cursor:"pointer",font:"inherit"}} onClick=${()=>setRk(x=>x+1)}>atualizar</button></span>
          <${PiiToggle} mini=${true} onChange=${()=>{ setRk(x=>x+1); if(edit) abrir(edit.lead.lead_id); if(res) acompanhar(res.lead_id); }}/></span></div>
      <input class="inp" style=${{flex:"none"}} placeholder="Buscar por código, empresa ou produto…" value=${busca} onInput=${(e)=>setBusca(e.target.value)}/>
      <div class="body">
      ${lista==null?html`<span class="spin"></span>`:lista.map((l,i)=>html`<div class="lead" key=${l.lead_id} style=${{outline:edit&&edit.lead.lead_id===l.lead_id?"2px solid var(--brand)":""}}>
        <div style=${{flex:1,minWidth:0}}>
          <div style=${{display:"flex",justifyContent:"space-between",gap:"8px",alignItems:"center"}}>
            <span class="nm">${l.cliente_nome||"(aguardando CDC…)"}</span>
            <span style=${{display:"flex",gap:"6px",alignItems:"center"}}>
              ${l.n_anexos?html`<span class="badge b-warm" title="anexos">📎 ${l.n_anexos}</span>`:null}
              ${l.sincronizado?html`<span class="badge b-cold" title="já replicado no Lakehouse">UC ✓</span>`:html`<span class="badge b-warm" title="gravado no Lakebase, replicação em andamento">CDC…</span>`}</span></div>
          <div class="mt">${l.lead_id} · ${l.empresa||""} · ${l.produto_nome||""} ${l.uf?"· "+l.uf:""}</div>
          ${l.email||l.telefone?html`<div class="mt" style=${{fontFamily:"monospace"}}>${l.email||""} ${l.telefone?"· "+l.telefone:""} ${l.documento?"· "+l.documento:""}</div>`:null}
          ${l.resumo_ia?html`<div class="rz">${l.resumo_ia}</div>`:null}
          <div style=${{marginTop:"7px",display:"flex",gap:"6px",alignItems:"center",flexWrap:"wrap"}}>
            ${l.classificacao_ia?html`<span class=${"badge "+cls(l.classificacao_ia)}>${l.classificacao_ia} ${l.score_ia||""}</span>`:null}
            ${l.status?html`<select class="inp" style=${{width:"auto",margin:0,padding:"4px 8px",fontSize:"12px"}} value=${l.status} onChange=${(e)=>mudaStatus(l.lead_id,e.target.value)}>
              ${((op&&op.status)||[l.status]).map(s=>html`<option key=${s} value=${s}>${s}</option>`)}</select>`:null}
            <span style=${{marginLeft:"auto",display:"flex",gap:"5px"}}>
              <${Btn} onClick=${()=>abrir(l.lead_id)}>Editar</${Btn}>
              <${Btn} kind="del" onClick=${()=>remover(l.lead_id)}>Remover</${Btn}></span>
          </div>
        </div></div>`)}
      ${lista&&!lista.length?html`<p class="cap">Nenhum lead encontrado.</p>`:null}
      </div>
    </div></div>
  </div>`;
}

/* ============ painel: toggle PII (Unity Catalog Column Mask) ============ */
function PiiToggle({ onChange, mini }){
  const [lib,setLib]=useState(null); const [busy,setBusy]=useState(false);
  useEffect(()=>{ api("/api/pii/status").then(r=>setLib(!!r.liberado)).catch(()=>setLib(false)); },[]);
  const toggle=async()=>{ if(busy)return; setBusy(true);
    try{ const r=await api("/api/pii/toggle",{method:"POST"}); setLib(!!r.liberado); onChange&&onChange(); }
    catch(e){} setBusy(false); };
  if(lib==null) return null;
  if(mini) return html`<button class=${"btnpii"+(lib?" on":"")} style=${{minWidth:0,padding:"5px 12px",fontSize:"12px"}} disabled=${busy} onClick=${toggle}
      title=${lib?"Nomes dos clientes visíveis — clique para revogar":"Nomes mascarados pela política do UC (LGPD) — clique para liberar"}>
    ${busy?html`<span class="spin"></span>`:(lib?"🔓 PII liberada":"🔒 PII mascarada")}</button>`;
  return html`<div class="card" style=${{display:"flex",alignItems:"center",gap:"12px",marginBottom:"14px"}}>
    <span style=${{fontSize:"22px",flex:"none"}}>${lib?"🔓":"🔒"}</span>
    <div style=${{flex:1,minWidth:0}}>
      <div style=${{fontWeight:700,fontSize:"14px"}}>Acesso a dados pessoais <span class="cap" style=${{fontWeight:500}}>· Unity Catalog</span></div>
      <div class="cap">${lib?"Liberado — nomes dos clientes visíveis." :"Restrito — nomes mascarados pela política do UC (LGPD)."}</div>
    </div>
    <button class=${"btnpii"+(lib?" on":"")} disabled=${busy} onClick=${toggle}>
      ${busy?html`<span class="spin"></span>`:(lib?"Revogar":"Liberar")}</button>
  </div>`;
}

/* ============ painel: leads B2B priorizados ============ */
function LeadsCard({ rk, onPii }){
  const [rows,setRows]=useState(null); const [f,setF]=useState("Todos");
  useEffect(()=>{ setRows(null);
    const q=f==="Todos"?"":"&classe="+encodeURIComponent(f);
    api("/api/leads?limit=60"+q).then(setRows).catch(()=>setRows([]));
  },[rk,f]);
  const vis=rows||[];
  const cls=(c)=>c==="Quente"?"b-hot":c==="Morno"?"b-warm":"b-cold";
  const ringc=(c)=>c==="Quente"?cssv("--hot"):c==="Morno"?cssv("--warm"):cssv("--cold");
  return html`<div class="card pane">
    <div class="pane-h"><h3 title="ordenados pelo score de IA">Leads priorizados</h3><${PiiToggle} mini=${true} onChange=${onPii}/></div>
    <div class="chips sm" style=${{marginBottom:"8px",flex:"none"}}>
      ${["Todos","Quente","Morno","Frio"].map(t=>html`<span key=${t} class=${"chip"+(f===t?" on":"")} onClick=${()=>setF(t)}>${t}</span>`)}
      ${rows?html`<span class="cnt" style=${{alignSelf:"center"}}>${rows.length}</span>`:null}</div>
    ${rows==null?html`<span class="spin"></span>`:html`<div class="body">${vis.map((l,i)=>html`<div class="lead" key=${i}>
      <div class="ring" style=${{"--p":l.score_ia||0,"--c":ringc(l.classificacao_ia)}}><i>${l.score_ia??"—"}</i></div>
      <div style=${{flex:1,minWidth:0}}>
        <div style=${{display:"flex",justifyContent:"space-between",gap:"8px",alignItems:"center"}}>
          <span class="nm">${l.cliente_nome}</span><span class=${"badge "+cls(l.classificacao_ia)}>${l.classificacao_ia||"—"}</span></div>
        <div class="mt">${l.produto_nome} · ${l.empresa||""} ${l.uf?"· "+l.uf:""} · ${l.segmento||l.canal} · ${l.status}</div>
        ${l.resumo_ia?html`<div class="rz">${l.resumo_ia}</div>`:null}
        ${l.proxima_acao_ia?html`<div class="ac"><b>Próxima ação:</b> ${l.proxima_acao_ia}</div>`:null}
      </div></div>`)}</div>`}
  </div>`;
}

/* ============ painel: rede de unidades industriais & recebimento ============ */
function RedeCard(){
  const [d,setD]=useState(null);
  useEffect(()=>{ api("/api/rede").then(r=>setD(r.rede||[])).catch(()=>setD([])); },[]);
  if(d==null) return html`<div class="card pane"><span class="spin"></span></div>`;
  return html`<div class="card pane">
    <div class="pane-h"><h3>Rede Fundalis <span class="cap" style=${{fontWeight:500}}>· plantas</span></h3><span class="cnt">${d.length}</span></div>
    <div class="body"><table>
      <thead><tr><th>Unidade</th><th>Tipo</th><th>Receita(mi)</th><th>Vendas</th></tr></thead>
      <tbody>${d.map((u,i)=>html`<tr key=${i}>
        <td><b>${u.nome}</b><div class="cap" style=${{fontSize:"10.5px"}}>${u.cidade}/${u.uf}</div></td>
        <td><span class=${"badge "+(u.tipo==="Fundição"?"b-hot":u.tipo==="Matriz"?"b-cold":"b-warm")}>${u.tipo}</span></td>
        <td>${fmt1(u.receita_mi)}</td><td>${fmt(u.vendas)}</td>
      </tr>`)}</tbody></table></div>
  </div>`;
}

/* ============ ABA — Painel ============ */
function Painel(){
  const [k,setK]=useState(null); const [dist,setDist]=useState(null); const [ufs,setUfs]=useState(null);
  const [rk,setRk]=useState(0); const [carregando,setCarregando]=useState(false);
  const carregar=()=>{ setCarregando(true);
    Promise.allSettled([
      api("/api/kpis").then(setK), api("/api/distribuicoes").then(setDist),
      api("/api/mapa").then(r=>setUfs(r.ufs||[]))
    ]).finally(()=>{ setRk(x=>x+1); setCarregando(false); });
  };
  useEffect(()=>{ carregar(); },[]);
  return html`<div class="view">
    <div class="painel-top">
      <span class="cap" style=${{fontWeight:700}}>Visão geral · dados fictícios</span>
      <button class="refresh" disabled=${carregando} onClick=${carregar} title="Atualizar">
        ${carregando?html`<span class="spin"></span>`:html`<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>`} Atualizar</button>
    </div>
    <div class="g g-kpi stretch" style=${{marginBottom:0}}>
      <div class="hero">
        <div class="lbl">Receita comercial</div>
        <div class="big">${k?brl(k.receita_total):"…"}</div>
        <div class="sub">${k?`${fmt(k.produtos)} produtos · ${fmt(k.unidades)} unidades · líder: ${k.categoria_lider}`:""}</div>
      </div>
      <div class="kpi"><div class="lbl">Itens vendidos</div><div class="val accent">${k?un(k.itens_vendidos):"…"}</div><div class="sub">${k?fmt(k.vendas_mes)+" vendas no mês":""}</div></div>
      <div class="kpi"><div class="lbl">Ticket médio</div><div class="val">${k?brl(k.ticket_medio):"…"}</div><div class="sub">por venda</div></div>
      <div class="kpi"><div class="lbl">Exportação</div><div class="val warm">${k?fmt1(k.ecommerce_pct)+"%":"…"}</div><div class="sub">da receita</div></div>
      <div class="kpi"><div class="lbl">Leads ativos</div><div class="val">${k?fmt(k.leads_ativos):"…"}</div><div class="sub">${k?fmt1(k.conversao)+"% conversão":""}</div></div>
    </div>
    <div class="g g-painel fill">
      <div class="card pane span2"><div class="pane-h"><h3>Mapa de vendas</h3></div>
        <div class="body"><p class="cap" style=${{margin:"0 0 10px"}}>Receita por estado — clique para explorar por produto.</p>
        ${ufs==null?html`<span class="spin"></span>`:html`<div style=${{maxWidth:"500px",margin:"0 auto"}}><${MapaBR} ufs=${ufs}/></div>`}</div></div>
      <div class="card pane"><div class="pane-h"><h3>Receita por categoria (R$ mi)</h3></div>
        <div class="body">${dist?html`<${Donut} items=${dist.familias}/>`:html`<span class="spin"></span>`}</div></div>
      <div class="card pane"><div class="pane-h"><h3>Receita por produto (R$ mi)</h3></div>
        <div class="body">${dist?html`<${Bars} items=${dist.produtos} colorVar="--brand"/>`:html`<span class="spin"></span>`}</div></div>
      <${LeadsCard} rk=${rk} onPii=${()=>setRk(x=>x+1)}/>
      <div class="card pane"><div class="pane-h"><h3>Funil de leads</h3></div>
        <div class="body">${dist?html`<${Bars} items=${dist.funil} colorVar="--s3"/>`:html`<span class="spin"></span>`}</div></div>
      <div class="card pane"><div class="pane-h"><h3>Receita por canal (R$ mi)</h3></div>
        <div class="body">${dist?html`<${Bars} items=${dist.canais} colorVar="--s2"/>`:html`<span class="spin"></span>`}</div></div>
      <${RedeCard}/>
    </div>
  </div>`;
}

/* ============ ABA — Produtos (catálogo) ============ */
const famBadge=(f)=> f==="Blocos de Motor"?"b-hot":f==="Cabeçotes"?"b-warm":f==="Componentes Estruturais"?"b-cold":f==="Peças Usinadas"?"b-hot":"b-cold";
/* ícone (SVG inline) por família — evita depender de fonte de emoji e serve de "imagem" do produto */
function ProdIcon({ fam }){
  const A={viewBox:"0 0 24 24",width:"26",height:"26",fill:"none",stroke:"currentColor","stroke-width":"1.7","stroke-linecap":"round","stroke-linejoin":"round"};
  if(fam==="Blocos de Motor") return html`<svg ...${A}><rect x="3" y="9" width="18" height="11" rx="1.5"/><circle cx="8" cy="6" r="2.1"/><circle cx="14" cy="6" r="2.1"/><line x1="7" y1="13" x2="7" y2="16.5"/><line x1="12" y1="13" x2="12" y2="16.5"/><line x1="17" y1="13" x2="17" y2="16.5"/></svg>`;
  if(fam==="Cabeçotes") return html`<svg ...${A}><rect x="3" y="6" width="18" height="6.5" rx="1.5"/><line x1="3.5" y1="15.5" x2="20.5" y2="15.5"/><circle cx="8" cy="9.2" r="1.5"/><circle cx="14" cy="9.2" r="1.5"/><line x1="6" y1="15.5" x2="6" y2="18.5"/><line x1="18" y1="15.5" x2="18" y2="18.5"/></svg>`;
  if(fam==="Componentes Estruturais") return html`<svg ...${A}><path d="M4 4v10a4 4 0 0 0 4 4h10"/><circle cx="4" cy="4" r="1.6"/><circle cx="18" cy="18" r="1.6"/><path d="M4 9h4"/></svg>`;
  if(fam==="Cubos & Carcaças") return html`<svg ...${A}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.4"/><circle cx="12" cy="6.6" r="0.9"/><circle cx="17.4" cy="12" r="0.9"/><circle cx="12" cy="17.4" r="0.9"/><circle cx="6.6" cy="12" r="0.9"/></svg>`;
  if(fam==="Coletores & Múltiplos") return html`<svg ...${A}><path d="M4 5v3a3 3 0 0 0 3 3h10a3 3 0 0 1 3 3v3"/><path d="M9 5v3"/><path d="M14 5v3"/></svg>`;
  if(fam==="Peças Usinadas") return html`<svg ...${A}><circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8"/></svg>`;
  return html`<svg ...${A}><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5"/><line x1="12" y1="22" x2="12" y2="12"/></svg>`;
}
const prodTile={flex:"none",width:"46px",height:"46px",borderRadius:"12px",background:"var(--brand-soft)",color:"var(--brand)",display:"grid",placeItems:"center"};
function ProdutoCard({ p }){
  const [open,setOpen]=useState(false); const [det,setDet]=useState(null);
  const abrir=()=>{ const nx=!open; setOpen(nx);
    if(nx&&det==null) api("/api/produtos/lojas?produto="+encodeURIComponent(p.nome)).then(setDet).catch(()=>setDet({lojas:[],canais:[]})); };
  return html`<div class="card" style=${{padding:"14px",cursor:"pointer"}} onClick=${abrir}>
    <div style=${{display:"flex",gap:"12px",alignItems:"center"}}>
      <span style=${prodTile}><${ProdIcon} fam=${p.familia}/></span>
      <div style=${{flex:1,minWidth:0}}>
        <div style=${{display:"flex",justifyContent:"space-between",gap:"8px",alignItems:"center"}}>
          <span style=${{fontWeight:700,fontSize:"14.5px"}}>${p.nome}</span>
          <span class=${"badge "+famBadge(p.familia)}>${p.marca||p.familia}</span></div>
        <div class="cap" style=${{marginTop:"2px"}}>${brl((p.receita_mi||0)*1e6)} · ${un(p.volume)}${p.ecommerce_pct?" · "+fmt(p.ecommerce_pct)+"% export.":""}</div>
      </div>
      <span class="cap" style=${{flex:"none"}}>${open?"▲":"▼"}</span>
    </div>
    ${open?html`<div style=${{marginTop:"10px",borderTop:"1px solid var(--grid)",paddingTop:"10px"}}>
      ${p.descricao?html`<p class="cap" style=${{marginBottom:"8px"}}>${p.descricao}</p>`:null}
      <div class="cap">Preço de referência: <b>${brl(p.preco)}</b> · ${p.familia}</div>
      ${det==null?html`<span class="spin"></span>`:html`<div style=${{marginTop:"9px"}}>
        <div class="cap" style=${{fontWeight:700,marginBottom:"6px"}}>Unidades que mais vendem</div>
        ${(det.lojas||[]).length?html`<div class="tscroll"><table><thead><tr><th>Unidade</th><th>Receita(mi)</th><th>Qtd</th></tr></thead>
          <tbody>${det.lojas.map((u,i)=>html`<tr key=${i}><td>${u.nome}</td><td>${fmt1(u.receita_mi)}</td><td>${fmt(u.volume)}</td></tr>`)}</tbody></table></div>`
          :html`<p class="muted">Sem vendas registradas.</p>`}
      </div>`}
    </div>`:null}
  </div>`;
}
function Produtos(){
  const [ps,setPs]=useState(null); const [fam,setFam]=useState("Todos");
  useEffect(()=>{ api("/api/produtos").then(r=>setPs(r.produtos||[])).catch(()=>setPs([])); },[]);
  const fams=["Todos","Blocos de Motor","Cabeçotes","Componentes Estruturais","Cubos & Carcaças","Coletores & Múltiplos","Peças Usinadas"];
  const vis=(ps||[]).filter(p=>fam==="Todos"||p.familia===fam);
  return html`<div class="view">
    <div class="chips" style=${{marginBottom:"12px"}}>
      ${fams.map(t=>html`<span key=${t} class=${"chip"+(fam===t?" on":"")} onClick=${()=>setFam(t)}>${t}</span>`)}</div>
    ${ps==null?html`<span class="spin"></span>`:vis.length?vis.map((p,i)=>html`<${ProdutoCard} key=${i} p=${p}/>`):html`<p class="muted">Sem produtos.</p>`}
  </div>`;
}

/* ============ ABA — Diagnóstico (foto da peça + catálogo de culturas) ============ */
function Diagnosticar(){
  const [prev,setPrev]=useState(null); const [file,setFile]=useState(null);
  const [busy,setBusy]=useState(false); const [res,setRes]=useState(null); const [err,setErr]=useState("");
  const [imgErro,setImgErro]=useState(false);
  const escolher=(e)=>{ const f=e.target.files&&e.target.files[0]; try{e.target.value="";}catch(_){}; if(!f) return;
    setFile(f); setRes(null); setErr(""); setImgErro(false); setPrev(URL.createObjectURL(f)); };
  const analisar=async()=>{ if(!file||busy) return; setBusy(true); setErr(""); setRes(null);
    try{ const fd=new FormData(); fd.append("file",file);
      setRes(await apiForm("/api/cultura/identificar",fd));
    }catch(e){ setErr(e.message||"Falha na análise."); } setBusy(false); };
  const VH={position:"absolute",width:"1px",height:"1px",opacity:0,overflow:"hidden"};
  return html`<div class="g g2 fill">
    <div class="stack vscroll"><div class="card">
      <input id="equipFile" type="file" accept="image/*" style=${VH} onChange=${escolher}/>
      ${prev?html`<div style=${{position:"relative",width:"100%",height:"380px",borderRadius:"14px",overflow:"hidden",marginBottom:"10px",background:"var(--surface-2)",border:"1px solid var(--card-b)"}}>
          ${imgErro
            ? html`<div style=${{position:"absolute",inset:0,display:"flex",flexDirection:"column",gap:"6px",alignItems:"center",justifyContent:"center",textAlign:"center",padding:"16px"}}>
                <div style=${{fontSize:"38px"}}>⚙️</div>
                <div style=${{fontWeight:700,color:"var(--brand-dark)"}}>Foto anexada</div>
                <div class="cap">A prévia deste formato não pôde ser exibida, mas a foto será analisada normalmente.</div></div>`
            : html`<img src=${prev} onError=${()=>setImgErro(true)} style=${{width:"100%",height:"100%",objectFit:"cover",display:"block"}}/>`}
        </div>`
        :html`<label htmlFor="equipFile" style=${{display:"block",border:"2px dashed var(--brand)",borderRadius:"16px",padding:"70px 16px",textAlign:"center",cursor:"pointer",background:"var(--brand-soft)"}}>
          <div style=${{fontSize:"40px"}}>⚙️</div>
          <div style=${{fontWeight:700,marginTop:"6px",color:"var(--brand-dark)"}}>Clique para escolher uma foto da peça</div>
          <div class="cap">Bloco, cabeçote, carcaça, componente ou região do defeito</div>
        </label>`}
      ${prev?html`<div style=${{display:"flex",gap:"8px"}}>
        <label htmlFor="equipFile" class="refresh" style=${{flex:1,justifyContent:"center",cursor:"pointer"}}>Trocar foto</label>
        <button class="btnpii on" style=${{flex:1}} disabled=${busy} onClick=${analisar}>${busy?html`<span class="spin"></span>`:"Diagnosticar"}</button>
      </div>`:null}
      ${err?html`<p style=${{color:"var(--critical)",marginTop:"10px",fontSize:"13px"}}>${err}</p>`:null}
    </div></div>
    <div class="stack vscroll">
      ${busy?html`<div class="card"><span class="spin"></span> Analisando a foto com a visão do Opus 4.8…</div>`
        :res?html`<${EquipResultado} r=${res}/>`
        :html`<div class="card"><h3>Resultado da inspeção</h3><p class="cap">Escolha uma foto da peça e clique em <b>Diagnosticar</b>: a IA identifica o tipo de peça, o defeito provável e a ação recomendada.</p></div>`}
    </div>
  </div>`;
}
function Diagnostico(){ return html`<div class="view"><${Diagnosticar}/></div>`; }

/* ============ ABA — Rechupe (texto livre -> features via IA -> modelo de ML servido) ============ */
const RECHUPE_ORDER=["tipo_ferro","temp_vazamento_c","modulo_geometrico_cm","espessura_parede_mm","teor_carbono_pct","teor_silicio_pct","inoculacao_kg_t","tempo_solidificacao_s","taxa_resfriamento_cs","usa_massalote"];
const RECHUPE_LBL={tipo_ferro:"Tipo de ferro",temp_vazamento_c:"Temp. vazamento (°C)",modulo_geometrico_cm:"Módulo geométrico (cm)",espessura_parede_mm:"Espessura de parede (mm)",teor_carbono_pct:"Carbono (%C)",teor_silicio_pct:"Silício (%Si)",inoculacao_kg_t:"Inoculação (kg/t)",tempo_solidificacao_s:"Tempo solidificação (s)",taxa_resfriamento_cs:"Resfriamento (°C/s)",usa_massalote:"Massalote/alimentador"};
function ShapBars({ itens }){
  const max=Math.max(0.01,...itens.map(x=>Math.abs(x.shap)));
  return html`<div>${itens.map((x,i)=>{ const w=Math.max(2,Math.abs(x.shap)/max*50), pos=x.shap>0;
    return html`<div key=${i} style=${{display:"grid",gridTemplateColumns:"minmax(0,1.1fr) minmax(0,1.6fr) 62px",gap:"10px",alignItems:"center",fontSize:"12.5px",padding:"4px 0"}}>
      <span style=${{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}} title=${x.label}>${x.label} <b>= ${x.valor}</b></span>
      <span style=${{position:"relative",height:"14px",background:"var(--surface-2)",borderRadius:"4px"}}>
        <span style=${{position:"absolute",left:"50%",top:"-2px",bottom:"-2px",width:"1px",background:"var(--muted)"}}></span>
        <span style=${{position:"absolute",top:"2px",height:"10px",borderRadius:"3px",width:w+"%",left:pos?"50%":(50-w)+"%",background:pos?cssv("--hot"):cssv("--cold")}}></span></span>
      <b style=${{textAlign:"right",color:pos?cssv("--hot"):cssv("--cold")}}>${x.shap>0?"+":""}${x.shap.toFixed(2).replace(".",",")}</b></div>`; })}</div>`;
}
const RECHUPE_STEP={temp_vazamento_c:5,modulo_geometrico_cm:0.05,espessura_parede_mm:1,teor_carbono_pct:0.05,teor_silicio_pct:0.05,inoculacao_kg_t:0.05,tempo_solidificacao_s:10,taxa_resfriamento_cs:0.1};
function Rechupe(){
  const [txt,setTxt]=useState("Bloco de motor diesel em ferro nodular (GGG-50) para cliente de veículos pesados. A peça tem parede principal de 45 mm e módulo geométrico de 3,8 cm na região dos mancais. O metal é vazado a 1465 °C, com 3,6% de carbono e 2,4% de silício, e recebe inoculação baixa de 0,1 kg/t no jato. O molde não usa massalote nem alimentador. A simulação indica tempo de solidificação de cerca de 900 s nas seções mais espessas e taxa de resfriamento de 1,2 °C/s.");
  const [busy,setBusy]=useState(false);
  const [res,setRes]=useState(null); const [err,setErr]=useState("");
  const [par,setPar]=useState(null);            // parâmetros editáveis (começam com o que a IA extraiu)
  const [assum,setAssum]=useState([]); const [obs,setObs]=useState(""); const [editados,setEditados]=useState([]);
  const chama=(body)=>api("/api/rechupe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const prever=async(t)=>{ const q=(t??txt).trim(); if(!q||busy)return; if(t!=null)setTxt(q); setBusy(true); setErr("");
    try{ const r=await chama({texto:q}); setRes(r); setPar({...r.features}); setAssum(r.assumidos||[]); setObs(r.observacao||""); setEditados([]); }
    catch(e){ setErr(e.message||"Falha na predição."); } setBusy(false); };
  const recalcular=async()=>{ if(!par||busy) return;  // sempre escora o modelo servido com os parâmetros da tela setBusy(true); setErr("");
    try{ setRes(await chama({features:par})); }catch(e){ setErr(e.message||"Falha na predição."); } setBusy(false); };
  const muda=(k,v)=>{ setPar(p=>({...p,[k]:v})); setEditados(e=>e.includes(k)?e:[...e,k]); setAssum(a=>a.filter(x=>x!==k)); };
  useEffect(()=>{ prever(); },[]);  // já roda com o exemplo pré-preenchido p/ mostrar os campos identificados
  const pct=res?Math.round((res.prob_rechupe||0)*100):0;
  const cor=(c)=>c==="Alto"?cssv("--hot"):c==="Médio"?cssv("--warm"):cssv("--good");
  const badge=(c)=>c==="Alto"?"b-hot":c==="Médio"?"b-warm":"b-cold";
  const igual=(a,b)=>(a===""||isNaN(Number(a))||isNaN(Number(b)))?String(a)===String(b):Number(a)===Number(b);
  const difere=res&&par&&RECHUPE_ORDER.some(k=>!igual(par[k],(res.features||{})[k]));
  const fstyle={width:"100%",boxSizing:"border-box",padding:"7px 9px",borderRadius:"9px",border:"1px solid var(--card-b)",background:"var(--surface-2)",color:"var(--text-primary)",font:"inherit",fontSize:"13px"};
  const campo=(k)=>{ const v=par[k]; const st={...fstyle,...(editados.includes(k)?{borderColor:"var(--brand)",background:"var(--brand-soft)"}:{})};
    if(k==="tipo_ferro") return html`<select style=${st} value=${v} onChange=${(e)=>muda(k,e.target.value)}>${["Cinzento","Nodular","Vermicular"].map(o=>html`<option key=${o}>${o}</option>`)}</select>`;
    if(k==="usa_massalote") return html`<select style=${st} value=${String(Number(v)?1:0)} onChange=${(e)=>muda(k,Number(e.target.value))}><option value="1">Sim</option><option value="0">Não</option></select>`;
    return html`<input type="number" step=${RECHUPE_STEP[k]||"any"} style=${st} value=${v} onInput=${(e)=>muda(k,e.target.value)} onKeyDown=${(e)=>e.key==="Enter"&&recalcular()}/>`; };
  return html`<div class="view"><div class="g g2 fill">
    <div class="card pane"><div class="body">
      <h3>Condições do processo</h3>
      <p class="cap" style=${{marginBottom:"10px"}}>Descreva em texto livre. A IA (Opus 4.8) extrai os parâmetros e um modelo de ML servido no Model Serving estima a probabilidade de rechupe.</p>
      <textarea value=${txt} onInput=${(e)=>setTxt(e.target.value)} rows="6" placeholder="Ex.: Bloco em ferro nodular, parede de 45 mm, vazamento a 1465 °C, sem massalote, inoculação baixa." style=${{width:"100%",boxSizing:"border-box",padding:"12px",borderRadius:"12px",border:"1px solid var(--card-b)",background:"var(--surface-1)",color:"var(--text-primary)",font:"inherit",fontSize:"14px",resize:"vertical"}}></textarea>
      <button class="btnpii on" style=${{width:"100%",marginTop:"10px"}} disabled=${busy} onClick=${()=>prever()}>${busy?html`<span class="spin"></span>`:"Extrair parâmetros do texto e prever"}</button>
      ${err?html`<p style=${{color:"var(--critical)",marginTop:"10px",fontSize:"13px"}}>${err}</p>`:null}
      ${par?html`<div style=${{marginTop:"16px",paddingTop:"14px",borderTop:"1px solid var(--grid)"}}>
        <div style=${{display:"flex",justifyContent:"space-between",alignItems:"baseline",gap:"8px",marginBottom:"8px"}}>
          <b style=${{fontSize:"14px"}}>Parâmetros do modelo</b>
          <span class="cap">extraídos pela IA · edite qualquer valor e clique em Prever</span></div>
        <div style=${{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"8px 12px"}}>
          ${RECHUPE_ORDER.map(k=>html`<label key=${k} style=${{display:"block"}}>
            <span class="cap" style=${{display:"block",fontSize:"11.5px",marginBottom:"3px"}}>${RECHUPE_LBL[k]}
              ${assum.includes(k)?html` <span class="badge b-warm" title="não estava no texto — valor típico assumido pela IA" style=${{fontSize:"10px",padding:"0 6px"}}>assumido</span>`:null}
              ${editados.includes(k)?html` <span class="badge b-cold" style=${{fontSize:"10px",padding:"0 6px"}}>editado</span>`:null}</span>
            ${campo(k)}</label>`)}
        </div>
        ${obs?html`<p class="cap" style=${{marginTop:"8px"}}>IA: ${obs}</p>`:null}
        <button class="btnpii on" style=${{width:"100%",marginTop:"12px"}} disabled=${busy} onClick=${recalcular}
          title="Envia estes parâmetros direto ao modelo servido (sem passar pela IA)">${busy?html`<span class="spin"></span>`:"Prever"}</button>
      </div>`:null}
    </div></div>
    <div class="stack vscroll">
    ${busy&&!res?html`<div class="card"><span class="spin"></span> Extraindo parâmetros e consultando o modelo…</div>`:null}
    ${res?html`<div class="card" style=${{opacity:busy?.6:1}}>
        <div style=${{display:"flex",gap:"14px",alignItems:"center"}}>
          <div class="ring" style=${{"--p":pct,"--c":cor(res.classe_risco),width:"64px",height:"64px",fontSize:"15px"}}><i style=${{width:"50px",height:"50px"}}>${pct}%</i></div>
          <div style=${{flex:1,minWidth:0}}>
            <div style=${{display:"flex",gap:"8px",alignItems:"center"}}><span style=${{fontWeight:800,fontSize:"16px"}}>Risco de rechupe</span><span class=${"badge "+badge(res.classe_risco)}>${res.classe_risco}</span>
              <span class="cap">${res.origem==="parametros"?"· parâmetros editados por você":"· parâmetros extraídos do texto"}</span></div>
            <div class="cap" style=${{marginTop:"2px"}}>Probabilidade prevista pelo endpoint <code>${res.modelo_ml}</code>${res.modelo_info&&res.modelo_info.modelo?html` · modelo UC <code>${res.modelo_info.modelo}</code> v${res.modelo_info.versao}`:null}.</div>
          </div>
        </div>
        ${difere?html`<p class="cap" style=${{marginTop:"8px",color:"var(--warning)"}}>Você alterou parâmetros — clique em <b>Prever</b> para atualizar o risco.</p>`:null}
      </div>
      ${res.explicacao?html`<div class="card" style=${{opacity:busy?.6:1}}>
        <h3>💬 Por que o modelo previu ${pct}%</h3>
        <p style=${{fontSize:"13.5px",lineHeight:1.55,margin:"6px 0 0"}}>${res.explicacao}</p>
        <p class="cap" style=${{marginTop:"6px",fontSize:"11.5px"}}>Texto gerado por <code>${String(res.explicacao_modelo||"").replace("system.ai.","")}</code> a partir apenas dos valores SHAP abaixo.</p>
      </div>`:null}
      <div class="card" style=${{opacity:busy?.6:1}}>
        <h3>Explicabilidade desta predição · SHAP</h3>
        <p class="cap" style=${{margin:"2px 0 10px"}}>Contribuição de cada parâmetro (log-odds), calculada pelo <b>TreeExplainer</b> dentro do modelo servido.
          <span style=${{color:cssv("--hot"),fontWeight:700}}>▶ aumenta</span> · <span style=${{color:cssv("--cold"),fontWeight:700}}>◀ reduz</span> o risco${res.shap_base!=null?html` · base do modelo: ${Math.round(100/(1+Math.exp(-res.shap_base)))}%`:null}.</p>
        ${(res.shap||[]).length?html`<${ShapBars} itens=${res.shap}/>`:html`<p class="cap">O endpoint ainda está servindo a versão sem SHAP — tente de novo em alguns minutos.</p>`}
      </div>
      ${(res.shap_global||[]).length?html`<div class="card" style=${{opacity:busy?.6:1}}>
        <h3>Importância global das features</h3>
        <p class="cap" style=${{margin:"2px 0 8px"}}>Média do |SHAP| no conjunto de teste (1.800 corridas sintéticas) — o que mais pesa no modelo em geral.</p>
        <${Bars} items=${res.shap_global.map(g=>({rotulo:g.label,valor:g.importancia}))} colorVar="--brand"/>
      </div>`:null}
      <div class="card" style=${{padding:"12px 16px"}}>
        <p class="cap" style=${{marginTop:"12px"}}>Modelo: GradientBoosting (scikit-learn) treinado com 9.000 corridas de fundição <b>sintéticas</b> (<code>${res.treino}</code>), registrado no Unity Catalog e servido no Model Serving.</p>
      </div>`:null}
    </div>
  </div></div>`;
}

/* ============ shell (6 abas) ============ */
function NavIcon({ k }){
  if(k==="chat") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7A8.4 8.4 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z"/></svg>`;
  if(k==="diagnostico") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`;
  if(k==="produtos") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5"/><line x1="12" y1="22" x2="12" y2="12"/></svg>`;
  if(k==="assuntos") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`;
  if(k==="docs") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/></svg>`;
  if(k==="cadastro") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>`;
  if(k==="rechupe") return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 2.7S6 9 6 14a6 6 0 0 0 12 0c0-5-6-11.3-6-11.3z"/></svg>`;
  return html`<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <line x1="4" y1="20" x2="4" y2="12"/><line x1="10" y1="20" x2="10" y2="4"/>
    <line x1="16" y1="20" x2="16" y2="9"/><line x1="20" y1="20" x2="20" y2="15"/></svg>`;
}
const PAGES={
  painel:["Painel","Visão comercial — vendas, mapa e leads do Lakehouse (consultas feitas como você, com máscara de PII)"],
  cadastro:["Cadastro","Cadastre por formulário ou PDF (prompt editável) · edite, remova e anexe arquivos · Lakebase → CDC → Unity Catalog com PII mascarada"],
  chat:["Agente","Opus 4.8 com guardrails · Genie (tabelas e PDFs) · memória, cache e RAG no Lakebase"],
  docs:["Documentos","Base de conhecimento do agente — envie, edite, reprocesse e remova documentos (ai_parse_document + vetores no Lakebase)"],
  rechupe:["Preditor de rechupe","Texto livre → parâmetros extraídos pela IA → modelo de ML servido"],
  diagnostico:["Inspeção de peças","Foto da peça → tipo, defeito provável e ação recomendada (visão do Opus 4.8)"],
  assuntos:["Assuntos","Perguntas da inference table do AI Gateway, classificadas pelo guardrail e agrupadas por assunto"]};
function App(){
  const [view,setView]=useState("painel"); const [cfg,setCfg]=useState(null);
  useEffect(()=>{ api("/api/config").then(setCfg).catch(()=>{}); },[]);
  const NAV=[["painel","Painel"],["cadastro","Cadastro"],["diagnostico","Peças"],["rechupe","Rechupe"],["docs","Documentos"],["chat","Agente"],["assuntos","Assuntos"]];
  const pg=PAGES[view];
  return html`<div class="app">
    <aside class="side">
      <div class="brand"><img src="/static/logo-white.svg" alt="Fundalis"/><div class="ttl">Fundalis IA<small>Fundição & Usinagem · empresa fictícia</small></div></div>
      <nav class="nav">${NAV.map(([k,l])=>html`<button key=${k} class=${view===k?"active":""} onClick=${()=>setView(k)} title=${l}>
        <span class="ic"><${NavIcon} k=${k}/></span><span class="tx">${l}</span></button>`)}</nav>
      <div class="foot">
        <div>👤 <b>${cfg?cfg.usuario:"…"}</b></div>
        <div style=${{opacity:.85}}>${cfg?(cfg.obo?"Consultas on-behalf-of (OBO)":"Service principal do app"):""}</div>
        <div style=${{marginTop:"6px"}}>Modelo: <code>${cfg?cfg.modelo:""}</code></div>
        <div style=${{marginTop:"6px",opacity:.8}}>Todos os dados são fictícios</div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div><h1>${pg[0]}</h1><div class="sub">${pg[1]}</div></div>
        <div class="right"><span class="pill live">ao vivo</span>${cfg&&cfg.genie?html`<span class="pill">✨ Genie</span>`:null}<span class="pill">🗄️ Lakebase</span></div>
      </header>
      <div class=${"scroll "+(view==="chat"?"full":"fit")} key=${view}>
        ${view==="chat"?html`<${Assistente}/>`:html`<div class="wrap">
          ${view==="painel"&&html`<${Painel}/>`}
          ${view==="cadastro"&&html`<${Cadastro}/>`}
          ${view==="assuntos"&&html`<${Assuntos}/>`}
          ${view==="docs"&&html`<${Documentos}/>`}
          ${view==="rechupe"&&html`<${Rechupe}/>`}
          ${view==="diagnostico"&&html`<${Diagnostico}/>`}
        </div>`}
      </div>
    </div>
  </div>`;
}
ReactDOM.createRoot(document.getElementById("root")).render(html`<${App}/>`);
