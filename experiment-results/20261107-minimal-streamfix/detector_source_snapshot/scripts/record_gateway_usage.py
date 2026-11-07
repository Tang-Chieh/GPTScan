"""Read only gateway usage counters; never read/copy credential tables."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    db = sqlite3.connect('file:' + str(args.database.resolve()) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    usage = db.execute("SELECT recorded_at,provider,model,requests,input_tokens,output_tokens,cache_read_tokens FROM client_usage WHERE app='gateway' AND provider='openai-codex' AND model='gpt-5.6-luna' ORDER BY recorded_at DESC LIMIT 1").fetchone()
    limits = db.execute("SELECT recorded_at,account_id,limit_id,label,used_fraction,resets_at FROM usage_history WHERE provider='openai-codex' ORDER BY recorded_at DESC LIMIT 2").fetchall()
    report = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'note': 'Gateway cumulative counters and account-wide quota; not necessarily attributable solely to this batch.',
              'gateway': dict(usage) if usage else None, 'quota_snapshots': []}
    for row in limits:
        item = dict(row)
        account = item.pop('account_id')
        item['account_id_sha256'] = hashlib.sha256(account.encode()).hexdigest() if account else None
        report['quota_snapshots'].append(item)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError('Do not overwrite previous usage evidence')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Saved usage-only snapshot; credential tables were not read')


if __name__ == '__main__':
    main()
