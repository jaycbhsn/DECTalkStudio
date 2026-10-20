/* DECtalk in the browser.
   - A tiny in-memory file system (WASI) holds DECtalk.conf, the dictionary and rendered WAVs.
   - DECtalk's pipeline threads run as green threads: when one would block it calls fb_yield,
     we save its stack with Asyncify and switch to the next, round-robin, on this one JS thread. */
(function (root) {
  "use strict";
  const STACK = 512 * 1024, ABUF = 256 * 1024;
  const E = { OK: 0, BADF: 8, INVAL: 28, NOENT: 44, SPIPE: 70 };

  class DECtalkEngine {
    constructor() { this.files = new Map(); this.log = []; }

    async init(wasmBytes, files) {
      for (const [p, d] of Object.entries(files)) this.files.set(p, d instanceof Uint8Array ? d : new TextEncoder().encode(d));
      this.fds = new Map([[3, { dir: true, path: "" }]]);
      this.nextFd = 4;
      this.fibers = []; this.nextId = 1; this.cur = null;
      const { instance } = await WebAssembly.instantiate(wasmBytes, { wasi_snapshot_preview1: this._wasi(), env: this._env() });
      this.ex = instance.exports;
      this.ex._initialize();
      this.mainSP = this.ex.__stack_pointer.value;
      this.mainBuf = this._buf();
      const r = this._call(0, 0, 0);
      if (r !== 0) throw new Error("DECtalk failed to start (code " + r + ")");
      return this;
    }

    /* ---------- public API ---------- */
    render(text) {
      const out = "render.wav";
      this.files.delete(out);
      const r = this._withStrings([out, text], (a, b) => this._call(1, a, b));
      const wav = this.files.get(out);
      if (r !== 0 || !wav) throw new Error("render failed");
      return wav.slice();
    }
    phonemes(text) {
      const out = "phonemes.log";
      const r = this._withStrings([out, text], (a, b) => this._call(2, a, b));
      const log = this.files.get(out);
      if (r !== 0 || !log) throw new Error("lookup failed");
      return new TextDecoder("latin1").decode(log);
    }

    /* ---------- green threads ---------- */
    _buf() { const p = this.ex.malloc(ABUF); return { p, size: ABUF }; }
    _armBuf(b) { const v = new DataView(this.ex.memory.buffer); v.setInt32(b.p, b.p + 8, true); v.setInt32(b.p + 4, b.p + b.size, true); }
    _env() {
      return {
        fb_spawn: (fn, arg) => {
          const base = this.ex.malloc(STACK);
          const f = { id: this.nextId++, fn, arg, base, sp: (base + STACK) & ~15, buf: this._buf(), state: "new" };
          this.fibers.push(f); return f.id;
        },
        fb_current: () => this.cur ? this.cur.id : 0,
        fb_done: id => { const f = this.fibers.find(x => x.id === id); return !f || f.state === "done" ? 1 : 0; },
        fb_yield: () => this._yield(false),
        fb_exit: () => this._yield(true),
      };
    }
    _yield(exiting) {
      if (this.ex.asyncify_get_state() === 2) { this.ex.asyncify_stop_rewind(); return; } // resumed here
      this.cur.exiting = exiting;
      this._armBuf(this.cur.buf);
      this.ex.asyncify_start_unwind(this.cur.buf.p);
    }
    _run(f) {
      const ex = this.ex;
      this.cur = f;
      ex.__stack_pointer.value = f.sp;
      if (f.state === "suspended") ex.asyncify_start_rewind(f.buf.p);
      f.state = "running";
      /* thread bodies are called through the function table from JS, which tolerates DECtalk's
         loosely-typed thread functions (a wasm-side indirect call would trap on the mismatch) */
      const ret = f.main ? ex.dt_api(f.op, f.a, f.b) : (ex.__indirect_function_table.get(f.fn)(f.arg), 0);
      if (ex.asyncify_get_state() === 1) {
        ex.asyncify_stop_unwind();
        f.sp = ex.__stack_pointer.value;
        f.state = f.exiting ? "done" : "suspended";
      } else { f.state = "done"; f.ret = ret; }
      this.cur = null;
    }
    _call(op, a, b) {
      const main = { id: 0, main: true, op, a, b, sp: this.mainSP, buf: this.mainBuf, state: "new" };
      const t0 = Date.now();
      while (main.state !== "done") {
        this._run(main);
        if (main.state === "done") break;
        for (const f of this.fibers.slice()) if (f.state !== "done") this._run(f);
        const dead = this.fibers.filter(f => f.state === "done");
        if (dead.length) {
          for (const f of dead) { this.ex.free(f.base); this.ex.free(f.buf.p); }
          this.fibers = this.fibers.filter(f => f.state !== "done");
        }
        if (Date.now() - t0 > 30000) throw new Error("DECtalk stopped responding");
      }
      this.ex.__stack_pointer.value = this.mainSP;
      return main.ret;
    }
    _withStrings(list, fn) {
      const enc = new TextEncoder(), ptrs = list.map(s => {
        const b = enc.encode(s), p = this.ex.malloc(b.length + 1);
        const m = new Uint8Array(this.ex.memory.buffer, p, b.length + 1); m.set(b); m[b.length] = 0; return p;
      });
      try { return fn(...ptrs); } finally { ptrs.forEach(p => this.ex.free(p)); }
    }

    /* ---------- minimal WASI: an in-memory file system ---------- */
    _wasi() {
      const self = this;
      const mem = () => this.ex.memory.buffer;
      const dv = () => new DataView(mem());
      const str = (p, l) => new TextDecoder().decode(new Uint8Array(mem(), p, l));
      const norm = p => p.replace(/^(\.\/)+/, "").replace(/^\/+/, "");
      const file = fd => self.fds.get(fd);
      const ensure = (f, need) => {
        let d = self.files.get(f.path);
        if (d.length < need) { const n = new Uint8Array(Math.max(need, d.length * 2 + 4096)); n.set(d); n.fill(0, d.length); d = n; self.files.set(f.path, d); f.cap = true; }
        return d;
      };
      const size = f => f.len != null ? f.len : self.files.get(f.path).length;
      return {
        environ_get: () => 0,
        environ_sizes_get: (c, s) => { dv().setUint32(c, 0, true); dv().setUint32(s, 0, true); return 0; },
        clock_time_get: (id, prec, out) => {
          const ns = id === 0 ? BigInt(Date.now()) * 1000000n : BigInt(Math.round(performance.now() * 1e6));
          dv().setBigUint64(out, ns, true); return 0;
        },
        fd_close: fd => {
          const f = file(fd); if (!f) return E.BADF;
          if (f.len != null && !f.dir) self.files.set(f.path, self.files.get(f.path).slice(0, f.len));
          self.fds.delete(fd); return 0;
        },
        fd_fdstat_get: (fd, out) => {
          const f = file(fd); if (fd > 2 && !f) return E.BADF;
          const v = dv(); v.setUint8(out, fd <= 2 ? 2 : f.dir ? 3 : 4); v.setUint16(out + 2, 0, true);
          v.setBigUint64(out + 8, 0xFFFFFFFFFFFFFFFFn, true); v.setBigUint64(out + 16, 0xFFFFFFFFFFFFFFFFn, true); return 0;
        },
        fd_fdstat_set_flags: () => 0,
        fd_prestat_get: (fd, out) => { if (fd !== 3) return E.BADF; dv().setUint8(out, 0); dv().setUint32(out + 4, 1, true); return 0; },
        fd_prestat_dir_name: (fd, p, l) => { if (fd !== 3) return E.BADF; new Uint8Array(mem(), p, 1)[0] = 47; return 0; },
        path_open: (dirfd, dflags, p, l, oflags, rb, ri, fdflags, out) => {
          const path = norm(str(p, l));
          if (path === "" || path === "." || (oflags & 2)) { const fd = self.nextFd++; self.fds.set(fd, { dir: true, path }); dv().setUint32(out, fd, true); return 0; }
          if (!self.files.has(path)) { if (!(oflags & 1)) return E.NOENT; self.files.set(path, new Uint8Array(0)); }
          else if (oflags & 8) self.files.set(path, new Uint8Array(0));
          const fd = self.nextFd++;
          self.fds.set(fd, { path, pos: 0, len: self.files.get(path).length, append: !!(fdflags & 1) });
          dv().setUint32(out, fd, true); return 0;
        },
        fd_read: (fd, iovs, n, nread) => {
          const f = file(fd); if (!f || f.dir) return E.BADF;
          const d = self.files.get(f.path), end = size(f); let total = 0; const v = dv();
          for (let i = 0; i < n; i++) {
            const ptr = v.getUint32(iovs + i * 8, true), len = v.getUint32(iovs + i * 8 + 4, true);
            const k = Math.max(0, Math.min(len, end - f.pos));
            new Uint8Array(mem(), ptr, k).set(d.subarray(f.pos, f.pos + k)); f.pos += k; total += k;
            if (k < len) break;
          }
          v.setUint32(nread, total, true); return 0;
        },
        fd_write: (fd, iovs, n, nw) => {
          const v = dv(); let total = 0;
          if (fd <= 2) {
            for (let i = 0; i < n; i++) { const ptr = v.getUint32(iovs + i * 8, true), len = v.getUint32(iovs + i * 8 + 4, true); total += len; self.log.push(str(ptr, len)); if (self.log.length > 200) self.log.shift(); }
            v.setUint32(nw, total, true); return 0;
          }
          const f = file(fd); if (!f || f.dir) return E.BADF;
          if (f.append) f.pos = size(f);
          for (let i = 0; i < n; i++) {
            const ptr = v.getUint32(iovs + i * 8, true), len = v.getUint32(iovs + i * 8 + 4, true);
            const d = ensure(f, f.pos + len); d.set(new Uint8Array(mem(), ptr, len), f.pos);
            f.pos += len; f.len = Math.max(size(f), f.pos); total += len;
          }
          v.setUint32(nw, total, true); return 0;
        },
        fd_seek: (fd, off, whence, out) => {
          const f = file(fd); if (!f || f.dir) return fd <= 2 ? E.SPIPE : E.BADF;
          const o = Number(off), base = whence === 0 ? 0 : whence === 1 ? f.pos : size(f);
          if (base + o < 0) return E.INVAL;
          f.pos = base + o; dv().setBigUint64(out, BigInt(f.pos), true); return 0;
        },
        fd_tell: (fd, out) => { const f = file(fd); if (!f) return E.BADF; dv().setBigUint64(out, BigInt(f.pos), true); return 0; },
        path_readlink: () => E.INVAL,
        path_remove_directory: () => E.NOENT,
        path_unlink_file: (fd, p, l) => self.files.delete(norm(str(p, l))) ? 0 : E.NOENT,
        proc_exit: code => { throw new Error("DECtalk exited (" + code + ")"); },
      };
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = DECtalkEngine;
  else root.DECtalkEngine = DECtalkEngine;
})(typeof self !== "undefined" ? self : this);
