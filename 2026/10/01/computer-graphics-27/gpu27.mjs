import {WIDTH, STRIDE, COUNTS, makeInstances, summarize} from './instances27.mjs';
const $ = id => document.getElementById(id);
const modes = ['individual', 'instanced'];
let device, pipeline, vertex, instance, target, context, format, query, resolve, readback, environment, lost = false, busy = false;
let hiddenDuringAction = false;
document.addEventListener('visibilitychange', () => {
  if (busy && document.hidden) hiddenDuringAction = true;
});
const shader = `
struct Output { @builtin(position) position: vec4f, @location(0) color: vec3f }
@vertex fn vs(@location(0) p: vec2f, @location(1) transform: vec4f, @location(2) color: vec4f) -> Output {
  var out: Output;
  out.position = vec4f(p * transform.zw + transform.xy, .5, 1);
  out.color = color.rgb; return out;
}
@fragment fn fs(v: Output) -> @location(0) vec4f {
  let c = v.color;
  let encoded = select(1.055 * pow(c, vec3f(1.0/2.4)) - .055, 12.92*c, c <= vec3f(.0031308));
  return vec4f(encoded,1);
}`;
const frame = () => new Promise(resolveFrame => requestAnimationFrame(resolveFrame));
function ensureLive() { if (lost || document.hidden || hiddenDuringAction) throw Error('设备丢失或页面曾隐藏；本次测量作废，请重新加载并保持页面可见'); }
async function initialize() {
  if (device) {ensureLive(); return environment;}
  if (!navigator.gpu) throw Error('navigator.gpu 不可用');
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) throw Error('没有可用 adapter');
  const timestamp = adapter.features.has('timestamp-query');
  const created = await adapter.requestDevice({requiredFeatures: timestamp ? ['timestamp-query'] : []});
  device = created;
  device.lost.then(info => {lost = true; $('status').textContent = `设备丢失：${info.reason}，重新加载恢复`;});
  device.addEventListener('uncapturederror', event => {lost = true; $('status').textContent = event.error.message;});
  format = navigator.gpu.getPreferredCanvasFormat();
  context = $('canvas').getContext('webgpu');
  context.configure({device, format, alphaMode:'opaque'});
  const module = device.createShaderModule({code:shader});
  const errors = (await module.getCompilationInfo()).messages.filter(m => m.type === 'error');
  if (errors.length) throw Error(errors.map(m => m.message).join('\n'));
  pipeline = await device.createRenderPipelineAsync({layout:'auto', vertex:{module,entryPoint:'vs',buffers:[
    {arrayStride:8,attributes:[{shaderLocation:0,offset:0,format:'float32x2'}]},
    {arrayStride:STRIDE,stepMode:'instance',attributes:[{shaderLocation:1,offset:0,format:'float32x4'},{shaderLocation:2,offset:16,format:'float32x4'}]}]},
    fragment:{module,entryPoint:'fs',targets:[{format}]},primitive:{topology:'triangle-list'}});
  const positions = new Float32Array([-1,-1,1,-1,1,1,-1,-1,1,1,-1,1]);
  vertex = device.createBuffer({size:positions.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
  device.queue.writeBuffer(vertex,0,positions);
  instance = device.createBuffer({size:4096*STRIDE,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
  target = device.createTexture({size:[WIDTH,WIDTH],format,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
  if (timestamp) {
    query = device.createQuerySet({type:'timestamp',count:2});
    resolve = device.createBuffer({size:16,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC});
    readback = device.createBuffer({size:16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
  }
  environment = {secureContext:isSecureContext,userAgent:navigator.userAgent,
    adapter:{vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description},
    timestampQuery:timestamp,format,width:WIDTH,height:WIDTH,instanceStride:STRIDE};
  return environment;
}
function encode(mode,count,view,{timed=false,negative=false}={}) {
  const encoder = device.createCommandEncoder();
  const descriptor = {colorAttachments:[{view,clearValue:[0,0,0,1],loadOp:'clear',storeOp:'store'}]};
  if (timed && query) descriptor.timestampWrites = {querySet:query,beginningOfPassWriteIndex:0,endOfPassWriteIndex:1};
  const pass = encoder.beginRenderPass(descriptor);
  pass.setPipeline(pipeline); pass.setVertexBuffer(0,vertex); pass.setVertexBuffer(1,instance);
  if (mode === 'individual') for(let i=0;i<count;++i) pass.draw(6,1,0,negative?0:i);
  else pass.draw(6,count);
  pass.end();
  if (timed && query) {encoder.resolveQuerySet(query,0,2,resolve,0);encoder.copyBufferToBuffer(resolve,0,readback,0,16);}
  return encoder;
}
async function pixels(mode,count,negative=false) {
  const encoder = encode(mode,count,target.createView(),{negative});
  const buffer = device.createBuffer({size:WIDTH*WIDTH*4,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
  try {
    encoder.copyTextureToBuffer({texture:target},{buffer,bytesPerRow:WIDTH*4},[WIDTH,WIDTH]);
    device.queue.submit([encoder.finish()]);await buffer.mapAsync(GPUMapMode.READ);ensureLive();
    return new Uint8Array(buffer.getMappedRange().slice(0));
  } finally {if(buffer.mapState==='mapped')buffer.unmap();buffer.destroy();}
}
function checkCenters(bytes,count) {
  const values = makeInstances(count), side = Math.sqrt(count), srgb = c => c<=.0031308?12.92*c:1.055*c**(1/2.4)-.055;
  let errors = 0;
  for(let i=0;i<count;++i) {
    const x = Math.floor((i%side+.5)*WIDTH/side), y = Math.floor((Math.floor(i/side)+.5)*WIDTH/side);
    const offset = (y*WIDTH+x)*4, rgb = [0,1,2].map(c => Math.round(srgb(values[i*8+4+c])*255));
    if(format.startsWith('bgra'))rgb.reverse();
    if(rgb.some((c,k)=>Math.abs(c-bytes[offset+k])>1)||bytes[offset+3]!==255)++errors;
  }
  return errors;
}
async function sample(mode,count) {
  ensureLive();
  const start = performance.now();
  const encoder = encode(mode,count,target.createView(),{timed:true});
  device.queue.submit([encoder.finish()]);
  const cpuSubmitMs = performance.now()-start, completionStart = performance.now();
  await device.queue.onSubmittedWorkDone();
  const completionWaitMs = performance.now()-completionStart;
  let gpuPassMs = null;
  if (query) {
    await readback.mapAsync(GPUMapMode.READ);
    try {const stamps = new BigUint64Array(readback.getMappedRange());if(stamps[1]<stamps[0])throw Error('timestamp decreased');gpuPassMs=Number(stamps[1]-stamps[0])/1e6;}
    finally {readback.unmap();}
  }
  ensureLive();return {cpuSubmitMs,completionWaitMs,gpuPassMs};
}
async function uploadSamples(count) {
  const data = makeInstances(count), samples = {single:[],multiple:[]};
  for(let round=0;round<5;++round) for(const mode of round%2?['multiple','single']:['single','multiple']) {
    await device.queue.onSubmittedWorkDone();
    const start = performance.now();
    if(mode==='single')device.queue.writeBuffer(instance,0,data);
    else for(let i=0;i<count;++i)device.queue.writeBuffer(instance,i*STRIDE,data,i*8,8);
    samples[mode].push(performance.now()-start);
    await device.queue.onSubmittedWorkDone();
  }
  return {bytes:data.byteLength,writeCalls:{single:1,multiple:count},cpuWriteCallMs:samples,
    summary:Object.fromEntries(Object.entries(samples).map(([key,v])=>[key,summarize(v)]))};
}
async function frameIntervals(mode,count) {
  // Presentation is not proved by rAF. These are callback intervals only.
  const intervals=[];let previous;
  for(let i=0;i<70;++i) {
    const now=await frame();ensureLive();
    if(i>=10)intervals.push(now-previous);previous=now;
    device.queue.submit([encode(mode,count,context.getCurrentTexture().createView()).finish()]);
  }
  await device.queue.onSubmittedWorkDone();return {intervalsMs:intervals,summary:summarize(intervals)};
}
function displaySummary(report) {
  $('summary').replaceChildren();
  const table=document.createElement('table'), head=table.insertRow();
  for(const label of ['物体数','提交方式','CPU编码提交中位ms','GPU pass中位ms'])head.insertCell().textContent=label;
  for(const item of report.scenes)for(const mode of modes) {
    const row=table.insertRow(), s=item.summary[mode];
    for(const value of [item.count,mode,s.cpuSubmitMs.median.toFixed(4),s.gpuPassMs?.median.toFixed(4)??'不支持'])row.insertCell().textContent=value;
  }
}
async function run() {
  const info = await initialize();
  const report = {environment:{...info,date:new Date().toISOString()},protocol:{counts:COUNTS,rounds:5,samplesPerRound:12,warmupPerMode:8,
    deterministic:true,msUnit:'milliseconds',geometry:'six vertices per quad',sampling:'one sample per pixel',
    cpuSubmit:'encoder creation through queue.submit return; excludes upload and readback',
    gpuPass:'render pass timestamp difference; excludes copies/upload/presentation',
    completionWait:'queue completion Promise wall time, not GPU execution time',
    frameInterval:'rAF callbacks on onscreen rendering, 10 warmups + 60 intervals, no readback'},scenes:[]};
  for(const count of COUNTS) {
    $('status').textContent=`正在检查与测量 ${count} 个物体`;
    device.queue.writeBuffer(instance,0,makeInstances(count));
    const a=await pixels('individual',count),b=await pixels('instanced',count);
    let mismatchedBytes=0;for(let i=0;i<a.length;++i)if(a[i]!==b[i])++mismatchedBytes;
    const centerErrors=checkCenters(a,count)+checkCenters(b,count);
    if(mismatchedBytes||centerErrors)throw Error(`像素检查失败：bytes=${mismatchedBytes}, centers=${centerErrors}`);
    const samples={individual:[],instanced:[]};
    for(const mode of modes)for(let i=0;i<8;++i)await sample(mode,count);
    const rounds=[];
    for(let round=0;round<5;++round) {
      const current={individual:[],instanced:[]};
      for(let j=0;j<12;++j)for(const mode of (round+j)%2?[...modes].reverse():modes) {
        const value=await sample(mode,count);samples[mode].push(value);current[mode].push(value);
      }
      rounds.push(Object.fromEntries(modes.map(mode=>[mode,summarize(current[mode].map(s=>s.cpuSubmitMs))])));
    }
    const summary=Object.fromEntries(modes.map(mode=>[mode,Object.fromEntries(['cpuSubmitMs','completionWaitMs','gpuPassMs'].map(key=>[key,key==='gpuPassMs'&&!query?null:summarize(samples[mode].map(s=>s[key]))]))]));
    report.scenes.push({count,drawCalls:{individual:count,instanced:1},vertexInvocations:count*6,mismatchedBytes,centerErrors,rounds,samples,summary,upload:await uploadSamples(count)});
  }
  device.queue.writeBuffer(instance,0,makeInstances(4096));
  report.frames={};for(const mode of modes)report.frames[mode]=await frameIntervals(mode,4096);
  ensureLive();displaySummary(report);$('log').textContent=JSON.stringify(report,null,2);
  $('status').textContent='PASS：三组像素与中心色通过，CPU/GPU/帧间隔分开记录。';
}
async function action(fn) {
  if(busy)return;hiddenDuringAction=false;busy=true;for(const id of ['run','negative','preview','count'])$(id).disabled=true;
  try {await fn();}catch(error){$('status').textContent=`FAIL：${error.message}`;}
  finally {busy=false;for(const id of ['run','negative','preview','count'])$(id).disabled=false;}
}
$('run').onclick=()=>action(run);
$('preview').onclick=()=>action(async()=>{await initialize();const count=Number($('count').value);device.queue.writeBuffer(instance,0,makeInstances(count));device.queue.submit([encode('instanced',count,context.getCurrentTexture().createView()).finish()]);await device.queue.onSubmittedWorkDone();ensureLive();$('status').textContent=`已显示 ${count} 个实例`;});
$('negative').onclick=()=>action(async()=>{await initialize();const count=64;device.queue.writeBuffer(instance,0,makeInstances(count));const bytes=await pixels('individual',count,true),errors=checkCenters(bytes,count);$('status').textContent=errors===63?'负对照成功：错误 firstInstance 造成 63 个中心缺失':'FAIL：负对照未检出预期错误';$('log').textContent=JSON.stringify({negative:'firstInstance=0',count,centerErrors:errors,expected:63},null,2);});
