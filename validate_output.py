#!/usr/bin/env python3
"""Check completed exports against the journal and report gaps for review."""
import json
from pathlib import Path
import re
import sys
from transcribe import stamp, validate

out = Path(sys.argv[1])
run = json.loads((out / 'run.json').read_text())
assert run['complete'] and run['status'] == 'completed', 'Run not complete'
data = json.loads((out / 'transcript.json').read_text())
segments = data['segments']
journal = [json.loads(line) for line in (out / 'segments.jsonl').read_text().splitlines()]
assert data['metadata'] == run and journal == segments
assert run['segment_count'] == len(segments)
validate(segments, run['duration_seconds'])
cues = (out / 'transcript.srt').read_text().strip().split('\n\n') if segments else []
assert len(cues) == len(segments)
for i, (cue, segment) in enumerate(zip(cues, segments), 1):
    lines = cue.splitlines()
    assert lines[0] == str(i)
    assert lines[1] == f"{stamp(segment['start'])} --> {stamp(segment['end'])}"
    assert '\n'.join(lines[2:]) == segment['text'].strip()
    for word in segment.get('words') or []:
        assert 0 <= word['start'] <= word['end'] <= run['duration_seconds'] + 0.5
assert (out / 'transcript.txt').read_text() == '\n'.join(s['text'] for s in segments) + '\n'
gaps = []
previous = 0
for segment in segments:
    if segment['start'] - previous > 15:
        gaps.append(dict(start=previous, end=segment['start']))
    previous = segment['end']
if run['duration_seconds'] - previous > 15:
    gaps.append(dict(start=previous, end=run['duration_seconds']))
repeated = []
for i in range(1, len(segments)):
    if segments[i]['text'].strip().lower() == segments[i-1]['text'].strip().lower():
        repeated.append(dict(start=segments[i]['start'], text=segments[i]['text']))
report = dict(export_checks='passed', segments=len(segments), duration_seconds=run['duration_seconds'], elapsed_seconds=run['elapsed_seconds'], gaps_over_15_seconds=gaps, consecutive_repeated_segments=repeated, audio_listening_review=False)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
