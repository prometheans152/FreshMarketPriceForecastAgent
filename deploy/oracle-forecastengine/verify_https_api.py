"""Exercise the deployed HTTPS endpoint using injected service credentials.

The token is never serialized. Only structured engine outputs and statuses are
saved for comparison with Windows native ForecastEngine evidence.
"""
import argparse
import http.client
import json
import os
import ssl
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    token = os.environ['TW01_ORIGIN_API_TOKEN']
    assert len(token) >= 32
    base = {'crop_id': 'cabbage', 'market_id': '中義市場',
            'current_price': 32, 'price_unit': 'NTD_per_taiwan_jin',
            'observed_on': '2026-10-14'}
    checks = [('cabbage_32_jin', '/v1/forecast', base, 200),
              ('cabbage_65_kg', '/v1/forecast', dict(base, current_price=65, price_unit='NTD_per_kg'), 200),
              ('cabbage_historical', '/v1/forecast', dict(base, observed_on='2026-09-30'), 200),
              ('no_date', '/v1/forecast', {k:v for k,v in base.items() if k != 'observed_on'}, 200),
              ('quote', '/v1/market-quote', {'crop_id':'cabbage','market_id':'中義市場'}, 200),
              ('bad_crop', '/v1/forecast', dict(base, crop_id='unknown'), 422),
              ('bad_market', '/v1/forecast', dict(base, market_id='unknown'), 422),
              ('zero', '/v1/forecast', dict(base, current_price=0), 422),
              ('negative', '/v1/forecast', dict(base, current_price=-1), 422),
              ('string_price', '/v1/forecast', dict(base, current_price='32'), 422),
              ('bad_unit', '/v1/forecast', dict(base, price_unit='per_box'), 422),
              ('bad_date', '/v1/forecast', dict(base, observed_on='2026-02-30'), 422),
              ('future_date', '/v1/forecast', dict(base, observed_on='2099-01-01'), 422),
              ('B_forbidden', '/v1/forecast', dict(base, mode='with_last_week'), 422),
              ('save_forbidden', '/v1/forecast', dict(base, save=True), 422),
              ('historical_insufficient', '/v1/forecast', dict(base, observed_on='2000-01-01'), 503)]
    entries=[]
    for label,path,data,expected in checks:
        conn=http.client.HTTPSConnection(args.host, timeout=24, context=ssl.create_default_context())
        try:
            conn.request('POST', path, body=json.dumps(data,ensure_ascii=False).encode('utf-8'),
                         headers={'Content-Type':'application/json', 'Authorization':'Bearer '+token})
            resp=conn.getresponse()
            content=json.loads(resp.read())
            entries.append({'case':label,'status':resp.status,'expected':expected,
                            'pass':resp.status==expected,'response':content if expected==200 else {'error':content.get('error',{}).get('code')}})
        finally:
            conn.close()
        print(('PASS' if entries[-1]['pass'] else 'FAIL')+' '+label+' '+str(entries[-1]['status']))
    report={'total':len(entries),'passed':sum(item['pass'] for item in entries), 'results':entries,
            'authenticated_by_private_service_environment':True,'secrets_recorded':False}
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite test evidence')
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RESULT',report['passed'],'/',report['total'])
    return 0 if report['passed']==report['total'] else 1


if __name__=='__main__':
    raise SystemExit(main())
