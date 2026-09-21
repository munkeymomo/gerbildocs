"""Add the desktop bridge to the Document Desk page.

The page stays a single self-contained file that works when opened directly.
When it is served by the desktop backend, `window.__DESK_API` and
`window.__DESK_TOKEN` are injected into the document head, the bridge connects,
and persistence and file writing move from localStorage and blob downloads to
the backend. Nothing else in the page changes.
"""
import re, sys, pathlib

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
s = src.read_text(encoding="utf-8")

SHIM = r'''
/* ============================ DESKTOP BRIDGE ============================
   Inert when the page is opened on its own. When the desktop backend serves
   it, state lives in the vault and exports are written into the document
   folder instead of coming down as browser downloads. */
const DESK = (() => {
  const api = window.__DESK_API || null;
  const token = window.__DESK_TOKEN || null;
  let docId = null, online = false, pending = null, saving = false;

  const headers = () => ({ "Content-Type": "application/json",
                           "Authorization": "Bearer " + token });
  async function req(path, opts) {
    const r = await fetch(api + path, Object.assign({ headers: headers() }, opts || {}));
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0, 240));
    return r.status === 204 ? null : r.json();
  }
  async function form(path, fd) {
    const r = await fetch(api + path, { method: "POST", body: fd,
                                        headers: { "Authorization": "Bearer " + token } });
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0, 240));
    return r.json();
  }
  return {
    get online() { return online; },
    get docId() { return docId; },
    get documentsDir() { return window.__DESK_DOCUMENTS_DIR || ""; },

    async connect() {
      if (!api || !token) return false;
      try { online = !!(await req("/health")).ok; } catch (e) { online = false; }
      return online;
    },
    /* Most recently updated document, or null if this is a fresh install. */
    async openLatest() {
      const { documents } = await req("/documents");
      if (!documents.length) return null;
      docId = documents[0].id;
      return (await req("/documents/" + docId)).state;
    },
    async create(title, kind, state) {
      const d = await req("/documents", { method: "POST",
        body: JSON.stringify({ title, kind, state: state || {} }) });
      docId = d.id;
      return d.state;
    },
    /* Coalesced: rapid edits produce one write, and one in flight at a time. */
    saveState(state) {
      if (!online || !docId) return;
      pending = state;
      if (saving) return;
      saving = true;
      setTimeout(async () => {
        const body = pending; pending = null;
        try { await req("/documents/" + docId, { method: "PUT",
                        body: JSON.stringify({ state: body }) }); }
        catch (e) { console.warn("save failed", e); }
        saving = false;
        if (pending) this.saveState(pending);
      }, 600);
    },
    async writeFile(relative, data) {
      if (!online || !docId) return null;
      let body;
      if (typeof data === "string") body = { relative, text: data };
      else body = { relative, base64: await toBase64(data) };
      return req("/documents/" + docId + "/files", { method: "POST", body: JSON.stringify(body) });
    },
    async uploadAttachment(target, attachmentId, file, note) {
      if (!online || !docId) return null;
      const fd = new FormData();
      fd.append("target", target); fd.append("attachment_id", attachmentId);
      fd.append("note", note || ""); fd.append("upload", file, file.name);
      return form("/documents/" + docId + "/attachments", fd);
    },
    async addRevision(revision) {
      if (!online || !docId) return null;
      return req("/documents/" + docId + "/revisions", { method: "POST",
        body: JSON.stringify({ revision }) });
    },
    async tree() {
      if (!online || !docId) return null;
      return req("/documents/" + docId + "/tree");
    }
  };
  function toBase64(data) {
    const blob = data instanceof Blob ? data : new Blob([data]);
    return new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => res(String(fr.result).split(",")[1]);
      fr.onerror = rej;
      fr.readAsDataURL(blob);
    });
  }
})();
'''

# 1. bridge goes in just before the boot block
anchor = "/* ============================ BOOT ============================ */"
assert anchor in s, "boot marker missing"
s = s.replace(anchor, SHIM + "\n" + anchor, 1)

# 2. save() also pushes to the vault
old_save = 'function save(){ try{ localStorage.setItem(LSK,JSON.stringify(S)); }catch(e){} }'
new_save = ('function save(){ try{ localStorage.setItem(LSK,JSON.stringify(S)); }catch(e){}\n'
            '  if(typeof DESK!=="undefined" && DESK.online) DESK.saveState(S); }')
assert old_save in s, "save() not found"
s = s.replace(old_save, new_save, 1)

# 3. boot becomes async so the vault can answer first
old_boot = """if(window.MathJax&&MathJax.startup&&MathJax.startup.promise) MathJax.startup.promise.then(()=>{ mathReady=true; try{render();}catch(e){} });
S=load()||seed();
migrate();"""
new_boot = """if(window.MathJax&&MathJax.startup&&MathJax.startup.promise) MathJax.startup.promise.then(()=>{ mathReady=true; try{render();}catch(e){} });

async function boot(){
  let remote=null;
  if(await DESK.connect()){
    S_EDITION_ONLINE=true;
    try{ remote=await DESK.openLatest(); }catch(e){ console.warn("vault unreadable",e); }
  }
  S = remote || load() || seed();
  if(DESK.online && !remote){
    // first run against a vault: hand it what is on screen so a folder exists
    try{ S = await DESK.create(S.title, S.kind, S) || S; }catch(e){ console.warn("create failed",e); }
  }
  migrate();"""
assert old_boot in s, "boot block not found"
s = s.replace(old_boot, new_boot, 1)

old_tail = """render();
window.addEventListener("keydown","""
new_tail = """  render();
}
let S_EDITION_ONLINE=false;
boot();
window.addEventListener("keydown","""
assert old_tail in s, "boot tail not found"
s = s.replace(old_tail, new_tail, 1)

# migrate() is a function declaration inside the old top-level flow; keep it reachable
s = s.replace("function migrate(){\n  const d=seed();", "function migrate(){\n  const d=seed();", 1)

# 4. exports go into the document folder when there is one
old_sf = """async function saveFile(name,data,textFallback){
  const ns=await dlNamespace();"""
new_sf = """async function saveFile(name,data,textFallback){
  if(typeof DESK!=="undefined" && DESK.online){
    try{ const r=await DESK.writeFile(name,data);
      if(r){ toast("Written to "+r.path.replace(/^.*[\\\\/]/,"")+" in the document folder"); return true; } }
    catch(e){ console.warn("vault write failed",e); }
  }
  const ns=await dlNamespace();"""
assert old_sf in s, "saveFile not found"
s = s.replace(old_sf, new_sf, 1)

# 5. attachments carry their bytes when there is somewhere to put them
old_att = """  on("[data-attach]","change",e=>{ const ref=e.target.dataset.attach;
    [...e.target.files].forEach(f=>S.attachments.push({id:uid("at"),name:f.name,bytes:f.size,type:f.type||"unknown",
      target:ref,addedAt:nowISO(),note:"",stored:false}));
    commit(e.target.files.length+" file(s) filed under data/"+targetFolder(ref)+"/"); });"""
new_att = """  on("[data-attach]","change",async e=>{ const ref=e.target.dataset.attach, files=[...e.target.files];
    for(const f of files){
      const id=uid("at");
      let rec={id,name:f.name,bytes:f.size,type:f.type||"unknown",target:ref,addedAt:nowISO(),note:"",stored:false};
      if(typeof DESK!=="undefined" && DESK.online){
        try{ const r=await DESK.uploadAttachment(ref,id,f,"");
          if(r&&r.attachment) rec=Object.assign(rec,r.attachment,{stored:true,addedAt:r.attachment.added_at||rec.addedAt}); }
        catch(err){ console.warn("upload failed",err); }
      }
      S.attachments.push(rec);
    }
    commit(files.length+" file(s) filed under data/"+targetFolder(ref)+"/"); });"""
assert old_att in s, "attachment handler not found"
s = s.replace(old_att, new_att, 1)

# 6. a saved revision is also written to drafts/
old_rev = """    $("#revGo").onclick=()=>{ S.revisions.push({id:uid("rev"),at:nowISO(),label:$("#revLbl").value||"Revision "+(S.revisions.length+1),
      by:"Mark Isaacs",snapshot:snapshotNow(),comments:[]}); closeModal(); commit("Revision saved"); }; };"""
new_rev = """    $("#revGo").onclick=()=>{ const rev={id:uid("rev"),at:nowISO(),label:$("#revLbl").value||"Revision "+(S.revisions.length+1),
      by:(S.me&&S.me.name)||"Unnamed editor",kind:"revision",snapshot:snapshotNow(),comments:[]};
      S.revisions.push(rev); closeModal(); commit("Revision saved");
      if(typeof DESK!=="undefined" && DESK.online) DESK.addRevision(rev).catch(()=>{}); }; };"""
assert old_rev in s, "revision handler not found"
s = s.replace(old_rev, new_rev, 1)

# 7. the header says which edition is actually running
old_chip = '''  if(ec){ const web=S.edition==="browser";'''
new_chip = '''  if(ec){ const web=S.edition==="browser";
    if(typeof DESK!=="undefined" && DESK.online){
      ec.textContent="Desktop edition · vault connected"; ec.className="chip desk";
      ec.style.cursor="default"; ec.title="Documents are stored on this machine"; ec.onclick=null;
      const dd=$("#docDir"); if(dd && S.dir) dd.textContent=S.dir;
      return;
    }'''
assert old_chip in s, "edition chip not found"
s = s.replace(old_chip, new_chip, 1)

dst.write_text(s, encoding="utf-8")
print(f"wrote {dst} ({len(s)} bytes)")
