const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.join(__dirname, "..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const context = vm.createContext({ navigator: { language: "pt-BR" } });
vm.runInContext(read("ui/i18n.js"), context);
assert.equal(vm.runInContext('pickLang(null)', context), "pt-BR");
assert.equal(vm.runInContext('pickLang("en-US")', context), "en-US");
const keys = lang => JSON.parse(vm.runInContext(`JSON.stringify(Object.keys(I18N["${lang}"]).sort())`, context));
assert.deepEqual(keys("pt-BR"), keys("en-US"));
for (const key of keys("en-US")) {
  const placeholders = lang => JSON.parse(vm.runInContext(`JSON.stringify((I18N["${lang}"]["${key}"].match(/\{\w+\}/g) || []).sort())`, context));
  assert.deepEqual(placeholders("pt-BR"), placeholders("en-US"), key);
}
for (const name of ["ui/index.html", "ui/flyout.html"]) {
  const html = read(name);
  assert(html.includes('<script src="api.js"></script>'));
  for (const [, js] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(js, {filename: name});
  for (const [, key] of html.matchAll(/data-i18n(?:-title|-aria)?="([^"]+)"/g)) assert(keys("en-US").includes(key), `${name}: ${key}`);
  assert(!/s\.status\s*[!=]==\s*"(?:ativo|aguardando|erro)"/.test(html));
  for (const status of ["running", "waiting", "error"]) assert(html.includes(`s.status === "${status}"`));
}
(async () => {
  let request;
  const apiContext = vm.createContext({ fetch: async (...args) => {request = args; return {ok: true};} });
  vm.runInContext(read("ui/api.js"), apiContext);
  await vm.runInContext('localFetch("/api/quit", {method: "POST"})', apiContext);
  assert.equal(request[1].headers["X-DeepNoise-Request"], "1");
  assert.equal(request[1].headers["Content-Type"], "application/json");
  apiContext.fetch = async () => ({ok: false, status: 500});
  await assert.rejects(vm.runInContext('localFetch("/api/diag", {method: "POST"})', apiContext), /500/);
  console.log("UI syntax, status contract, translation parity, and request helper checks passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
