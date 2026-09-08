"""Private shared transcription UI. Bind only to loopback behind Tailscale Serve."""
import asyncio
import hmac
import json
import math
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlsplit
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(os.environ.get('TRANSCRIBER_ROOT', Path(__file__).resolve().parent))
STATIC = Path(__file__).resolve().parent / 'web'
MAX_BYTES = 2 * 1024**3
MAX_DURATION = 6 * 3600
FORMATS = {'mp3', 'wav', 'flac', 'ogg', 'mov', 'mp4', 'm4a', '3gp', '3g2', 'mj2', 'matroska', 'webm', 'aac', 'aiff', 'asf', 'avi', 'mpeg', 'mpegts', 'amr'}
ARTIFACTS = {'docx', 'txt', 'md', 'srt', 'json'}
active_uploads = set()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def identity(request):
    config = read_json(ROOT / 'web-config.json')
    admin = request.headers.get('x-transcriber-admin', '')
    if admin and config.get('admin_token') and hmac.compare_digest(admin, config['admin_token']):
        return 'Local administrator'
    login = request.headers.get('tailscale-user-login', '').strip().lower()
    if login and login in [s.lower() for s in config.get('allowed_logins', [])]:
        return login
    raise HTTPException(403, 'Connect through Tailscale using an allowed account. Access is limited to configured accounts.')


@app.middleware('http')
async def security(request, call_next):
    if request.url.path.startswith('/api/'):
        try:
            request.state.user = identity(request)
            if request.method not in ('GET', 'HEAD'):
                if request.headers.get('x-transcriber-request') != '1':
                    raise HTTPException(403, 'Missing request verification header')
                origin = request.headers.get('origin')
                if origin and (urlsplit(origin).netloc != request.headers.get('host') or urlsplit(origin).scheme not in ('http', 'https')):
                    raise HTTPException(403, 'Cross-origin uploads are not allowed')
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response


@app.get('/')
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/assets/{name}')
def asset(name: str):
    if name not in ('app.js', 'style.css'):
        raise HTTPException(404)
    return FileResponse(STATIC / name)


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'local-transcriber-web'}


def job_paths(job_id):
    if not re.fullmatch('[a-f0-9]{12}', job_id):
        raise HTTPException(404, 'Job not found')
    queue = ROOT / 'jobs' / (job_id + '.json')
    if not queue.is_file():
        raise HTTPException(404, 'Job not found')
    return queue, ROOT / 'output' / job_id


def public_job(job_id):
    queue, out = job_paths(job_id)
    job, run = read_json(queue), read_json(out / 'run.json')
    completed = bool(run.get('complete')) and job.get('status') == 'completed'
    status = job.get('status', 'unknown')
    duration = run.get('duration_seconds') or job.get('duration_seconds') or 0
    processed = run.get('last_segment_end', 0)
    percent = 100 if completed else min(99, round(100 * processed / duration)) if duration else 0
    stage = 'completed' if completed else status
    if status == 'running':
        stage = 'transcribing' if run.get('segment_count') else 'preparing'
    error = None
    if status in ('failed', 'interrupted'):
        reason = str(run.get('error') or job.get('error') or '')
        error = 'The worker restarted before this job finished. Upload again to retry.' if status == 'interrupted' else 'Transcription failed. Try uploading again; the original job is preserved.'
        if '10 GiB' in reason or 'busy' in reason:
            error = 'The GPU is busy with another service. Please retry when it is available.'
    return dict(id=job_id, title=job.get('title') or 'Untitled recording', status=stage,
                complete=completed, progress=percent, processed_seconds=processed,
                duration_seconds=duration, segment_count=run.get('segment_count', 0),
                language=run.get('language_detected') or job.get('language', 'auto'),
                submitted_at=job.get('submitted_at'), started_at=job.get('started_at'),
                elapsed_seconds=round((job.get('finished_at') or time.time()) - job['started_at']) if job.get('started_at') else 0,
                error=error, downloads=sorted(ARTIFACTS) if completed else [])


@app.get('/api/jobs')
def jobs(request: Request):
    paths = sorted((ROOT / 'jobs').glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    health = read_json(ROOT / 'service-health.json')
    alive = False
    try:
        if health.get('pid'):
            os.kill(int(health['pid']), 0)
            alive = True
    except (OSError, ValueError):
        pass
    return dict(user=request.state.user, worker=health.get('status', 'offline') if alive else 'offline',
                jobs=[public_job(p.stem) for p in paths if re.fullmatch('[a-f0-9]{12}', p.stem)],
                max_bytes=MAX_BYTES, max_duration_seconds=MAX_DURATION)


@app.get('/api/jobs/{job_id}')
def job(job_id: str):
    return public_job(job_id)


async def probe(path):
    process = await asyncio.create_subprocess_exec('ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-show_format', '-show_streams', '-of', 'json', str(path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
    except BaseException:
        process.kill()
        await process.wait()
        raise
    try:
        info = json.loads(stdout)
        audio = [s for s in info['streams'] if s.get('codec_type') == 'audio']
        formats = set(info['format']['format_name'].split(','))
        duration = float(info['format'].get('duration') or audio[0].get('duration', 0))
        if process.returncode or not audio or not formats.intersection(FORMATS) or not math.isfinite(duration) or duration <= 0:
            raise ValueError()
    except (ValueError, KeyError, IndexError):
        raise HTTPException(422, 'This file is not supported or has no readable audio track.') from None
    if duration > MAX_DURATION:
        raise HTTPException(422, 'Recordings can be up to 6 hours long. Split this file into shorter recordings.')
    return duration


@app.post('/api/jobs', status_code=202)
async def upload(request: Request, filename: str = 'recording', title: str = '', language: str = 'auto'):
    if language not in ('auto', 'en', 'zh'):
        raise HTTPException(422, 'Choose automatic, English or Chinese.')
    title = title.strip() or Path(filename).stem
    if not title or len(title) > 200 or any(ord(c) < 32 for c in title):
        raise HTTPException(422, 'Use a title of 1 to 200 characters without control characters.')
    try:
        size = int(request.headers.get('content-length', '0'))
    except ValueError:
        raise HTTPException(400, 'Invalid upload length') from None
    if size < 0 or size > MAX_BYTES:
        raise HTTPException(413, 'Files can be up to 2 GB.')
    if len(active_uploads) >= 2:
        raise HTTPException(429, 'Two uploads are already in progress. Please try again shortly.')
    if shutil.disk_usage(ROOT).free < max(size, MAX_BYTES) + 4 * 1024**3:
        raise HTTPException(507, 'The PC needs more free disk space before accepting another upload.')
    job_id = uuid.uuid4().hex[:12]
    suffix = Path(filename).suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,8}', suffix):
        suffix = '.media'
    source = ROOT / 'input' / (job_id + suffix)
    partial = source.with_name(source.name + '.part')
    for directory in ('input', 'jobs', 'output'):
        (ROOT / directory).mkdir(exist_ok=True)
    active_uploads.add(job_id)
    committed = False
    try:
        received = 0
        with partial.open('xb') as stream:
            async for chunk in request.stream():
                received += len(chunk)
                if received > MAX_BYTES:
                    raise HTTPException(413, 'Files can be up to 2 GB.')
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if not received or (size and received != size):
            raise HTTPException(400, 'The upload was incomplete. Please try again.')
        try:
            duration = await probe(partial)
        except asyncio.TimeoutError:
            raise HTTPException(422, 'This file took too long to inspect. Try a standard MP3, WAV or MP4 file.') from None
        partial.rename(source)
        payload = dict(status='queued', input=str(source), title=title, language=language,
                       submitted_at=time.time(), duration_seconds=duration, no_vad=False,
                       initial_prompt=None, submitted_by=request.state.user)
        queue = ROOT / 'jobs' / (job_id + '.json')
        temporary = queue.with_suffix('.json.tmp')
        with temporary.open('x') as stream:
            json.dump(payload, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.rename(queue)
        committed = True
        return public_job(job_id)
    finally:
        active_uploads.discard(job_id)
        partial.unlink(missing_ok=True)
        if not committed:
            source.unlink(missing_ok=True)


@app.get('/api/jobs/{job_id}/transcript')
def transcript(job_id: str):
    _, out = job_paths(job_id)
    if not public_job(job_id)['complete']:
        raise HTTPException(409, 'The transcript will be available when processing finishes.')
    data = read_json(out / 'transcript.json')
    # Expose only transcript content; worker diagnostics include private host paths.
    return {'segments': [dict(start=s['start'], end=s['end'], text=s['text']) for s in data.get('segments', [])]}


@app.get('/api/jobs/{job_id}/download/{extension}')
def download(job_id: str, extension: str):
    _, out = job_paths(job_id)
    if extension not in ARTIFACTS:
        raise HTTPException(404)
    item = public_job(job_id)
    if not item['complete']:
        raise HTTPException(409, 'Documents are still being prepared.')
    if extension == 'json':
        return JSONResponse(dict(title=item['title'], language=item['language'], **transcript(job_id)),
            headers={'Content-Disposition': 'attachment; filename="transcript.json"'})
    return FileResponse(out / ('transcript.' + extension), filename='transcript.' + extension)
