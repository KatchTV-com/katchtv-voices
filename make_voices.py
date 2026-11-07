#!/usr/bin/env python3
"""KatchTV's own Read-button voices, Female 1 and Male 1 (Wonder 2026-11-07). Run by the daily GitHub job .github/workflows/voices.yml
in the PUBLIC repo KatchTV-com/katchtv-voices (GitHub runs jobs in public repos free of charge).

usage: python3 make_voices.py REQUESTS.json OUT_DIR [SECONDS]      (or: ... REQUESTS.json OUT_DIR --todo  → prints how many articles need voicing)
  REQUESTS.json  [{"slug": "...", "parts": ["sentence as read.js speaks it", ...]}]  (D1 table voice_requests)
  OUT_DIR        v/ of the "audio" branch (katchtv.com/v/... serves it through Cloudflare)
  SECONDS        stop making new sentences after this many seconds (default 150); just run it again to continue.
Each sentence is made once and kept in ~/kk/cache/<f|m>/<key>.npy, so nothing is made twice.
Per article it writes <slug>-f1.mp3, <slug>-m1.mp3 and <slug>.json (where each sentence starts and ends).
The voices are mixed from the free Kokoro voices with the recipe in the VOICE_RECIPE secret (kept private, so Female 1 / Male 1 stay ours):
  {"f": {"<kokoro voice>": weight, ...}, "m": {...}}
Model files: ~/kk/kokoro.onnx (kokoro-v1.0.onnx) and ~/kk/voices.bin (voices-v1.0.bin), from
https://github.com/thewh1teagle/kokoro-onnx/releases (Kokoro-82M, Apache 2.0).
"""
import json, os, sys, time, subprocess, tempfile
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = ('f', 'm')
SR, GAP = 24000, 0.28
B36 = '0123456789abcdefghijklmnopqrstuvwxyz'

def vkey(t):  # same as vkey() in site/assets/read.js: FNV-1a over UTF-8 + byte length in base 36
    b = t.encode('utf-8'); h = 0x811c9dc5
    for x in b: h ^= x; h = (h * 0x01000193) & 0xffffffff
    n, s = len(b), ''
    while True:
        s = B36[n % 36] + s; n //= 36
        if not n: break
    return '%08x' % h + s

def main():
    req = json.load(open(sys.argv[1])); out = sys.argv[2]
    if isinstance(req, dict): req = req.get('requests', [])
    def needs(r):
        keys = [vkey(p) for p in r['parts'] if p.strip()]; mf = os.path.join(out, r['slug'] + '.json')
        old = json.load(open(mf)) if os.path.exists(mf) else {}
        return not all(old.get(g, {}).get('p', {}).get(kk) for g in VOICES for kk in keys)
    if len(sys.argv) > 3 and sys.argv[3] == '--todo': print(sum(1 for r in req if needs(r))); return
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 150
    home = os.environ.get('KOKORO_DIR', os.path.expanduser('~/kk')); cache = os.path.join(home, 'cache'); t0 = time.time()
    k = None
    styles = None
    os.makedirs(out, exist_ok=True); finished = True
    for r in req:
        slug, parts = r['slug'], [p for p in r['parts'] if p.strip()]
        keys = [vkey(p) for p in parts]
        mf = os.path.join(out, slug + '.json'); old = json.load(open(mf)) if os.path.exists(mf) else {}
        if all(old.get(g, {}).get('p', {}).get(kk) for g in VOICES for kk in keys): print('ok   ', slug); continue
        ready = True
        for g in VOICES:
            os.makedirs(os.path.join(cache, g), exist_ok=True)
            for p, kk in zip(parts, keys):
                f = os.path.join(cache, g, kk + '.npy')
                if os.path.exists(f): continue
                if time.time() - t0 > budget: ready = False; break
                if k is None:
                    rec = os.environ.get('VOICE_RECIPE')
                    if not rec: sys.exit('VOICE_RECIPE secret is missing (Settings > Secrets and variables > Actions)')
                    R, bank = json.loads(rec), np.load(os.path.join(home, 'voices.bin'))
                    styles = {g2: sum(bank[n] * w for n, w in R[g2].items()) for g2 in VOICES}
                    from kokoro_onnx import Kokoro
                    k = Kokoro(os.path.join(home, 'kokoro.onnx'), os.path.join(home, 'voices.bin'))
                a, _ = k.create(p, voice=styles[g], speed=1.0, lang='en-us'); np.save(f, a.astype(np.float32))
            if not ready: break
        if not ready: finished = False; print('more ', slug); break
        man = {'slug': slug}
        for g in VOICES:
            seen, chunks, pos = {}, [], 0.0; gap = np.zeros(int(GAP * SR), dtype=np.float32)
            for kk in keys:
                if kk in seen: continue
                a = np.load(os.path.join(cache, g, kk + '.npy')); seen[kk] = [round(pos, 3), round(pos + len(a) / SR, 3)]
                chunks += [a, gap]; pos += len(a) / SR + GAP
            with tempfile.TemporaryDirectory() as td:
                wav = os.path.join(td, 'a.wav'); sf.write(wav, np.concatenate(chunks), SR)
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ac', '1', '-b:a', '48k', os.path.join(out, f'{slug}-{g}1.mp3')], check=True)
            man[g] = {'file': f'{slug}-{g}1.mp3', 'p': seen}
        man['ver'] = vkey(json.dumps([man['f']['p'], man['m']['p']], sort_keys=True))[:8]
        json.dump(man, open(mf, 'w'), separators=(',', ':')); print('made ', slug)
    print('ALL DONE' if finished else 'RUN AGAIN')

if __name__ == '__main__':
    main()
