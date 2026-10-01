export const P=8, C=3, W=64, PAGE_BYTES=4*W*W, NONE=0xffffffff;
export const trajectories=[{name:'locality',requests:Array.from({length:16},(_,i)=>Math.floor(i/4))},{name:'thrash',requests:Array.from({length:16},(_,i)=>i%4)}];
function integer(value,min,max,name){if(!Number.isInteger(value)||value<min||value>max)throw Error(`invalid ${name}`);}
export function pageBytes(id){
 integer(id,0,P-1,'page');const a=new Uint8Array(PAGE_BYTES);
 for(let y=0;y<W;y++)for(let x=0;x<W;x++){const i=4*(y*W+x);a[i]=(29*id+3*x+y)%256;a[i+1]=(47*id+x+5*y)%256;a[i+2]=(7*(x^y)+13*id)%256;a[i+3]=255;}return a;
}
export class PageCache {
 constructor(capacity){integer(capacity,1,P,'capacity');this.capacity=capacity;this.slots=Array(capacity);this.age=Array(capacity);this.table=new Uint32Array(P);this.reset();}
 reset(){this.slots.fill(-1);this.age.fill(0);this.table.fill(NONE);this.clock=0;}
 select(request){
  if(!Array.isArray(request)||request.length<1||request.length>P)throw Error('invalid request');
  for(const id of request)integer(id,0,P-1,'page');
  const needed=[...new Set(request)].sort((a,b)=>a-b);if(needed.length>this.capacity)throw Error('frame demand exceeds capacity');
  const changes=[];let hits=0;
  for(const id of needed){let layer=this.slots.indexOf(id);
   if(layer>=0)hits++;
   else {layer=-1;for(let i=0;i<this.capacity;i++)if(!needed.includes(this.slots[i])&&(layer<0||this.age[i]<this.age[layer]))layer=i;
    if(layer<0)throw Error('no unpinned layer');const evicted=this.slots[layer];if(evicted>=0)this.table[evicted]=NONE;
    changes.push({page:id,layer,evicted:evicted<0?null:evicted});this.slots[layer]=id;this.table[id]=layer;}
   this.age[layer]=++this.clock;
  }
  return {hits,misses:changes.length,evictions:changes.filter(c=>c.evicted!==null).length,changes,table:this.table};
 }
}
export function compareRGBA(actual,reference){
 if(!(actual instanceof Uint8Array)||!(reference instanceof Uint8Array)||actual.length!==PAGE_BYTES||reference.length!==PAGE_BYTES)throw Error('invalid RGBA attachment');
 let differentBytes=0,differentPixels=0,maximum=0;
 for(let i=0;i<PAGE_BYTES;i+=4){let pixel=false;for(let k=0;k<4;k++){const d=Math.abs(actual[i+k]-reference[i+k]);if(d){differentBytes++;pixel=true;maximum=Math.max(maximum,d);}}if(pixel)differentPixels++;}
 return {differentBytes,differentPixels,maximum,equal:differentBytes===0};
}
export function requireEqual(actual,reference){const result=compareRGBA(actual,reference);if(!result.equal)throw Error(`RGBA mismatch: ${result.differentPixels} pixels`);return result;}
export function checkData(data){
 if(!data||data.schema!=='streamE08/v1'||data.pages!==P||data.side!==W||data.capacity!==C||!Array.isArray(data.page_rgba)||data.page_rgba.length!==P)throw Error('invalid reference schema');
 for(let id=0;id<P;id++){const a=data.page_rgba[id];if(!Array.isArray(a)||a.length!==PAGE_BYTES||Array.from(a).some(v=>!Number.isInteger(v)||v<0||v>255))throw Error('invalid reference bytes');requireEqual(new Uint8Array(a),pageBytes(id));}
 if(JSON.stringify(data.trajectories)!==JSON.stringify(trajectories))throw Error('invalid reference trajectory');
 if(data.logical_texture_bytes?.resident!==P*PAGE_BYTES||data.logical_texture_bytes?.stream!==C*PAGE_BYTES||data.page_table_bytes!==P*4||data.frame_control_bytes!==16)throw Error('invalid logical bytes');
 return data.page_rgba.map(a=>new Uint8Array(a));
}
export function quantiles(values){
 if(!Array.isArray(values)||values.length===0||Array.from(values).some(v=>!Number.isFinite(v)||v<0))throw Error('invalid timing samples');
 const a=[...values].sort((x,y)=>x-y),q=p=>a[Math.floor(p*(a.length-1))];return {n:a.length,p10:q(.1),median:q(.5),p90:q(.9)};
}
function checksum(bytes){let h=2166136261;for(const b of bytes)h=Math.imul(h^b,16777619)>>>0;return h.toString(16).padStart(8,'0');}
function base64(bytes){let text='';for(const b of bytes)text+=String.fromCharCode(b);return btoa(text);}
const shader=`@group(0) @binding(0) var pages:texture_2d_array<f32>;
@group(0) @binding(1) var<storage,read> mapping:array<u32>;
@group(0) @binding(2) var<uniform> frame:vec4u;
@vertex fn vs(@builtin(vertex_index) i:u32)->@builtin(position) vec4f {
 let p=array<vec2f,3>(vec2f(-1.,-1.),vec2f(3.,-1.),vec2f(-1.,3.));return vec4f(p[i],0.,1.);
}
@fragment fn fs(@builtin(position) p:vec4f)->@location(0) vec4f {
 return textureLoad(pages,vec2i(p.xy),i32(mapping[frame.x]),0);
}`;
async function digest(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');}
function display(bytes){const ctx=document.getElementById('canvas').getContext('2d');const im=ctx.createImageData(W,W);im.data.set(bytes);ctx.putImageData(im,0,0);}
export async function readPixels(device,texture,buffer){
 const encoder=device.createCommandEncoder();encoder.copyTextureToBuffer({texture},{buffer,bytesPerRow:W*4,rowsPerImage:W},[W,W]);device.queue.submit([encoder.finish()]);
 await buffer.mapAsync(GPUMapMode.READ);
 try{return new Uint8Array(buffer.getMappedRange().slice(0));}finally{buffer.unmap();}
}
async function runExperiment(progress){
 if(!navigator.gpu)throw Error('WebGPU unavailable');if(document.hidden)throw Error('page hidden');
 let device,lost=false,hidden=false,uncaptured=null;const resources=[];
 const visibility=()=>{if(document.hidden)hidden=true;};document.addEventListener('visibilitychange',visibility);
 const valid=()=>{if(lost||hidden||uncaptured)throw Error(uncaptured||'device lost or page hidden; discard run');};
 const keep=x=>{resources.push(x);return x;};
 try {
  const sourceURL=new URLSearchParams(location.search).get('data')||'build/streamE08.json';
  const response=await fetch(sourceURL);if(!response.ok)throw Error('reference fetch failed');const referenceText=await response.text();const references=checkData(JSON.parse(referenceText));
  const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('GPU adapter unavailable');
  const timestamp=adapter.features.has('timestamp-query');device=await adapter.requestDevice({requiredFeatures:timestamp?['timestamp-query']:[]});
  device.lost.then(()=>{lost=true;});device.addEventListener('uncapturederror',event=>{uncaptured=event.error.message;});
  device.pushErrorScope('validation');
  const module=device.createShaderModule({code:shader});const errors=(await module.getCompilationInfo()).messages.filter(x=>x.type==='error');if(errors.length)throw Error(errors.map(e=>e.message).join('\n'));
  const pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs'},fragment:{module,entryPoint:'fs',targets:[{format:'rgba8unorm'}]},primitive:{topology:'triangle-list'}});
  const moduleResponse=await fetch(import.meta.url);if(!moduleResponse.ok)throw Error('module hash fetch failed');
  const report={schema:'gpuE08/v1',environment:{date:new Date().toISOString(),userAgent:navigator.userAgent,vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,timestamp_query:timestamp,secure_context:isSecureContext,module_sha256:await digest(await moduleResponse.arrayBuffer()),shader_sha256:await digest(new TextEncoder().encode(shader)),cpu_reference_sha256:await digest(new TextEncoder().encode(referenceText))},parameters:{P,C,W,format:'rgba8unorm',policy:'pinned-demand LRU',trajectories,warmup:4,pairs:30,order:'even pair resident/stream; odd pair stream/resident',sample_start:'cold streaming cache; resident preloaded',quantile:'sorted[floor(p*(n-1))]',inflight_frames:1},logical_bytes:{resident_texture:P*PAGE_BYTES,stream_texture:C*PAGE_BYTES,per_arm_table:4*P,per_arm_control:16,per_arm_output:PAGE_BYTES,per_arm_readback:PAGE_BYTES,per_arm_query_resolve:timestamp?256:0,per_arm_query_read:timestamp?16:0,cpu_source_pages:P*PAGE_BYTES,physical_vram_measured:false},initialization:[],quality:[],negative:{},warmup:[],samples:[],raf:[],summary:[]};
  function write(arm,selection){
   for(const c of selection.changes)device.queue.writeTexture({texture:arm.texture,origin:[0,0,c.layer]},references[c.page],{bytesPerRow:W*4,rowsPerImage:W},[W,W,1]);
   if(selection.misses)device.queue.writeBuffer(arm.mapping,0,selection.table);
   return {texture_bytes:selection.misses*PAGE_BYTES,table_bytes:selection.misses?4*P:0,texture_calls:selection.misses,table_calls:selection.misses?1:0};
  }
  async function createArm(mode){
   const start=performance.now(),layers=mode==='resident'?P:C;
   const arm={mode,cache:new PageCache(layers)};
   arm.texture=keep(device.createTexture({size:[W,W,layers],format:'rgba8unorm',usage:GPUTextureUsage.COPY_DST|GPUTextureUsage.TEXTURE_BINDING}));
   arm.mapping=keep(device.createBuffer({size:P*4,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}));
   arm.control=keep(device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}));
   arm.output=keep(device.createTexture({size:[W,W],format:'rgba8unorm',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC}));
   arm.readback=keep(device.createBuffer({size:PAGE_BYTES,usage:GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST}));
   if(timestamp){arm.queries=keep(device.createQuerySet({type:'timestamp',count:2}));arm.resolve=keep(device.createBuffer({size:256,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC}));arm.queryRead=keep(device.createBuffer({size:16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}));}
   arm.bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:arm.texture.createView({dimension:'2d-array'})},{binding:1,resource:{buffer:arm.mapping}},{binding:2,resource:{buffer:arm.control}}]});
   let uploaded={texture_bytes:0,table_bytes:0,texture_calls:0,table_calls:0};
   if(mode==='resident')uploaded=write(arm,arm.cache.select(Array.from({length:P},(_,i)=>i)));
   await device.queue.onSubmittedWorkDone();valid();report.initialization.push({mode,...uploaded,allocation_upload_completed_ms:performance.now()-start});return arm;
  }
  const arms={resident:await createArm('resident'),stream:await createArm('stream')};
  function reset(arm){if(arm.mode==='stream')arm.cache.reset();}
  async function frame(arm,page,badMapping=false){
   valid();await device.queue.onSubmittedWorkDone();const start=performance.now();
   const selectStart=performance.now(),selection=arm.cache.select([page]),selection_ms=performance.now()-selectStart;
   const uploadStart=performance.now(),bytes=write(arm,selection);device.queue.writeBuffer(arm.control,0,new Uint32Array([page,0,0,0]));
   if(badMapping){const wrong=selection.table.slice();wrong[page]=(wrong[page]+1)%arm.cache.capacity;device.queue.writeBuffer(arm.mapping,0,wrong);}
   const upload_cpu_ms=performance.now()-uploadStart,encodeStart=performance.now();
   const encoder=device.createCommandEncoder();const descriptor={colorAttachments:[{view:arm.output.createView(),clearValue:[0,0,0,0],loadOp:'clear',storeOp:'store'}]};
   if(timestamp)descriptor.timestampWrites={querySet:arm.queries,beginningOfPassWriteIndex:0,endOfPassWriteIndex:1};
   const pass=encoder.beginRenderPass(descriptor);pass.setPipeline(pipeline);pass.setBindGroup(0,arm.bind);pass.draw(3);pass.end();
   if(timestamp){encoder.resolveQuerySet(arm.queries,0,2,arm.resolve,0);encoder.copyBufferToBuffer(arm.resolve,0,arm.queryRead,0,16);}
   device.queue.submit([encoder.finish()]);const encode_submit_ms=performance.now()-encodeStart;
   await device.queue.onSubmittedWorkDone();const end_to_end_ms=performance.now()-start;valid();
   let gpu_render_ms=null;
   if(timestamp){await arm.queryRead.mapAsync(GPUMapMode.READ);try{const q=new BigUint64Array(arm.queryRead.getMappedRange());if(q[1]<q[0])throw Error('timestamp order');gpu_render_ms=Number(q[1]-q[0])/1e6;}finally{arm.queryRead.unmap();}}
   const pixels=await readPixels(device,arm.output,arm.readback);valid();
   return {pixels,row:{page,layer:selection.table[page],hits:selection.hits,misses:selection.misses,evictions:selection.evictions,changes:selection.changes,...bytes,control_bytes:16,selection_ms,upload_cpu_ms,encode_submit_ms,end_to_end_ms,gpu_render_ms,checksum:checksum(pixels)}};
  }
  async function uploadBatch(arm,trajectory){
   reset(arm);const rows=[];
   for(const page of trajectory.requests){valid();await device.queue.onSubmittedWorkDone();const selectStart=performance.now(),selection=arm.cache.select([page]),selection_ms=performance.now()-selectStart;
    const start=performance.now(),bytes=write(arm,selection),upload_cpu_ms=performance.now()-start;
    if(selection.misses)await device.queue.onSubmittedWorkDone();const completed_ms=selection.misses?performance.now()-start:0;
    rows.push({page,hits:selection.hits,misses:selection.misses,evictions:selection.evictions,...bytes,selection_ms,upload_cpu_ms,completed_ms,effective_texture_MBps:bytes.texture_bytes&&completed_ms>0?bytes.texture_bytes/completed_ms/1000:null});
   }return rows;
  }
  async function batch(arm,trajectory){
   const upload=await uploadBatch(arm,trajectory);reset(arm);const frames=[];
   for(const page of trajectory.requests){const result=await frame(arm,page);requireEqual(result.pixels,references[page]);frames.push({...result.row,rgba_mismatches:0});}
   const sum=(rows,key)=>rows.reduce((a,b)=>a+b[key],0),gpu=timestamp?sum(frames,'gpu_render_ms'):null;
   return {upload,frames,totals:{selection_ms:sum(frames,'selection_ms'),encode_submit_ms:sum(frames,'encode_submit_ms'),upload_cpu_ms:sum(frames,'upload_cpu_ms'),end_to_end_ms:sum(frames,'end_to_end_ms'),gpu_render_ms:gpu,texture_bytes:sum(frames,'texture_bytes'),table_bytes:sum(frames,'table_bytes'),control_bytes:sum(frames,'control_bytes'),upload_completed_ms:sum(upload,'completed_ms'),upload_texture_bytes:sum(upload,'texture_bytes')}};
  }
  progress('逐帧检查完整 RGBA 与错误映射负对照');
  for(const trajectory of trajectories){reset(arms.stream);for(let index=0;index<trajectory.requests.length;index++){
   const page=trajectory.requests[index],a=await frame(arms.resident,page),b=await frame(arms.stream,page);requireEqual(a.pixels,references[page]);requireEqual(b.pixels,references[page]);requireEqual(a.pixels,b.pixels);
   report.quality.push({trajectory:trajectory.name,frame:index,page,resident:a.row,stream:b.row,different_bytes:0,resident_rgba_base64:base64(a.pixels),stream_rgba_base64:base64(b.pixels)});
  }}
  try{arms.stream.cache.select([0,1,2,3]);throw Error('capacity control unexpectedly accepted');}catch(e){if(e.message!=='frame demand exceeds capacity')throw e;report.negative.capacity={rejected:true,message:e.message};}
  const wrong=await frame(arms.resident,0,true),difference=compareRGBA(wrong.pixels,references[0]);if(difference.equal)throw Error('wrong mapping control not detected');
  report.negative.mapping={...difference,rgba_base64:base64(wrong.pixels)};device.queue.writeBuffer(arms.resident.mapping,0,arms.resident.cache.table);await device.queue.onSubmittedWorkDone();
  for(const trajectory of trajectories){
   for(let i=0;i<4;i++)for(const mode of i%2?['stream','resident']:['resident','stream']){progress(`${trajectory.name} 预热 ${i+1}/4 ${mode}`);report.warmup.push({trajectory:trajectory.name,index:i,mode,...await batch(arms[mode],trajectory)});}
   for(let pair=0;pair<30;pair++){const order=pair%2?['stream','resident']:['resident','stream'];for(let position=0;position<2;position++){const mode=order[position];progress(`${trajectory.name} 样本 ${pair+1}/30 ${mode}`);report.samples.push({trajectory:trajectory.name,pair,position,order:order.join('/'),mode,...await batch(arms[mode],trajectory)});}}
   for(const mode of ['resident','stream']){const samples=report.samples.filter(s=>s.trajectory===trajectory.name&&s.mode===mode);const summary={trajectory:trajectory.name,mode};
    for(const key of ['selection_ms','encode_submit_ms','upload_cpu_ms','end_to_end_ms','upload_completed_ms'])summary[key]=quantiles(samples.map(s=>s.totals[key]));
    summary.gpu_render_ms=timestamp?quantiles(samples.map(s=>s.totals.gpu_render_ms)):null;
    const bandwidth=samples.map(s=>s.totals.upload_texture_bytes&&s.totals.upload_completed_ms>0?s.totals.upload_texture_bytes/s.totals.upload_completed_ms/1000:null).filter(x=>x!==null);summary.effective_texture_MBps=bandwidth.length?quantiles(bandwidth):null;
    report.summary.push(summary);
   }
  }
  progress('独立 rAF 串行帧回调检查（包含读回开销）');
  for(const trajectory of trajectories)for(const mode of ['resident','stream']){
   const arm=arms[mode];reset(arm);let previous=null;const intervals=[],frames=[];
   for(let index=-4;index<trajectory.requests.length;index++){const stamp=await new Promise(resolve=>requestAnimationFrame(resolve));valid();if(index>=0&&previous!==null)intervals.push(stamp-previous);previous=stamp;
    const page=trajectory.requests[(index+trajectory.requests.length)%trajectory.requests.length],result=await frame(arm,page);requireEqual(result.pixels,references[page]);if(index>=0)frames.push(result.row);display(result.pixels);
   }
   report.raf.push({trajectory:trajectory.name,mode,warmup_frames:4,includes_serial_readback:true,interval_ms:intervals,quantiles:quantiles(intervals),frames});
  }
  const error=await device.popErrorScope();if(error)throw Error(error.message);valid();report.completed=true;
  report.notes=['Both arms coexist during this experiment; per-arm texture payload compares policies and does not measure a physical VRAM delta. All eight source pages are already in CPU memory; no disk/network fetch latency is timed. The fixed trajectories visit pages0..3 of the eight-page strip.','All quality and timed frames read back every RGBA byte and compare to independently generated C++ bytes before accepting a sample.','End-to-end starts before selection, includes texture/table/control writes, draw, optional query resolve/copy and queue-completion notification; excludes pixel readback and timestamp mapping.','Upload-only is a separate cold-cache replay with no draw or control-buffer upload. Effective MB/s numerator is texture payload only; table bytes are recorded separately.','Each sample resets streaming metadata outside timing; existing physical layers are overwritten on cold-cache misses. Resident texture remains preloaded.','Timestamps cover render pass only; zero timing can reflect precision. Logical payload is not physical VRAM.','rAF callbacks serialize completion and readback; intervals are diagnostic scheduling with this instrumentation, not display latency or a pipelined game FPS.'];
  return report;
 }finally{document.removeEventListener('visibilitychange',visibility);for(const resource of resources.reverse())resource.destroy();if(device)device.destroy();}
}
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id);let receipt=null,busy=false;
 $('run').addEventListener('click',async()=>{if(busy)return;busy=true;receipt=null;$('download').disabled=true;$('run').disabled=true;$('readback').textContent='';$('summary').textContent='';
  try{receipt=await runExperiment(message=>{$('status').textContent=message;});$('readback').textContent=JSON.stringify(receipt);$('summary').textContent=JSON.stringify({quality_frames:receipt.quality.length,negative:receipt.negative.capacity,wrong_mapping_pixels:receipt.negative.mapping.differentPixels,samples:receipt.samples.length,summary:receipt.summary},null,2);$('status').textContent='PASS：画质、负对照、预热、30 对样本与 rAF 检查完成';$('download').disabled=false;}
  catch(e){receipt=null;$('status').textContent=`FAIL：${e.message}`;$('readback').textContent='';}
  finally{busy=false;$('run').disabled=false;}
 });
 $('download').addEventListener('click',()=>{if(!receipt)return;const url=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='gpuE08-readback.json';a.click();URL.revokeObjectURL(url);});
}
