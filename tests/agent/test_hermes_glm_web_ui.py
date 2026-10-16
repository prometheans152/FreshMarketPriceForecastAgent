"""Run the actual browser functions without any external model requests."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEGACY_WEB = ROOT / "tests" / "fixtures" / "legacy_chat_web_20261013"


def test_chat_is_prominent_accessible_and_explains_independent_questions():
    # Historical GLM chat frontend is intentionally NOT the active manual Web UI.
    html = (LEGACY_WEB / "index.html").read_text(encoding="utf-8")
    assert html.index('id="agentSection"') < html.index('id="predictForm"')
    assert "聊天查行情／預測" in html
    assert '<label for="agentQuery"' in html
    assert 'id="agentStatus"' in html
    assert "中義市場高麗菜最新公開市場行情" in html
    assert "中義市場高麗菜今天一台斤32元" in html
    assert "每題獨立" in html


CASES = {
    "busy_guard_and_payload": r'''
let finish;
context.fetch = async (url, opts) => { calls.push({url,opts}); return new Promise(resolve => {finish=resolve}); };
context.bindAgent();
const pending = elements.agentBtn.handlers.click();
elements.agentQuery.handlers.keydown({key:'Enter', preventDefault(){}});
assert.equal(calls.length, 1, 'Enter while waiting must not send a duplicate model request');
assert.deepEqual(JSON.parse(calls[0].opts.body), {query:'中義市場高麗菜今天一台斤32元',store_id:'store-test'});
assert.equal(calls[0].url, 'agent/query');
assert.equal(calls[0].opts.method, 'POST');
assert.ok(calls[0].opts.signal, 'chat request must be cancellable');
assert.equal(elements.agentBtn.disabled, true);
finish(response({answer:'資料不足', forecast:null}));
await pending;
assert.equal(elements.agentBtn.disabled, false);
assert.equal(timers.size, 0, 'completed request must clear its timeout');
assert.equal(elements.agentBtn.textContent, '問代理人');
''',
    "timeout_is_bounded_and_understandable": r'''
context.fetch = (url, opts) => new Promise((resolve,reject) => {
  calls.push({url,opts});
  opts.signal?.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), {name:'AbortError'})));
});
context.bindAgent();
const pending = elements.agentBtn.handlers.click();
const timer = [...timers.values()].find(x => x.ms===120000);
assert.ok(timer, 'chat must have the agreed 120 second limit');
timer.fn();
await pending;
assert.equal(calls[0].opts.signal.aborted, true);
assert.ok(/2\s*分鐘|120\s*秒/.test(elements.agentResult.textContent), elements.agentResult.textContent);
assert.ok(elements.agentResult.textContent.includes('稍後'));
assert.equal(elements.agentBtn.disabled, false);
assert.equal(timers.size, 0);
''',
    "malformed_response_is_not_reported_as_network_failure": r'''
context.fetch = async () => ({ok:true,status:200,json:async () => {throw new SyntaxError('not JSON')}});
context.bindAgent();
await elements.agentBtn.handlers.click();
assert.ok(elements.agentResult.textContent.includes('回覆格式'), elements.agentResult.textContent);
assert.ok(!elements.agentResult.textContent.includes('無法連線'));
assert.equal(elements.agentBtn.disabled, false);
''',
    "http_error_and_network_error_restore_controls": r'''
context.fetch = async () => response({error:{message:'聊天設定尚未完成，請補齊設定。'}}, false, 503);
context.bindAgent();
await elements.agentBtn.handlers.click();
assert.ok(elements.agentResult.textContent.includes('聊天設定尚未完成'));
assert.equal(elements.agentBtn.disabled, false);
context.fetch = async () => {throw new TypeError('network failure')};
await elements.agentBtn.handlers.click();
assert.ok(elements.agentResult.textContent.includes('無法連線'));
assert.equal(elements.agentBtn.disabled, false);
assert.equal(timers.size, 0);
''',
    "quote_only_and_details_are_honest_and_safe": r'''
const attack='<img src=x onerror=alert(1)>';
context.renderAgentResult(elements.agentResult, {
  provider:'glm_zai',runtime:'hermes 0.19.0',backend_used:'hermes',degraded:false,
  answer:'中義市場高麗菜行情：30元/台斤，資料日期2026-10-02。',forecast:null,
  tool_trace:[{tool:'get_market_quote',ok:true,validation:'accepted'},
              {tool:'post_forecast',ok:false,validation:'rejected',error:attack}]
});
const text=flatten(elements.agentResult);
assert.ok(!text.includes('上方文字僅供參考'), text);
assert.ok(text.includes('預測') && text.includes('店價') && text.includes('單位'), text);
const details=elements.agentResult.children.find(x => x.tagName==='details');
assert.ok(details, 'technical tool trace should be collapsed under details');
assert.equal(details.open, false);
assert.ok(details.children.some(x => x.tagName==='summary' && x.textContent.includes('查詢詳情')));
assert.ok(flatten(details).includes(attack), 'tool error remains literal text');
assert.ok(!elements.agentResult.htmlWrites, 'untrusted answer/trace must not use HTML');
''',
    "configured_status_is_not_a_live_connection_claim": r'''
const text=context.agentStatusText({provider:'glm_zai',model:'glm-5.3-flash',runtime:'hermes',configured:true,reason:null});
assert.ok(text.includes('GLM') && text.includes('Hermes'));
assert.ok(text.includes('已設定'));
assert.ok(!text.includes('連線成功') && !text.includes('已連線'), text);
assert.ok(text.includes('送出'), text);
''',
    "missing_status_does_not_claim_glm_success": r'''
const text=context.agentStatusText({provider:'glm_zai',model:'',runtime:'hermes',configured:false,reason:'profile_model_missing'});
assert.ok(/未完成|尚未設定|待設定/.test(text), text);
assert.ok(!text.includes('已設定') && !text.includes('連線成功'), text);
const fallback=context.backendLabel({provider:'glm_zai',runtime:'hermes 0.19.0',backend_used:'rule',degraded:true,degraded_reason:'hermes_error'});
assert.ok(fallback.text.includes('降級') && fallback.text.includes('規則'), fallback.text);
''',
    "coding_profile_is_labeled_as_a_personal_local_demo": r'''
const text=context.agentStatusText({provider:'glm_zai_coding',model:'glm-5.3-flash',runtime:'hermes',configured:true,reason:null,local_demo:true});
assert.ok(text.includes('Hermes＋GLM 本機試用'), text);
assert.ok(text.includes('設定就緒') && text.includes('送出後確認'), text);
assert.ok(!text.includes('連線成功') && !text.includes('已連線'), text);
const missing=context.agentStatusText({provider:'glm_zai_coding',runtime:'hermes',configured:false,reason:'api_key_missing',local_demo:true});
assert.ok(!missing.includes('設定就緒'), missing);
''',
    "status_reads_only_the_local_configuration_endpoint": r'''
const status=makeElement('p');
elements.agentStatus=status;
context.fetch=async (url,opts) => {calls.push({url,opts}); return response({provider:'glm_zai',model:'glm-5.3-flash',runtime:'hermes',configured:true,reason:null});};
await context.loadAgentStatus();
assert.equal(calls.length,1);
assert.equal(calls[0].url,'agent/status');
assert.ok(!calls[0].opts?.method || calls[0].opts.method==='GET');
assert.ok(status.textContent.includes('已設定'));
assert.ok(!status.textContent.includes('已連線'));
assert.equal(timers.size,0);
''',
    "status_failure_keeps_chat_usable_without_a_false_label": r'''
elements.agentStatus=makeElement('p');
context.fetch=async () => {throw new TypeError('offline')};
await context.loadAgentStatus();
assert.ok(elements.agentStatus.textContent.includes('無法讀取'), elements.agentStatus.textContent);
assert.ok(!elements.agentStatus.textContent.includes('已設定'));
assert.equal(elements.agentBtn.disabled,false);
''',
}


@pytest.mark.parametrize("case", CASES)
def test_actual_frontend_chat_behavior(case):
    node = shutil.which("node")
    assert node, "Node is required for the authorized frontend checks"
    source = (LEGACY_WEB / "app.js").read_text(encoding="utf-8")
    functions = source[source.index("function backendLabel("):source.index("document.addEventListener('DOMContentLoaded'")]
    harness = r'''
const assert=require('node:assert/strict');
const vm=require('node:vm');
function makeElement(tagName='div') {
  return {tagName,children:[],textContent:'',value:'',hidden:true,disabled:false,open:false,handlers:{},
    appendChild(x){this.children.push(x)},addEventListener(type,fn){this.handlers[type]=fn},
    set innerHTML(x){this.htmlWrites=(this.htmlWrites||0)+1; throw Error('Unexpected HTML injection')}};
}
function flatten(el){return el.textContent + el.children.map(flatten).join(' ')}
const elements={agentBtn:makeElement('button'),agentQuery:makeElement('input'),agentResult:makeElement()};
elements.agentBtn.textContent='問代理人';
elements.agentQuery.value='中義市場高麗菜今天一台斤32元';
const timers=new Map(); let timerId=0;
const calls=[];
const response=(data,ok=true,status=200) => ({ok,status,json:async () => data});
const context={
  document:{getElementById:id => elements[id]||null,createElement:tag => makeElement(tag)},
  API_AGENT_QUERY:'agent/query',API_AGENT_STATUS:'agent/status',AGENT_TIMEOUT_MS:120000,
  STORE_ID_RE:/^[A-Za-z0-9_-]+$/,currentStoreId:()=>'store-test',
  setTimeout(fn,ms){const id=++timerId;timers.set(id,{fn,ms});return id},clearTimeout(id){timers.delete(id)},
  AbortController,console,
  resetSaveBar(){throw Error('quote-only query must not change save state')},
  setSaveStatus(){throw Error('quote-only query must not change save state')},
};
vm.createContext(context);
vm.runInContext(__SOURCE__,context);
(async () => {
__CASE__
})().catch(err => {console.error(err);process.exitCode=1});
'''.replace("__SOURCE__", json.dumps(functions)).replace("__CASE__", CASES[case])
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
