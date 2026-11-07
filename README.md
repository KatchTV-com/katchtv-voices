# KatchTV voices

Makes the audio for the **Read** button on [katchtv.com/blog](https://katchtv.com/blog), in KatchTV's own voices **Female 1** and **Male 1**.

- `make_voices.py` voices articles with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache 2.0) through [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
- The voice recipes are kept in the private `VOICE_RECIPE` secret. They are not in this repo.
- `.github/workflows/voices.yml` runs daily. It voices the articles listeners asked for (`https://katchtv.com/api/voice` and `requests/*.json`) and puts the audio on the `audio` branch, one commit only so the repo stays small.
- katchtv.com plays the audio at `/v/<article>.json` and `/v/<article>-f1.mp3` / `-m1.mp3`, through Cloudflare and cached there.
- Each sentence is made once and cached, so an edit only re-voices the sentences that changed.

**No cost:** GitHub Actions on standard runners is free for public repos. The job stops by itself if this repo is ever made private.

**Stays on by itself:** GitHub pauses scheduled jobs in public repos after 60 days with no activity, so every run re-enables the job and resets that clock. A monthly check also reminds Wonder if it is ever off.
