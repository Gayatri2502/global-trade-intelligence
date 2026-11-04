"""GitHub Actions entry point for persistent per-source contact discovery."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from urllib import error, request
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from run import run

ROOT = Path(__file__).parent
API = 'https://cdnzpncsbxavakbvtgem.supabase.co/rest/v1/rpc/trade_crawler_ledger'
KEY = 'sb_publishable_j3HSf2k6MVooEUqvfpHYvQ_g5EHYTEv'


def rpc(payload, endpoint=API):
    body = json.dumps(payload, separators=(',', ':'))
    stamp = int(time.time())
    signature = hmac.new(os.environ['CRAWLER_SIGNING_SECRET'].encode(),
                         f'{stamp}.{body}'.encode(), hashlib.sha256).hexdigest()
    data = json.dumps(dict(p_body=body, p_timestamp=stamp, p_signature=signature)).encode()
    with request.urlopen(request.Request(endpoint, data=data, headers={'apikey': KEY,
                         'Content-Type': 'application/json'}), timeout=40) as response:
        return json.load(response)


def slots(schedule, now):
    for offset in range(-7, 8):
        day = now.date() + timedelta(days=offset)
        if day.weekday() in schedule['days']:
            for clock in sorted(set(schedule['times'])):
                yield datetime.combine(day, datetime.strptime(clock, '%H:%M').time(), now.tzinfo)


def retry(operation):
    for attempt in range(3):
        try:
            return operation()
        except error.HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            delay = exc.headers.get('Retry-After', '')
            if delay.isdigit() and int(delay) > 60:
                raise
            time.sleep(max(2 ** (attempt+1), int(delay) if delay.isdigit() else 0))
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt+1))


def control(action, **fields):
    return retry(lambda: rpc(dict(action=action, **fields), API.replace('trade_crawler_ledger', 'trade_crawler_control')))


def execute(source, schedule, now, manual=False, dry_run=False):
    history = list(slots(schedule, now))
    last = max((slot for slot in history if slot <= now), default=None)
    next_run = min((slot for slot in history if slot > now), default=None)
    state = {} if dry_run else retry(lambda: rpc({'source': source, 'action': 'state'}))
    slot = last.isoformat() if last else ''
    print(json.dumps(dict(source=source, last_success=state.get('completed_at'),
                          next_run=next_run.isoformat() if next_run else None)))
    requested = control('claim').get('run_id') if not dry_run and source == 'public-company-sites' else None
    if not requested and not manual and (not last or state.get('slot', '') >= slot):
        return True
    started = datetime.now(timezone.utc).isoformat()
    run_id = f'{source}:{slot}' if not manual else f'{source}:manual:{os.getenv("GITHUB_RUN_ID", started)}'
    run_id = requested or run_id
    config = json.loads((ROOT/'config.json').read_text())
    hosts = set(schedule.get('hosts', []))
    config['sources'] = [row for row in config['sources']
                         if not urlsplit(row['url']).path.lower().endswith('.pdf')
                         and (not hosts or (urlsplit(row['url']).hostname or '').removeprefix('www.') in hosts)]
    if not config['sources']:
        raise ValueError('No reviewed company pages match this job')
    config['search_queries'] = []
    last_report = 0
    def report(stage, stats=None, discovered=0):
        if dry_run or source != 'public-company-sites':
            return
        control('progress', run_id=run_id, stage=stage, started_at=started,
                pages_fetched=(stats or {}).get('pages_fetched', 0), discovered=discovered,
                failed_requests=len((stats or {}).get('errors', [])))

    def progress(stats, discovered):
        nonlocal last_report
        if time.monotonic() - last_report >= 10:
            report('crawling', stats, discovered)
            last_report = time.monotonic()

    report('connecting')
    try:
        leads, stats = run(config, progress)
        report('saving', stats, len(leads))
    except Exception as exc:
        if not dry_run:
            retry(lambda: rpc(dict(source=source, run_id=run_id, action='failure',
                                   summary=dict(started_at=started, slot=slot, error_types=[type(exc).__name__]))))
        raise
    summary = dict(started_at=started, slot=slot, discovered=len(leads),
                   failed_requests=len(stats['errors']), pages_fetched=stats['pages_fetched'],
                   error_types=sorted({str(row.get('reason', '')).split(':')[0][:60] for row in stats['errors']
                                       if 'url' not in row}))
    if dry_run:
        print(json.dumps(summary))
        return bool(leads)
    payload = dict(source=source, run_id=run_id, summary=summary,
                   action='save' if leads else 'failure', leads=leads)
    result = retry(lambda: rpc(payload))
    print(json.dumps(result))
    return result.get('status') == 'saved'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manual', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--source', help='Run only this configured source job')
    args = parser.parse_args()
    config = json.loads((ROOT/'schedule.json').read_text())
    now = datetime.now(ZoneInfo(config['timezone']))
    success = True
    if args.source and args.source not in config['sources']:
        parser.error('Unknown source job')
    for source, schedule in config['sources'].items():
        if not schedule['enabled'] or (args.source and args.source != source):
            continue
        try:
            if schedule.get('adapter', 'public-company-sites') != 'public-company-sites':
                raise ValueError('Source adapter is not implemented')
            success = execute(source, schedule, now, args.manual, args.dry_run) and success
        except Exception as exc:
            print(json.dumps(dict(source=source, status='failed', reason=type(exc).__name__,
                                  http_status=getattr(exc, 'code', None))))
            success = False
    raise SystemExit(0 if success else 1)
