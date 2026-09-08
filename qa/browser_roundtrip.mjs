/** Real Chromium + isolated participant app, synthetic accounts only.
 * Usage: node qa/browser_roundtrip.mjs APP_CHECKOUT CAMP_ZIP NEW_OUTPUT_DIR
 * Input ZIP must contain synthetic QA data; no production server or account.
 */
import assert from 'node:assert/strict';
import {createHash, randomBytes, randomUUID} from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn, execFileSync} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync, existsSync, openSync, closeSync} from 'node:fs';
import {resolve, dirname, join, basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import net from 'node:net';

const [appArg, bundleArg, outputArg] = process.argv.slice(2);
assert(appArg && bundleArg && outputArg, 'APP_CHECKOUT CAMP_ZIP NEW_OUTPUT_DIR required');
const app = resolve(appArg), bundle = resolve(bundleArg), output = resolve(outputArg);
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const appSHA = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: app, encoding:'utf8'}).trim();
assert.equal(appSHA, '439d2ba491cef5f2a4c01947a03a1577491672d9');
const gitPaths = args => execFileSync('git', args, {cwd:app, encoding:'utf8'}).split('\0').filter(Boolean);
const generatedAllowlist = new Set(['next-env.d.ts']);
const changedTracked = gitPaths(['diff','HEAD','--name-only','-z']);
assert.deepEqual(changedTracked.filter(path=>!generatedAllowlist.has(path)), [], 'Tracked app source differs from pinned commit');
const untracked = gitPaths(['ls-files','--others','--exclude-standard','-z']);
const ignoredInputs = gitPaths(['ls-files','--others','--ignored','--exclude-standard','-z','--',
 'src','app','pages','scripts',':(top,glob).env*',':(top,glob)*.config.*',':(top,glob)package*.json']);
const executableSource = path => /^(src|app|pages|scripts)\//.test(path) ||
 /\.(?:[cm]?[jt]sx?|json|wasm|node)$/.test(path) || /(^|\/)\.env(?:\.|$)/.test(path);
assert.deepEqual([...new Set([...untracked,...ignoredInputs])].filter(executableSource), [], 'Untracked app source/config must not affect pinned execution');
const generatedFiles = [...generatedAllowlist].filter(path=>existsSync(join(app,path))).map(path=>({
 path, sha256:createHash('sha256').update(readFileSync(join(app,path))).digest('hex')}));
assert(!existsSync(output), 'Output directory must be new');
mkdirSync(output, {recursive:true, mode:0o700});
const inspect = path => JSON.parse(execFileSync('python3', [join(repo,'plugin/scripts/camp_submit.py'), 'inspect', path], {encoding:'utf8'}));
const source = inspect(bundle), bytes = readFileSync(bundle);
assert.equal(source.manifest.week, 1, 'This roundtrip checks a week-1 bundle');
const require = createRequire(join(app, 'package.json'));
const {chromium} = require('playwright');
const {expect} = require('@playwright/test');
const listener = net.createServer();
await new Promise(r=>listener.listen(0,'127.0.0.1',r));
const port = listener.address().port;
await new Promise(r=>listener.close(r));
const origin = `http://127.0.0.1:${port}`;
const password = 'Synthetic-' + randomBytes(24).toString('hex') + 'Aa!';
const key = randomBytes(32).toString('hex');
const env = Object.fromEntries(Object.entries(process.env).filter(([k])=> !k.startsWith('SPARKER_') && !k.startsWith('NEXT_PUBLIC_') && !k.startsWith('GITHUB_') && k !== 'NODE_OPTIONS'));
Object.assign(env, {SPARKER_MODE:'live',SPARKER_DEMO:'0',SPARKER_ALLOW_LOOPBACK_HTTP:'1',SPARKER_ORIGIN:origin,
 SPARKER_DB:join(output,'synthetic.sqlite'),SPARKER_ADMIN_USERNAME:'test-admin',SPARKER_ADMIN_LABEL:'TEST ONLY Admin',
 SPARKER_ADMIN_PASSWORD:password,SPARKER_CONSOLE_KEY:key,SPARKER_MANAGEMENT_MODE:'legacy',NEXT_TELEMETRY_DISABLED:'1'});
const log = openSync(join(output,'server.log'),'wx',0o600);
const server = spawn('node',['node_modules/next/dist/bin/next','dev','--hostname','127.0.0.1','--port',String(port)],
 {cwd:app,env,stdio:['ignore',log,log],detached:true});
let browser;
const checks = [], errors = [];
const result = {status:'RUNNING',evidence_kind:'real_chromium_isolated_participant_app',participant_app_sha:appSHA,
 source_guard:{tracked_source_matches_head:true,generated_allowlist:[...generatedAllowlist],generated_files:generatedFiles},
 source_zip:bundle,source_sha256:source.sha256,manifest:source.manifest,checks};
const save = () => writeFileSync(join(output,'result.json'),JSON.stringify(result,null,2)+'\n',{mode:0o600});
try {
 const deadline = Date.now()+120000;
 while(true){
  assert(server.exitCode===null,'Next server exited');
  try{if((await fetch(origin+'/api/health')).ok)break;}catch{}
  assert(Date.now()<deadline,'Next readiness timeout');await new Promise(r=>setTimeout(r,250));
 }
 browser = await chromium.launch({headless:true, ...(process.env.QA_CHROMIUM_EXECUTABLE ? {executablePath:process.env.QA_CHROMIUM_EXECUTABLE} : {})});
 result.browser_version = browser.version();
 const context = await browser.newContext({baseURL:origin,acceptDownloads:true});
 // Browser HTTP(S) traffic is restricted to this fresh loopback server.
 await context.route('**/*',route=>new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
 const page = await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.getByRole('heading',{level:1,name:'LEADERBOARD',exact:true})).toBeVisible();
 const provision = await context.request.post('/api/admin/participants',{headers:{Origin:origin,Authorization:'Bearer '+key,'X-Console-Actor':'test-admin','X-Request-ID':randomUUID()},data:{id:'TEST-browser-roundtrip',label:'TEST ONLY Browser',username:'browser-roundtrip',participantId:'P03',mappingVerified:true}});
 assert.equal(provision.status(),201);const {code}=await provision.json();
 await page.getByText('초대 코드로 계정 활성화',{exact:true}).click();
 await page.getByLabel('초대받은 아이디').fill('browser-roundtrip');
 await page.getByLabel('초대 코드',{exact:true}).fill(code);
 await page.getByLabel('새 비밀번호',{exact:true}).fill(password);
 await page.getByRole('button',{name:'초대 수락 · 비밀번호 설정'}).click();
 await expect(page.getByTestId('row-TEST-browser-roundtrip')).toBeVisible();
 checks.push('synthetic participant activated through Chromium UI');
 const dashboard=async()=>{const r=await page.request.get('/api/dashboard');assert.equal(r.status(),200);return r.json();};
 const baseline=await dashboard();
 const upload=async(file,week=1)=>{
  await page.getByLabel('주차',{exact:true}).selectOption(String(week));
  await page.getByLabel(/과제 파일/).setInputFiles(file);
  const response=page.waitForResponse(r=>r.url()===origin+'/api/submissions'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'제출하기',exact:true}).click();
  return response;
 };
 const first=await upload(bundle);assert.equal(first.status(),201);const firstID=(await first.json()).id;
 await expect(page.getByTestId('week-1')).toContainText(basename(bundle));
 await page.reload();await expect(page.getByTestId('week-1')).toContainText(basename(bundle));
 checks.push('actual Camp ZIP uploaded via file input and persists after reload');
 const downloadPromise=page.waitForEvent('download');
 await page.getByTestId('week-1').getByRole('link').click();
 const download=await downloadPromise;const downloaded=join(output,'downloaded.zip');await download.saveAs(downloaded);
 assert.equal(createHash('sha256').update(readFileSync(downloaded)).digest('hex'),source.sha256);
 assert.deepEqual(inspect(downloaded).manifest,source.manifest);
 checks.push('Chromium download SHA-256 and full Camp manifest match input');
 const operatorDownload=await context.request.get('/api/admin/files/'+firstID,{headers:{Authorization:'Bearer '+key,'X-Console-Actor':'test-admin','X-Request-ID':randomUUID()}});
 assert.equal(operatorDownload.status(),200);
 assert.equal(createHash('sha256').update(await operatorDownload.body()).digest('hex'),source.sha256);
 checks.push('authenticated operator API download matches the participant upload SHA-256');
 const second=await upload(bundle);assert.equal(second.status(),201);const secondID=(await second.json()).id;assert.notEqual(firstID,secondID);
 await page.getByText('이전 제출 기록 (보관 중)',{exact:true}).click();
 await expect(page.locator('details').getByRole('link',{name:basename(bundle)+' ↓'})).toBeVisible();
 let state=await dashboard();assert.equal(state.submissions.length,2);assert.equal(state.submissions.filter(s=>s.active).length,1);
 checks.push('re-upload retains prior submission and creates a new active history entry');
 const oversized={name:'synthetic-oversize.zip',mimeType:'application/zip',buffer:Buffer.alloc(5*1024*1024+1,120)};
 const rejected=await upload(oversized);assert([400,413].includes(rejected.status()));
 assert.equal((await dashboard()).submissions.length,2);
 await expect(page.getByText(/파일 크기는 최대 5 MiB|요청 크기 제한 초과/)).toBeVisible();
 checks.push('UI upload over 5 MiB rejected without creating a submission');
 const wrongWeek=await upload(bundle,2);assert.equal(wrongWeek.status(),201);
 await expect(page.getByTestId('week-2')).toContainText(basename(bundle));
 state=await dashboard();assert.equal(state.submissions.filter(s=>s.week===2).length,1);
 result.wrong_week_behavior='App accepts week-1 ZIP under UI-selected week 2; ZIP manifest does not select or validate app week.';
 checks.push('wrong-week behavior observed: explicit UI week wins over ZIP manifest');
 assert.deepEqual(state.entries.map(e=>e.tokens),baseline.entries.map(e=>e.tokens));
 checks.push('assignment submission does not fabricate usage tokens');
 await page.screenshot({path:join(output,'submission-history.png'),fullPage:true});
 assert.deepEqual(errors,[]);result.status='PASS';result.submission_ids=[firstID,secondID];save();
 console.log(JSON.stringify({status:result.status,artifact:join(output,'result.json'),source_sha256:source.sha256}));
} catch(error){result.status='FAIL';result.error=String(error);save();throw error;}
finally {
 if(browser)await browser.close();
 try{process.kill(-server.pid,'SIGTERM');}catch{}
 await Promise.race([new Promise(r=>server.once('exit',r)),new Promise(r=>setTimeout(r,5000))]);
 if(server.exitCode===null){try{process.kill(-server.pid,'SIGKILL');}catch{}}
 closeSync(log);
}
