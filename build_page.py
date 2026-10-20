#!/usr/bin/env python3
"""Builds DECtalk Studio for the web: one self-contained HTML file.
Starts from the app UI (shared with the Android build), swaps the native engine for the
WebAssembly one, embeds the engine + dictionary, and adds mouse/keyboard controls."""
import base64, gzip, sys

SRC = '/home/claude/app/assets/web/index.html'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/web/dectalk-studio.html'
s = open(SRC, encoding='utf-8').read()

def rep(a, b, count=1):
    global s
    n = s.count(a)
    assert n == count, (n, a[:100])
    s = s.replace(a, b)

# ---------------- engine: native server -> in-page WebAssembly ----------------
rep("""    const r=await fetch('dt/render?q='+encodeURIComponent(spec.text));
    if(!r.ok)throw new Error('render failed');
    const ab=await r.arrayBuffer();""", """    const eng=await startEngine();
    await breathe();
    const ab=eng.render(spec.text).buffer;""")
rep("""  const r=await fetch('dt/phonemes?q='+encodeURIComponent(text));
  if(!r.ok)throw new Error('lookup');
  const t=await r.text();phonCache.set(text,t);return t;""", """  const eng=await startEngine();
  const t=eng.phonemes(text);phonCache.set(text,t);return t;""")
rep("""fetch('dt/ping').then(r=>r.text()).then(t=>setEngine(t.trim()==='ok')).catch(()=>setEngine(false));""",
    """startEngine().catch(()=>{});""")
rep("""/* ================= words → sounds (DECtalk's own dictionary) ================= */""",
"""/* ================= DECtalk engine (WebAssembly, runs in this page) ================= */
let enginePromise=null,lastBreath=0;
/* the engine runs on this thread, so long render batches pause briefly to keep the page responsive */
const breathe=()=>{const now=performance.now();if(now-lastBreath<30)return Promise.resolve();
  lastBreath=now;return new Promise(r=>setTimeout(r,0))};
const b64=s=>{const bin=atob(s),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u};
async function gunzip(u){return new Uint8Array(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer())}
function startEngine(){
  if(!enginePromise)enginePromise=(async()=>{
    busy('Starting DECtalk…',0.4);
    try{
      const [wasm,dic]=await Promise.all([gunzip(b64(DT_ASSETS.wasm)),gunzip(b64(DT_ASSETS.dic))]);
      busy('Starting DECtalk…',0.8);
      const eng=await new DECtalkEngine().init(wasm,{'DECtalk.conf':DT_ASSETS.conf,'dic/dtalk_us.dic':dic});
      setEngine(true);return eng;
    }catch(e){setEngine(false,e);throw e}
    finally{busy(null)}
  })();
  return enginePromise;
}

/* ================= words → sounds (DECtalk's own dictionary) ================= */""")
rep("""function setEngine(ok){engineOK=ok;$('engineWarn').classList.toggle('show',!ok)}""",
"""function setEngine(ok,err){engineOK=ok;$('engineWarn').classList.toggle('show',!ok);
  if(!ok&&err)$('engineWarn').textContent=/compile|CompileError|wasm|WebAssembly|Content Security/i.test(String(err&&err.message||err))
    ?'This page isn’t allowed to run DECtalk here (WebAssembly is blocked). Download the page and open the file directly, and it will run in your browser.'
    :'DECtalk couldn’t start in this browser: '+(err&&err.message||err)+'. Try a current version of Chrome, Edge, Firefox or Safari.'}""")
rep("""<div id="engineWarn">The DECtalk engine isn’t running, so notes can’t be sung. Restart the app; if it keeps happening, your device’s processor may not be supported.</div>""",
    """<div id="engineWarn">DECtalk isn’t running, so notes can’t be sung. Reload the page to try again.</div>""")

# ---------------- saving: hosted page, local file, or plain download ----------------
rep("""function saveBlob(bytes,name,mime){
  if(window.DTAndroid&&DTAndroid.saveFile){
    let bin='';const CH=0x8000;for(let i=0;i<bytes.length;i+=CH)bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+CH));
    DTAndroid.saveFile(name,mime,btoa(bin));return;
  }
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([bytes],{type:mime}));a.download=name;a.click();
}""", """/* Saving works three ways: through claude.ai's download prompt when this page is hosted there
   (it can't save .wav, so audio is wrapped in a .zip), the browser's save dialog where offered,
   or a plain download. */
let hostDownloads=null;
if(window.claude&&claude.use)claude.use('downloads').then(d=>{hostDownloads=d}).catch(()=>{});
const CRC_T=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}return t})();
function crc32(u){let c=0xFFFFFFFF;for(let i=0;i<u.length;i++)c=CRC_T[(c^u[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0}
function zipOne(name,data){ /* a .zip holding one uncompressed file */
  const nm=new TextEncoder().encode(name),crc=crc32(data),n=data.length;
  const lh=new DataView(new ArrayBuffer(30));[[0,0x04034b50,4],[4,20,2],[8,0,2],[14,crc,4],[18,n,4],[22,n,4],[26,nm.length,2]].forEach(([o,v,s])=>s===4?lh.setUint32(o,v,true):lh.setUint16(o,v,true));
  const cd=new DataView(new ArrayBuffer(46));[[0,0x02014b50,4],[4,20,2],[6,20,2],[16,crc,4],[20,n,4],[24,n,4],[28,nm.length,2]].forEach(([o,v,s])=>s===4?cd.setUint32(o,v,true):cd.setUint16(o,v,true));
  const off2=30+nm.length+n,ed=new DataView(new ArrayBuffer(22));[[0,0x06054b50,4],[8,1,2],[10,1,2],[12,46+nm.length,4],[16,off2,4]].forEach(([o,v,s])=>s===4?ed.setUint32(o,v,true):ed.setUint16(o,v,true));
  return new Blob([lh,nm,data,cd,nm,ed],{type:'application/zip'});
}
async function saveBlob(bytes,name,mime){
  if(hostDownloads){
    let fname=name,data=new Blob([bytes],{type:mime});
    if(/\\.wav$/i.test(name)){fname=name.replace(/\\.wav$/i,'.zip');data=zipOne(name,bytes)}
    try{await hostDownloads.save({filename:fname,data});toast(fname===name?`Saved ${name}`:`Saved ${fname} (your WAV is inside)`)}
    catch(e){if(e&&e.code!=='declined')toast('This page can’t save files here. Download the page and open it directly to save.')}
    return;
  }
  if(window.showSaveFilePicker){
    try{
      const ext=name.slice(name.lastIndexOf('.'));
      const h=await showSaveFilePicker({suggestedName:name,types:[{description:ext==='.wav'?'WAV audio':'DECtalk Studio project',accept:{[mime]:[ext]}}]});
      const w=await h.createWritable();await w.write(new Blob([bytes],{type:mime}));await w.close();toast(`Saved ${h.name}`);return;
    }catch(e){if(e&&e.name==='AbortError')return}
  }
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([bytes],{type:mime}));a.download=name;document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),10000);toast(`Downloaded ${name}`);
}""")
rep("""window.onSaved=(ok,name)=>toast(ok?`Saved ${name}`:'Not saved');""", "")

# ---------------- mouse: marquee selection, right-click delete, modifier clicks, cursors ----------------
rep("""const LONG_PRESS=500;let pressFx=null;""", """const LONG_PRESS=500;let pressFx=null,marquee=null;""")
rep("""    if(n){const nx0=nx(n.t),ww=Math.max(3,n.d*notePPB);const edge=Math.max(8,Math.min(18,ww/3));
      if(!selNotes.has(n)){selNotes.clear();selNotes.add(n)}""",
"""    if(n&&e.button===2){g=null;return} /* right-click deletes; see contextmenu */
    if(n&&(e.shiftKey||e.ctrlKey||e.metaKey)){ /* add to / remove from the selection */
      if(selNotes.has(n))selNotes.delete(n);else selNotes.add(n);drawNotes();g=null;return}
    if(n){const nx0=nx(n.t),ww=Math.max(3,n.d*notePPB);const edge=Math.max(8,Math.min(18,ww/3));
      if(!selNotes.has(n)){selNotes.clear();selNotes.add(n)}""")
rep("""    else g.mode='empty';
  });""", """    else{g.mode='empty';g.mouse=e.pointerType==='mouse';g.add=e.shiftKey||e.ctrlKey||e.metaKey;g.keep=g.add?new Set(selNotes):new Set()}
  });""")
rep("""    if(g.mode==='empty'||g.mode==='key'){noteX=""",
"""    if(g.mode==='empty'&&g.mouse){ /* mouse drag on empty space draws a selection box */
      const r=el.getBoundingClientRect(),x1=Math.min(g.x,e.clientX-r.left),x2=Math.max(g.x,e.clientX-r.left),y1=Math.min(g.y,e.clientY-r.top),y2=Math.max(g.y,e.clientY-r.top);
      marquee={x1,y1,x2,y2};selNotes=new Set(g.keep);
      for(const n of T().notes){const a=nx(n.t),b=a+n.d*notePPB,c=ny(n.p),d=c+ROWH;if(b>=x1&&a<=x2&&d>=y1&&c<=y2)selNotes.add(n)}
      drawNotes();return}
    if(g.mode==='empty'||g.mode==='key'){noteX=""")
rep("""    } else if(g.undo){sortNotes();save()}
    if(g.mode==='seek'&&g.moved)drawAll();""", """    } else if(g.undo){sortNotes();save()}
    if(marquee){marquee=null;drawNotes()}
    if(g.mode==='seek'&&g.moved)drawAll();""")
rep("""  el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);
  el.addEventListener('wheel',e=>{e.preventDefault();if(e.ctrlKey){notePPB""",
"""  el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);
  el.addEventListener('contextmenu',e=>{e.preventDefault();const r=el.getBoundingClientRect();const n=hit(e.clientX-r.left,e.clientY-r.top);
    if(n){pushUndo();T().notes=T().notes.filter(m=>m!==n);selNotes.delete(n);drawNotes();drawSong();save()}});
  /* hover cursor shows what a press will do */
  el.addEventListener('pointermove',e=>{if(e.buttons||e.pointerType!=='mouse'||!T())return;const r=el.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    let cur='crosshair';if(y<NRULER)cur='pointer';else if(x<KEYW)cur='pointer';else{const n=hit(x,y);if(n){const ww=Math.max(3,n.d*notePPB);cur=x>nx(n.t)+ww-Math.max(8,Math.min(18,ww/3))?'ew-resize':'grab'}}
    el.style.cursor=cur});
  el.addEventListener('wheel',e=>{e.preventDefault();if(e.ctrlKey){notePPB""")
rep("""  const px=nx(curBeat());if(px>=KEYW){""",
"""  if(marquee){c.fillStyle='rgba(228,222,207,.12)';c.strokeStyle='rgba(228,222,207,.7)';c.fillRect(marquee.x1,marquee.y1,marquee.x2-marquee.x1,marquee.y2-marquee.y1);c.strokeRect(marquee.x1+.5,marquee.y1+.5,marquee.x2-marquee.x1,marquee.y2-marquee.y1)}
  const px=nx(curBeat());if(px>=KEYW){""")

# long-press is a touch gesture; with a mouse, double-click edits (holding still before a drag shouldn't open it)
rep("""      const gg=g;pressFx={note:n,t0:performance.now()};requestAnimationFrame(animPress);""",
    """      if(e.pointerType!=='mouse'){const gg=g;pressFx={note:n,t0:performance.now()};requestAnimationFrame(animPress);""")
rep("""        if(navigator.vibrate)try{navigator.vibrate(15)}catch(_){};openNoteEditor(n)},LONG_PRESS);""",
    """        if(navigator.vibrate)try{navigator.vibrate(15)}catch(_){};openNoteEditor(n)},LONG_PRESS);}""")

# only quick presses count toward a double-click (a long hold released isn't a "click")
rep("""    g={x0:e.clientX,y0:e.clientY,x,y,moved:false,sx:noteX,sy:noteY};""",
    """    g={x0:e.clientX,y0:e.clientY,x,y,moved:false,sx:noteX,sy:noteY,t0:performance.now()};""")
rep("""    if(!g.moved&&(g.mode==='move'||g.mode==='resize')){const now=Date.now();""",
    """    if(!g.moved&&(g.mode==='move'||g.mode==='resize')&&performance.now()-g.t0<300){const now=Date.now();""")

# closing a panel hands keyboard focus back to the page, so shortcuts keep working
rep("""function closeSheet(id){$(id).classList.remove('show')}""",
    """const releaseFocus=()=>{const a=document.activeElement;if(a&&a.closest&&a.closest('.scrim'))a.blur()};
function closeSheet(id){$(id).classList.remove('show');releaseFocus()}""")

# ---------------- keyboard ----------------
rep("""document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  if(e.key===' '){e.preventDefault();play()}""",
"""let clip=null,nudgeT=null;
function nudge(dt,dp,dd){
  if(!selNotes.size)return;pushUndo();const step=+$('snap').value||0.25;
  const list=[...selNotes];const minT=Math.min(...list.map(n=>n.t));const sh=Math.max(dt*step,-minT);
  for(const n of list){n.t=+(n.t+sh).toFixed(4);n.p=clamp(n.p+dp,LO,HI);if(dd)n.d=+Math.max(step,n.d+dd*step).toFixed(4)}
  sortNotes();drawNotes();drawSong();save();
  clearTimeout(nudgeT);const first=list.reduce((a,n)=>n.t<a.t?n:a,list[0]);nudgeT=setTimeout(()=>playOne(T(),first),120);
}
function copySel(){if(!selNotes.size)return false;const l=[...selNotes];const t0=Math.min(...l.map(n=>n.t));clip=l.map(n=>({...n,t:n.t-t0}));return true}
function pasteAt(beat){if(!clip||!clip.length){toast('Copy some notes first (Ctrl+C)');return}pushUndo();
  const s=+$('snap').value;const t0=s?Math.round(beat/s)*s:beat;const made=clip.map(n=>({...n,t:+(t0+n.t).toFixed(4)}));
  T().notes.push(...made);sortNotes();selNotes=new Set(made);drawNotes();drawSong();save()}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){const open=[...document.querySelectorAll('.scrim.show')];if(open.length){open.forEach(o=>o.classList.remove('show'));releaseFocus();editNote=null;e.preventDefault();return}
    if(selNotes.size){selNotes.clear();drawNotes()}return}
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT')return;
  if(document.querySelector('.scrim.show'))return;
  const mod=e.ctrlKey||e.metaKey,k=e.key;
  if(view==='notes'){
    if(k==='ArrowLeft'||k==='ArrowRight'){e.preventDefault();const d=k==='ArrowLeft'?-1:1;e.shiftKey?nudge(0,0,d):nudge(d,0,0);return}
    if(k==='ArrowUp'||k==='ArrowDown'){e.preventDefault();nudge(0,(k==='ArrowUp'?1:-1)*(e.shiftKey?12:1),0);return}
    if(mod&&k.toLowerCase()==='a'){e.preventDefault();selNotes=new Set(T().notes);drawNotes();return}
    if(mod&&k.toLowerCase()==='c'){if(copySel()){e.preventDefault();toast(`Copied ${clip.length} note${clip.length>1?'s':''}`)}return}
    if(mod&&k.toLowerCase()==='x'){if(copySel()){e.preventDefault();delSel()}return}
    if(mod&&k.toLowerCase()==='v'){e.preventDefault();pasteAt(curBeat());return}
    if(mod&&k.toLowerCase()==='d'){e.preventDefault();if(copySel()){const l=[...selNotes];pasteAt(Math.max(...l.map(n=>n.t+n.d)))}return}
    if((k==='Enter'||k.toLowerCase()==='e')&&!mod&&selNotes.size){e.preventDefault();openNoteEditor([...selNotes].sort((a,b)=>a.t-b.t)[0]);return}
    if(k.toLowerCase()==='l'&&!mod){e.preventDefault();$('lyricsBtn').click();return}
    if((k==='='||k==='+')&&!mod){notePPB=Math.min(400,notePPB*1.25);drawNotes();return}
    if(k==='-'&&!mod){notePPB=Math.max(12,notePPB/1.25);drawNotes();return}
  }
  if(k==='Tab'&&!mod){e.preventDefault();if(view==='song'){setView('notes');focusTrackNotes()}else setView('song');return}
  if(k==='Home'){e.preventDefault();stop();return}
  if(k==='?'){openSheet('keysSheet');return}
  if(k===' '){e.preventDefault();play()}""")

# keyboard help + menu entry
rep("""  <button data-act="clearCache">Clear voice cache</button>""",
    """  <button data-act="keys">Keyboard &amp; mouse shortcuts</button>
  <button data-act="clearCache">Clear voice cache</button>""")
rep("""  else if(a==='clearCache')""", """  else if(a==='keys')openSheet('keysSheet');
  else if(a==='clearCache')""")
rep("""<div id="busy">""", """<div class="scrim" id="keysSheet"><div class="sheet">
  <h2>Keyboard &amp; mouse</h2>
  <table class="keys">
    <tr><th colspan="2">Anywhere</th></tr>
    <tr><td><kbd>Space</kbd></td><td>Play or pause</td></tr>
    <tr><td><kbd>Home</kbd></td><td>Back to the start</td></tr>
    <tr><td><kbd>Tab</kbd></td><td>Switch between Song and Notes</td></tr>
    <tr><td><kbd>Ctrl</kbd> <kbd>Z</kbd></td><td>Undo</td></tr>
    <tr><td><kbd>Esc</kbd></td><td>Close a panel, or clear the selection</td></tr>
    <tr><td>Wheel / <kbd>Shift</kbd>+wheel</td><td>Scroll up-down / left-right (or drag the scroll bar)</td></tr>
    <tr><th colspan="2">Notes view</th></tr>
    <tr><td>Click empty space</td><td>Add a note</td></tr>
    <tr><td>Drag empty space</td><td>Select notes in a box</td></tr>
    <tr><td><kbd>Shift</kbd>/<kbd>Ctrl</kbd> + click</td><td>Add or remove a note from the selection</td></tr>
    <tr><td>Drag a note / its right edge</td><td>Move / resize</td></tr>
    <tr><td>Double-click a note, or <kbd>Enter</kbd></td><td>Edit the note’s sounds</td></tr>
    <tr><td>Right-click a note</td><td>Delete it</td></tr>
    <tr><td><kbd>←</kbd> <kbd>→</kbd></td><td>Move selected notes by the snap length</td></tr>
    <tr><td><kbd>Shift</kbd> <kbd>←</kbd> <kbd>→</kbd></td><td>Shorten or lengthen selected notes</td></tr>
    <tr><td><kbd>↑</kbd> <kbd>↓</kbd></td><td>Up or down a semitone (<kbd>Shift</kbd>: an octave)</td></tr>
    <tr><td><kbd>Ctrl</kbd> <kbd>C</kbd> / <kbd>X</kbd> / <kbd>V</kbd></td><td>Copy, cut, paste at the playhead</td></tr>
    <tr><td><kbd>Ctrl</kbd> <kbd>D</kbd></td><td>Duplicate the selection after itself</td></tr>
    <tr><td><kbd>Ctrl</kbd> <kbd>A</kbd> / <kbd>Delete</kbd></td><td>Select all / delete selected</td></tr>
    <tr><td><kbd>L</kbd></td><td>Lyrics</td></tr>

    <tr><td><kbd>Ctrl</kbd>+wheel, <kbd>+</kbd> <kbd>−</kbd></td><td>Zoom</td></tr>
  </table>
  <div class="row"><div class="spacer"></div><button class="on" onclick="closeSheet('keysSheet')">Done</button></div>
</div></div>
<div id="busy">""")

# ---------------- desktop layout ----------------
rep("""@media (prefers-reduced-motion:reduce)""", """@media (min-width:760px) and (min-height:560px){
  .scrim{align-items:center}
  .sheet{border-radius:14px;max-height:84%}
  #heads{width:168px}
}
.keys{border-collapse:collapse;width:100%;font-size:14px}
.keys th{text-align:left;color:var(--dim);font-weight:400;padding:12px 0 4px}
.keys td{padding:5px 8px 5px 0;border-bottom:1px solid var(--rule);vertical-align:top}
.keys td:first-child{white-space:nowrap;color:var(--dim)}
kbd{font-family:inherit;background:var(--ink);border:1px solid var(--rule2);border-bottom-width:2px;border-radius:4px;padding:0 5px;color:var(--putty);font-size:13px}
@media (prefers-reduced-motion:reduce)""")
rep("""<title>DECtalk Studio</title>""", """<title>DECtalk Studio</title>
<meta name="description" content="A multitrack singing editor that runs DECtalk in your browser.">""")
rep("""<p class="hint">Voices by DECtalk.""", """<p class="hint">Runs entirely in your browser; nothing is uploaded. Press <kbd>?</kbd> for shortcuts. Voices by DECtalk.""")

# ---------------- embed engine + assets ----------------
engine_js = open('/home/claude/web/engine.js', encoding='utf-8').read()
wasm_gz = base64.b64encode(open('/home/claude/web/dectalk.wasm.gz', 'rb').read()).decode()
dic_gz = base64.b64encode(open('/home/claude/web/dic.gz', 'rb').read()).decode()
conf = open('/home/claude/app/assets/dectalk/DECtalk.conf', encoding='latin1').read().replace('\r', '')
assets = ('<script>\n/* DECtalk engine (WebAssembly, gzip) and US English dictionary, embedded so the page works offline */\n'
          'const DT_ASSETS={conf:' + __import__('json').dumps(conf) + ',\nwasm:"' + wasm_gz + '",\ndic:"' + dic_gz + '"};\n</script>\n'
          '<script>\n' + engine_js + '\n</script>\n')
rep("""<script>
"use strict";""", assets + """<script>
"use strict";""")
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s.encode()) // 1024, 'KB')
