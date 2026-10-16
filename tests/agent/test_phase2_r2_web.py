"""Execute production rendering functions in Node with a controlled DOM."""
from pathlib import Path
import subprocess
import shutil


def test_provider_labels_execution_failures_and_text_only_rendering():
    node = shutil.which("node")
    assert node, "Node is required for the authorized frontend checks"
    # Original chat semantics remain tested against exact pre-migration snapshot;
    # tests/integrations/test_manual_web_ui.py asserts current production has no chat.
    source = Path("tests/fixtures/legacy_chat_web_20261013/app.js").read_text(encoding="utf-8")
    functions = source[source.index("function backendLabel("):source.index("function bindAgent(")]
    harness = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const el = () => ({children:[],textContent:'',appendChild(x){this.children.push(x)},set innerHTML(x){throw Error('HTML injection')}});
const context = {document:{createElement:el}};
vm.createContext(context);
vm.runInContext(SOURCE, context);
for (const [provider, runtime, wanted] of [['glm_zai','openai_compat','GLM'],['qwen_local','openai_compat','Qwen'],['glm_bigmodel','hermes 0.19.0','Hermes']]) {
  const label = context.backendLabel({provider,runtime,backend_used:'rule',degraded:true,degraded_reason:'tool failure'}).text;
  assert.ok(label.includes(wanted), label);
  if (provider.startsWith('glm')) assert.ok(!label.includes('Qwen'), label);
  assert.ok(label.includes('規則'), label);
}
assert.ok(!context.backendLabel({backend_used:'rule',degraded:true}).text.includes('Qwen'));
const attack = '<img src=x onerror=alert(1)>';
const out = el();
context.renderAgentResult(out, {provider:'glm_zai',backend_used:'rule',degraded:true,degraded_reason:attack,
 answer:attack,tool_trace:[{tool:'get_market_quote',ok:false,validation:'accepted',error:attack}]});
const texts = JSON.stringify(out);
assert.ok(texts.includes(attack));
assert.ok(texts.includes('執行失敗'), texts);
assert.ok(!texts.includes('Qwen 失敗'), texts);
console.log('frontend runtime assertions passed');
'''
    harness = harness.replace("SOURCE", repr(functions))
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_qwen_source_is_preserved_when_rule_profile_selects_old_backend():
    node = shutil.which("node")
    assert node, "Node is required for the authorized frontend checks"
    source = Path("tests/fixtures/legacy_chat_web_20261013/app.js").read_text(encoding="utf-8")
    functions = source[source.index("function backendLabel("):source.index("function bindAgent(")]
    harness = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const context = {};
vm.createContext(context);
vm.runInContext(SOURCE, context);
const success = context.backendLabel({provider:'rule',runtime:'rule',backend:'qwen',backend_used:'qwen',degraded:false});
assert.equal(success.text, 'Qwen 代理人');
assert.equal(success.degraded, false);
const fallback = context.backendLabel({provider:'rule',runtime:'rule',backend:'qwen',backend_used:'rule',degraded:true,degraded_reason:'qwen_request_failed:OSError'});
assert.ok(fallback.text.startsWith('Qwen 降級→規則模式'), fallback.text);
assert.ok(fallback.text.includes('qwen_request_failed:OSError'), fallback.text);
assert.equal(fallback.degraded, true);
const rule = context.backendLabel({provider:'rule',runtime:'rule',backend:'rule',backend_used:'rule',degraded:false});
assert.equal(rule.text, '代理人（規則模式）');
assert.ok(!context.backendLabel({provider:'rule',backend:'rule',backend_used:'rule',degraded:true}).text.includes('Qwen'));
for (const [provider, wanted] of [['glm_zai','GLM'],['qwen_local','Qwen']]) {
  const label = context.backendLabel({provider,runtime:'openai_compat',backend:'qwen',backend_used:'rule',degraded:true}).text;
  assert.ok(label.startsWith(wanted + ' 降級→規則模式'), label);
}
const hermes = context.backendLabel({provider:'glm_bigmodel',runtime:'hermes 0.19.0',backend:'qwen',backend_used:'rule',degraded:true}).text;
assert.ok(hermes.startsWith('GLM（Hermes） 降級→規則模式'), hermes);
console.log('legacy Qwen runtime assertions passed');
'''
    harness = harness.replace("SOURCE", repr(functions))
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
