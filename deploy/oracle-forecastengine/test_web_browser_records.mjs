// Confirm cloud UI save/delete is browser-local, never Oracle /records API.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = fs.readFileSync(process.argv[2], 'utf8');
const storage = new Map();
const elements = new Map();
let sentNetworkRequests = 0;
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {hidden: true, textContent: '', className: '',
      disabled: false, value: '', innerHTML: '', open: false});
  }
  return elements.get(id);
}
element('storeId').value = 'test-anonymous-label';
// A record saved before the rename lives under the legacy key only.
const legacyRecord = {record_id: 'legacy-record-id', crop_id: 'cabbage'};
storage.set('tw01_web_browser_only_records_v1', JSON.stringify([legacyRecord]));
const context = vm.createContext({
  console,
  setTimeout: () => {},
  localStorage: {
    getItem: key => storage.get(key) || null,
    setItem: (key, val) => storage.set(key, val),
  },
  window: {crypto: {randomUUID: () => 'web-local-test-id'},
    confirm: () => true},
  document: {getElementById: element, addEventListener: () => {}},
  fetch: async () => {sentNetworkRequests++; throw Error('unexpected HTTP request');},
});
vm.runInContext(source, context, {filename: 'oracle_web_app.js'});
vm.runInContext(
  "lastRun = {request: {crop_id:'cabbage',current_price:32}, " +
    "response: {request_id:'local-test-1',crop_id:'cabbage',market_id:'中義市場'," +
    "mode_executed:'without_last_week',model_version:'0.1.0'," +
    "results:[{horizon_days:7,target_date:'2026-10-21',direction:'flat'," +
    "relative_change_estimate:-0.0486,price_estimate:30.4}]}}",
  context
);
await vm.runInContext('saveCurrentRecord()', context);
let entries = JSON.parse(storage.get('fmpa_web_browser_only_records_v1'));
assert.equal(entries.length, 2);
assert.equal(entries[0].record_id, 'web-local-test-id');
assert.equal(entries[1].record_id, 'legacy-record-id', 'legacy record migrated');
assert.equal(JSON.parse(storage.get('tw01_web_browser_only_records_v1')).length, 1,
  'legacy key is kept for rollback');
assert.equal(entries[0].anonymous_store_label, 'test-anonymous-label');
assert.equal(entries[0].request.current_price, 32);
assert.equal(sentNetworkRequests, 0);
await vm.runInContext("deleteRecord('web-local-test-id', {disabled:false})", context);
entries = JSON.parse(storage.get('fmpa_web_browser_only_records_v1'));
assert.equal(entries.length, 1);
assert.equal(entries[0].record_id, 'legacy-record-id');
assert.equal(sentNetworkRequests, 0);
assert.doesNotMatch(source, /fetchJson\(API_RECORDS/);
console.log('BROWSER_RECORDS_LOCAL_ONLY_AND_DELETION=PASS');
