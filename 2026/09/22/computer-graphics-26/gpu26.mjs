const $ = id => document.getElementById(id);
let device, data, latest, baseline, busy = false, lost = false, ready = false;
const log = value => { $('log').textContent += JSON.stringify(value, null, 2) + '\n'; };
const shader = `
struct Uniforms { mvp: mat4x4f, object: vec4f }
@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var tex: texture_2d<f32>;
@group(0) @binding(2) var samp: sampler;
struct Vertex { @builtin(position) position: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@location(0) p: vec3f, @location(1) uv: vec2f) -> Vertex {
  var out: Vertex; out.position = uniforms.mvp * vec4f(p,1); out.uv = uv; return out;
}
fn srgb(c: vec3f) -> vec3f {
  return select(1.055 * pow(c,vec3f(1.0/2.4)) - .055, 12.92*c, c <= vec3f(.0031308));
}
struct Fragment { @location(0) color: vec4f, @location(1) auxiliary: vec4f }
@fragment fn fs(v: Vertex) -> Fragment {
  var out: Fragment;
  out.color = vec4f(srgb(textureSample(tex,samp,v.uv).rgb),1);
  out.auxiliary = vec4f(v.uv,v.position.z,uniforms.object.x); return out;
}`;
let pipelines, groups, vertex, index, color, diagnostic, depth;
async function initializeResources() {
  if (!navigator.gpu) throw Error('navigator.gpu 不可用，需要支持 WebGPU 的安全上下文');
  const response = await fetch(new URLSearchParams(location.search).get('data') || 'build/pipeline26.json');
  if (!response.ok) throw Error(`CPU 数据读取失败 HTTP ${response.status}`);
  data = await response.json();
  if (data.width !== 128 || data.height !== 128 || data.reference.length !== 16384 || data.vertices.length !== 20 || data.indices.length !== 6 || data.mvp.length !== 2 || data.mvp.some(m => m.length !== 16 || m.some(v => !Number.isFinite(v))) || data.texture.length !== 256) throw Error('CPU 数据格式不符合本实验固定场景');
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) throw Error('没有可用 WebGPU adapter');
  device = await adapter.requestDevice(); lost = false;
  const initializedDevice = device;
  device.lost.then(info => { if(device !== initializedDevice)return; lost = true; $('status').textContent = `设备丢失：${info.reason}，重新加载页面后重试`; log({deviceLost: info.reason, message: info.message}); });
  device.addEventListener('uncapturederror', event => log({uncapturedError: event.error.message}));
  log({date: new Date().toISOString(), secureContext: isSecureContext, userAgent: navigator.userAgent, adapter: {vendor:adapter.info.vendor, architecture:adapter.info.architecture, device:adapter.info.device, description:adapter.info.description}, target:'rgba8unorm', diagnostic:'rgba32float', depth:'depth32float'});
  device.pushErrorScope('validation');
  try {
    const module = device.createShaderModule({code:shader});
    const compilation = await module.getCompilationInfo();
    const errors = compilation.messages.filter(m => m.type === 'error');
    if (errors.length) throw Error(errors.map(m => m.message).join('\n'));
    const descriptor = {layout:'auto', vertex:{module, entryPoint:'vs', buffers:[{arrayStride:20, attributes:[{shaderLocation:0,offset:0,format:'float32x3'},{shaderLocation:1,offset:12,format:'float32x2'}]}]}, fragment:{module,entryPoint:'fs',targets:[{format:'rgba8unorm'},{format:'rgba32float'}]}, primitive:{topology:'triangle-list', cullMode:'none'}, depthStencil:{format:'depth32float',depthWriteEnabled:true,depthCompare:'less'}};
    pipelines = [await device.createRenderPipelineAsync(descriptor), await device.createRenderPipelineAsync({...descriptor,depthStencil:{format:'depth32float',depthWriteEnabled:true,depthCompare:'always'}})];
    const buffer = (values,usage) => { const b=device.createBuffer({size:values.byteLength,usage:usage|GPUBufferUsage.COPY_DST});device.queue.writeBuffer(b,0,values);return b; };
    vertex=buffer(new Float32Array(data.vertices),GPUBufferUsage.VERTEX);
    index=buffer(new Uint16Array(data.indices),GPUBufferUsage.INDEX);
    const texture=device.createTexture({size:[8,8],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
    device.queue.writeTexture({texture},new Uint8Array(data.texture),{bytesPerRow:32},[8,8]);
    const sampler=device.createSampler({magFilter:'nearest',minFilter:'nearest',mipmapFilter:'nearest',addressModeU:'clamp-to-edge',addressModeV:'clamp-to-edge'});
    const uniforms=data.mvp.map((matrix,k) => buffer(new Float32Array([...matrix,k+1,0,0,0]),GPUBufferUsage.UNIFORM));
    groups=pipelines.map(pipeline => uniforms.map(b => device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:b}},{binding:1,resource:texture.createView()},{binding:2,resource:sampler}]})));
    const target = format => device.createTexture({size:[128,128],format,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
    color=target('rgba8unorm');diagnostic=target('rgba32float');depth=target('depth32float');
  } finally {
    const error=await device.popErrorScope(); if(error) throw Error(error.message);
  }
  ready = true;
}
async function initialize() {
  try {await initializeResources();}
  catch(error) {const failedDevice=device;device=null;ready=false;lost=false;pipelines=null;groups=null;color=null;diagnostic=null;depth=null;failedDevice?.destroy();throw error;}
}
function show() {
  if(!latest)return;
  const pixels=new Uint8ClampedArray(128*128*4), mode=$('view').value;
  for(let i=0;i<16384;++i) {
    const d=latest.diagnostic.subarray(i*4,i*4+4), r=data.reference[i];
    let rgb=latest.color.subarray(i*4,i*4+3);
    if(mode==='uv')rgb=d[3]?[255*d[0],255*d[1],d[3]===1?80:220]:[0,0,0];
    if(mode==='depth')rgb=d[3]?[255*latest.depth[i],255*latest.depth[i],255*latest.depth[i]]:[0,0,0];
    if(mode==='difference')rgb=d[3]!==r[3]?[255,0,0]:r[4]?[255,180,0]:[0,0,0];
    pixels.set([...rgb,255],i*4);
  }
  $('canvas').getContext('2d').putImageData(new ImageData(pixels,128,128),0,0);
}
async function render(reverse=false,negative=false) {
  device.pushErrorScope('validation');
  const readbacks=[];
  try {
    const encoder=device.createCommandEncoder();
    const pass=encoder.beginRenderPass({colorAttachments:[{view:color.createView(),clearValue:[0,0,0,1],loadOp:'clear',storeOp:'store'},{view:diagnostic.createView(),clearValue:[0,0,1,0],loadOp:'clear',storeOp:'store'}],depthStencilAttachment:{view:depth.createView(),depthClearValue:1,depthLoadOp:'clear',depthStoreOp:'store'}});
    const p=negative?1:0;pass.setPipeline(pipelines[p]);pass.setVertexBuffer(0,vertex);pass.setIndexBuffer(index,'uint16');
    for(const k of reverse?[1,0]:[0,1]) {pass.setBindGroup(0,groups[p][k]);pass.drawIndexed(6);}pass.end();
    for(const [texture,bytes,aspect] of [[color,4,'all'],[diagnostic,16,'all'],[depth,4,'depth-only']]) {
      const buffer=device.createBuffer({size:128*128*bytes,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
      encoder.copyTextureToBuffer({texture,aspect},{buffer,bytesPerRow:128*bytes},[128,128]);readbacks.push(buffer);
    }
    device.queue.submit([encoder.finish()]);
    await Promise.all(readbacks.map(b => b.mapAsync(GPUMapMode.READ)));
    latest={color:new Uint8Array(readbacks[0].getMappedRange().slice(0)),diagnostic:new Float32Array(readbacks[1].getMappedRange().slice(0)),depth:new Float32Array(readbacks[2].getMappedRange().slice(0))};
    if(lost)throw Error('设备已丢失，不能把读回当作成功');
    let interior=0, boundary=0, objectMismatch=0, boundaryObjectMismatch=0, colorMismatch=0, colorSamples=0, maxUV=0,maxDepth=0,maxStoredDepth=0, changed=0, nonfinite=0, backgroundMismatch=0, boundaryMaxUV=0, boundaryMaxDepth=0, boundaryColorMismatch=0;
    const probes=[];
    for(let i=0;i<16384;++i) {
      const r=data.reference[i],d=latest.diagnostic.subarray(i*4,i*4+4);
      if([...d,latest.depth[i]].some(v=>!Number.isFinite(v)))++nonfinite;
      if(baseline&&d[3]!==baseline.diagnostic[i*4+3])++changed;
      if(r[4]) {++boundary;if([0,1,2].some(c=>Math.abs(latest.color[i*4+c]-r[5+c])>1))++boundaryColorMismatch;if(d[3]!==r[3])++boundaryObjectMismatch;else if(r[3]) {boundaryMaxUV=Math.max(boundaryMaxUV,Math.abs(d[0]-r[0]),Math.abs(d[1]-r[1]));boundaryMaxDepth=Math.max(boundaryMaxDepth,Math.abs(latest.depth[i]-r[2]));}continue;}
      if(d[3]!==r[3])++objectMismatch;
      if(!r[3]) {if(latest.depth[i]!==1||[0,1,2].some(c=>latest.color[i*4+c]!==0)||latest.color[i*4+3]!==255)++backgroundMismatch;continue;}
      ++interior;maxUV=Math.max(maxUV,Math.abs(d[0]-r[0]),Math.abs(d[1]-r[1]));maxDepth=Math.max(maxDepth,Math.abs(d[2]-r[2]));maxStoredDepth=Math.max(maxStoredDepth,Math.abs(latest.depth[i]-r[2]));
      const margin=Math.min(...r.slice(0,2).map(u=>Math.abs(u*8-Math.round(u*8))));
      if(margin>.002) {++colorSamples;if([0,1,2].some(c=>Math.abs(latest.color[i*4+c]-r[5+c])>1))++colorMismatch;}
      if(probes.length<3&&i%127===0)probes.push({xy:[i%128,Math.floor(i/128)],cpu:r.slice(0,4),gpu:[...d],storedDepth:latest.depth[i],rgba:[...latest.color.subarray(i*4,i*4+4)]});
    }
    const baselineByteMismatch={color:0,diagnostic:0,depth:0};
    if(baseline)for(const key of Object.keys(baselineByteMismatch)) {const a=new Uint8Array(latest[key].buffer),b=new Uint8Array(baseline[key].buffer);for(let i=0;i<a.length;++i)if(a[i]!==b[i])++baselineByteMismatch[key];}
    const reverseIdentical=!reverse||Object.values(baselineByteMismatch).every(n=>n===0);
    const passCheck=reverseIdentical&&interior>0&&colorSamples>0&&nonfinite===0&&backgroundMismatch===0&&objectMismatch===0&&maxUV<.00015&&maxDepth<.000002&&maxStoredDepth<.000002&&colorMismatch===0;
    if(!baseline&&!negative)baseline=latest;
    show();log({mode:negative?'depth_always_negative':reverse?'reverse_order':'normal',pass:passCheck,interior,boundary,objectMismatch,boundaryObjectMismatch,boundaryMaxUV,boundaryMaxDepth,boundaryColorMismatch,backgroundMismatch,colorSamples,textureBoundaryExcluded:interior-colorSamples,baselineByteMismatch,reverseIdentical,colorMismatch,maxUV,maxDepth,maxStoredDepth,nonfinite,objectsChangedFromFirstRun:changed,probes});
    $('status').textContent=negative?(changed>0&&!passCheck?'负对照成功：关闭深度造成遮挡错误，CPU 检查拒绝结果。':'负对照未检出预期错误，请检查记录。'):(passCheck?'PASS：内部 UV、真实深度附件、对象编号与纹理颜色通过；边界单独记录。':'FAIL：CPU/GPU 内部检查不通过，见记录。');
  } finally {
    for(const buffer of readbacks) {if(buffer.mapState==='mapped')buffer.unmap();buffer.destroy();}
    const error=await device.popErrorScope();if(error)throw Error(error.message);
  }
}
async function action(fn) {
  if(busy)return;busy=true;for(const id of ['run','reverse','negative'])$(id).disabled=true;
  try {await fn();}catch(error) {$('status').textContent=`失败：${error.message}`;log({error:error.message});}
  finally {busy=false;$('run').disabled=lost;for(const id of ['reverse','negative'])$(id).disabled=!latest||lost;}
}
$('run').onclick=()=>action(async()=>{if(!ready)await initialize();await render();});
$('reverse').onclick=()=>action(()=>render(true));
$('negative').onclick=()=>action(()=>render(false,true));
$('view').onchange=show;
