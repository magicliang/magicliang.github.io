export const WIDTH=128,HEIGHT=128,N=WIDTH*HEIGHT-3,GUARD=64;
export function validateReference(data) {
 if(data?.version!==1||data.width!==WIDTH||data.height!==HEIGHT||data.count!==N||data.first_hits!==8192||data.second_hits!==4096||!Array.isArray(data.reference)||data.reference.length!==N*4||!data.reference.every(Number.isFinite)||!Array.isArray(data.active_ids)||data.active_ids.length!==8192)throw Error('invalid CPU reference layout');
 let active=0;
 for(let id=0;id<N;id++) {
  const first=id%WIDTH<64,second=first&&Math.floor(id/WIDTH)>=32&&Math.floor(id/WIDTH)<96;
  const rho=[.25+(id%16)/32,.25+(Math.floor(id/WIDTH)%16)/32,.5];
  const expected=first?rho.map((v,k)=>v*(second?[.5,.75,.625][k]:.125)):[.125,.125,.125];expected.push(second?2:first?1:0);
  for(let k=0;k<4;k++)if(Math.abs(data.reference[id*4+k]-expected[k])>1e-12)throw Error('CPU reference differs from analytic mirror oracle');
  if(first&&data.active_ids[active++]!==id)throw Error('invalid active ID set');
 }
 return data;
}
export function makeLayout(interleaved,permuted) {
 if(typeof interleaved!=='boolean'||typeof permuted!=='boolean')throw Error('invalid layout flags');
 const alive=[],dead=[],ids=[];
 for(let id=0;id<N;id++)(id%WIDTH<64?alive:dead).push(id);
 if(interleaved){for(let i=0;i<alive.length;i++){ids.push(alive[i]);if(i<dead.length)ids.push(dead[i]);}}else ids.push(...alive,...dead);
 const materials=new Float32Array(N*4),seen=new Set();
 for(let id=0;id<N;id++) {const address=permuted?(id*4099)%N:id;seen.add(address);materials.set([.25+(id%16)/32,.25+(Math.floor(id/WIDTH)%16)/32,.5,1],address*4);}
 if(seen.size!==N)throw Error('material addresses not a permutation');
 let mixedWorkgroups=0;
 for(let begin=0;begin<N;begin+=64){const group=ids.slice(begin,begin+64);if(group.some(id=>id%WIDTH<64)&&group.some(id=>id%WIDTH>=64))mixedWorkgroups++;}
 return {ids:new Uint32Array(ids),materials,mixedWorkgroups};
}
export function schedule() {return Array.from({length:30},(_,pair)=>pair%2?['queue','scan']:['scan','queue']);}
export function verifyReadback(data,readback,mode) {
 validateReference(data);
 if(!['scan','queue'].includes(mode)||!Array.isArray(readback?.output)||readback.output.length!==(N+GUARD)*4||!readback.output.every(Number.isFinite)||!Array.isArray(readback.queue)||readback.queue.length!==N+GUARD||!readback.queue.every(x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff)||!Array.isArray(readback.counters)||readback.counters.length!==8||!readback.counters.every(x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff))throw Error('invalid readback layout');
 const [count,overflow,processed,invalid,tailWrites,secondHits]=readback.counters;
 if(count!==8192||overflow!==0||processed!==8192||invalid!==0||tailWrites!==0||secondHits!==4096)throw Error('queue counters rejected');
 if(readback.output.slice(N*4).some(x=>x!==0))throw Error('output tail guard changed');
 if(readback.queue.slice(N).some(x=>x!==0xffffffff))throw Error('queue tail guard changed');
 let maximumError=0;
 for(let i=0;i<N*4;i++)maximumError=Math.max(maximumError,Math.abs(readback.output[i]-data.reference[i]));
 if(maximumError>2e-6)throw Error(`radiance or termination mismatch ${maximumError}`);
 if(mode==='queue') {
  const ids=readback.queue.slice(0,count).sort((a,b)=>a-b);
  if(ids.some((id,i)=>id!==data.active_ids[i]))throw Error('queue ID set mismatch');
  if(readback.queue.slice(count).some(id=>id!==0xffffffff))throw Error('unused queue slot changed');
 }else if(readback.queue.some(id=>id!==0xffffffff))throw Error('scan modified queue');
 return {maximumError,count,processed,secondHits,guardSlots:GUARD};
}
const shader=`
struct Parameters {n:u32,capacity:u32,permuted:u32,mutation:u32};
struct Task {origin:vec4f,direction:vec4f,beta:vec4f};
struct Counters {count:atomic<u32>,overflow:atomic<u32>,processed:atomic<u32>,invalid:atomic<u32>,tail:atomic<u32>,second:atomic<u32>,pad0:atomic<u32>,pad1:atomic<u32>};
@group(0) @binding(0) var<uniform> parameters:Parameters;
@group(0) @binding(1) var<storage,read> order:array<u32>;
@group(0) @binding(2) var<storage,read> materials:array<vec4f>;
@group(0) @binding(3) var<storage,read_write> states:array<Task>;
@group(0) @binding(4) var<storage,read_write> queue:array<u32>;
@group(0) @binding(5) var<storage,read_write> counters:Counters;
@group(0) @binding(6) var<storage,read_write> results:array<vec4f>;
fn reflected(d:vec3f,n:vec3f)->vec3f {return d-2.*dot(d,n)/dot(n,n)*n;}
fn environment(d:vec3f)->f32 {return .125+.875*max(0.,d.z);}
fn plane_t(o:vec3f,d:vec3f,n:vec3f,offset:f32)->f32 {let denominator=dot(n,d);if(denominator==0.){return -1.;}return (offset-dot(n,o))/denominator;}
fn produce(thread:u32,compact:bool) {
 if(thread>=parameters.n) {
  if(parameters.mutation==4u){results[thread]=vec4f(9.);atomicAdd(&counters.tail,1u);}return;
 }
 let id=order[thread];let x=(f32(id%128u)+.5)/64.-1.;let y=(f32(id/128u)+.5)/64.-1.;
 let origin=vec3f(x,y,2.);let direction=vec3f(0.,0.,-1.);let t=plane_t(origin,direction,vec3f(1.,0.,1.),0.);let p=origin+t*direction;
 states[id]=Task(vec4f(0.),vec4f(0.),vec4f(0.));results[id]=vec4f(vec3f(environment(direction)),0.);
 if(t<=0.||p.x>=0.||p.x< -1.||abs(p.y)>=1.){return;}
 let address=select(id,(id*4099u)%parameters.n,parameters.permuted==1u);
 states[id]=Task(vec4f(p,1.),vec4f(reflected(direction,vec3f(1.,0.,1.)),0.),materials[address]);results[id]=vec4f(0.,0.,0.,-1.);
 let slot=atomicAdd(&counters.count,1u);
 if(compact){if(slot<parameters.capacity){queue[slot]=id;}else{atomicAdd(&counters.overflow,1u);}}
}
fn consume(id:u32) {
 if(id>=parameters.n){atomicAdd(&counters.invalid,1u);return;}
 let task=states[id];if(task.origin.w==0.){atomicAdd(&counters.invalid,1u);return;}
 atomicAdd(&counters.processed,1u);
 let t=plane_t(task.origin.xyz,task.direction.xyz,vec3f(1.,0.,-1.),2.);let p=task.origin.xyz+t*task.direction.xyz;
 var beta=task.beta.xyz;var direction=task.direction.xyz;var status=1.;
 if(t>0.&&abs(p.y)<.5&&p.z>=0.&&p.z<1.){beta*=vec3f(.5,.75,.625);direction=reflected(direction,vec3f(1.,0.,-1.));status=2.;atomicAdd(&counters.second,1u);}
 results[id]=vec4f(beta*environment(direction),status);
}
@compute @workgroup_size(64) fn produce_scan(@builtin(global_invocation_id) gid:vec3u){produce(gid.x,false);}
@compute @workgroup_size(64) fn produce_queue(@builtin(global_invocation_id) gid:vec3u){produce(gid.x,true);}
@compute @workgroup_size(64) fn consume_scan(@builtin(global_invocation_id) gid:vec3u){if(gid.x>=parameters.n){return;}let id=order[gid.x];if(states[id].origin.w>0.){consume(id);}}
@compute @workgroup_size(64) fn consume_queue(@builtin(global_invocation_id) gid:vec3u){if(gid.x>=min(atomicLoad(&counters.count),parameters.capacity)){return;}consume(queue[gid.x]);}`;
const $=id=>document.getElementById(id);
let data,device,environment,resources,pipelines,bind,query,queryResolve,queryRead,ready=false,lost=false,busy=false,receipt;
function ensureLive(){if(lost||!ready)throw Error('device unavailable; reload');if(document.hidden)throw Error('page hidden; measurement invalid');}
function invalidate(message){receipt=undefined;$('download').disabled=true;$('readback').textContent='';if(message)$('status').textContent=message;}
async function hash(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');}
async function initialize(){
 if(device){ensureLive();return;}
 if(!navigator.gpu)throw Error('WebGPU unavailable');
 const response=await fetch(new URLSearchParams(location.search).get('data')??'build/wavefrontE04.json');if(!response.ok)throw Error('CPU reference fetch failed');const referenceBytes=await response.arrayBuffer();data=validateReference(JSON.parse(new TextDecoder().decode(referenceBytes)));
 const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('adapter unavailable');
 const timestamp=adapter.features.has('timestamp-query');device=await adapter.requestDevice({requiredFeatures:timestamp?['timestamp-query']:[]});
 device.lost.then(info=>{lost=true;invalidate(`device lost: ${info.message}`);});device.addEventListener('uncapturederror',e=>{lost=true;invalidate(e.error.message);});
 if(device.limits.maxComputeWorkgroupsPerDimension<Math.ceil(N/64)||device.limits.maxStorageBuffersPerShaderStage<6||device.limits.maxStorageBufferBindingSize<N*48)throw Error('device limits insufficient');
 const source=await fetch(import.meta.url);if(!source.ok)throw Error('source hash fetch failed');
 environment={date:new Date().toISOString(),vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,userAgent:navigator.userAgent,timestampQuery:timestamp,module_sha256:await hash(await source.arrayBuffer()),shader_sha256:await hash(new TextEncoder().encode(shader)),reference_sha256:await hash(referenceBytes),maxComputeWorkgroupsPerDimension:device.limits.maxComputeWorkgroupsPerDimension,maxStorageBufferBindingSize:device.limits.maxStorageBufferBindingSize};
 const storage=(size)=>device.createBuffer({size,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC});
 resources={parameters:device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),order:storage(N*4),materials:storage(N*16),states:storage(N*48),queue:storage((N+GUARD)*4),counters:storage(32),output:storage((N+GUARD)*16),seedQueue:device.createBuffer({size:(N+GUARD)*4,usage:GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST}),seedCounters:device.createBuffer({size:32,usage:GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST})};
 device.queue.writeBuffer(resources.seedQueue,0,new Uint32Array(N+GUARD).fill(0xffffffff));
 const layout=device.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.COMPUTE,buffer:{type:'uniform'}},...[1,2,3,4,5,6].map(binding=>({binding,visibility:GPUShaderStage.COMPUTE,buffer:{type:binding<=2?'read-only-storage':'storage'}}))]});
 const pipelineLayout=device.createPipelineLayout({bindGroupLayouts:[layout]});
 bind=device.createBindGroup({layout,entries:['parameters','order','materials','states','queue','counters','output'].map((key,binding)=>({binding,resource:{buffer:resources[key]}}))});
 const module=device.createShaderModule({code:shader});const errors=(await module.getCompilationInfo()).messages.filter(e=>e.type==='error');if(errors.length)throw Error(errors.map(e=>e.message).join('\n'));
 pipelines={};for(const entryPoint of ['produce_scan','produce_queue','consume_scan','consume_queue'])pipelines[entryPoint]=await device.createComputePipelineAsync({layout:pipelineLayout,compute:{module,entryPoint}});
 if(timestamp){query=device.createQuerySet({type:'timestamp',count:4});queryResolve=device.createBuffer({size:32,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC});queryRead=device.createBuffer({size:32,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});}
 ready=true;ensureLive();
}
function upload(interleaved,permuted,capacity=N,mutation=0){
 const layout=makeLayout(interleaved,permuted);device.queue.writeBuffer(resources.order,0,layout.ids);device.queue.writeBuffer(resources.materials,0,layout.materials);device.queue.writeBuffer(resources.parameters,0,new Uint32Array([N,capacity,Number(permuted),mutation]));
 const seed=new Uint32Array(8);if(mutation===2)seed[0]=11;device.queue.writeBuffer(resources.seedCounters,0,seed);return layout.mixedWorkgroups;
}
async function sample(mode){
 ensureLive();const start=performance.now(),encoder=device.createCommandEncoder();
 encoder.copyBufferToBuffer(resources.seedQueue,0,resources.queue,0,(N+GUARD)*4);encoder.copyBufferToBuffer(resources.seedCounters,0,resources.counters,0,32);encoder.clearBuffer(resources.output);
 for(let stage=0;stage<2;stage++){
  const descriptor=query?{timestampWrites:{querySet:query,beginningOfPassWriteIndex:stage*2,endOfPassWriteIndex:stage*2+1}}:{};
  const pass=encoder.beginComputePass(descriptor);pass.setPipeline(pipelines[`${stage?'consume':'produce'}_${mode}`]);pass.setBindGroup(0,bind);pass.dispatchWorkgroups(Math.ceil(N/64));pass.end();
 }
 if(query){encoder.resolveQuerySet(query,0,4,queryResolve,0);encoder.copyBufferToBuffer(queryResolve,0,queryRead,0,32);}
 device.queue.submit([encoder.finish()]);const submitted=performance.now();await device.queue.onSubmittedWorkDone();const done=performance.now();ensureLive();
 let timestamps=null,gpuStageMs=null;
 if(query){await queryRead.mapAsync(GPUMapMode.READ);try{const stamps=Array.from(new BigUint64Array(queryRead.getMappedRange()));if(stamps[1]<stamps[0]||stamps[3]<stamps[2]||stamps[2]<stamps[1])throw Error('timestamps decreased');timestamps=stamps.map(String);gpuStageMs=[Number(stamps[1]-stamps[0])/1e6,Number(stamps[3]-stamps[2])/1e6];}finally{queryRead.unmap();}}
 return {mode,cpuEncodeSubmitMs:submitted-start,cpuWaitMs:done-submitted,cpuSubmitToDoneMs:done-start,timestamps,gpuStageMs,gpuSumMs:gpuStageMs?gpuStageMs[0]+gpuStageMs[1]:null};
}
async function readback(){
 const keys=['output','queue','counters'],sizes=[(N+GUARD)*16,(N+GUARD)*4,32],buffers=sizes.map(size=>device.createBuffer({size,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}));
 try{const encoder=device.createCommandEncoder();for(let i=0;i<3;i++)encoder.copyBufferToBuffer(resources[keys[i]],0,buffers[i],0,sizes[i]);device.queue.submit([encoder.finish()]);await Promise.all(buffers.map(b=>b.mapAsync(GPUMapMode.READ)));ensureLive();return Object.fromEntries(keys.map((key,i)=>[key,Array.from(i?new Uint32Array(buffers[i].getMappedRange()):new Float32Array(buffers[i].getMappedRange()))]));}finally{for(const buffer of buffers)buffer.destroy();}
}
function display(values){const context=$('canvas').getContext('2d'),image=context.createImageData(WIDTH,HEIGHT);for(let id=0;id<WIDTH*HEIGHT;id++){for(let k=0;k<3;k++){const c=id<N?values[id*4+k]:0;image.data[id*4+k]=Math.round(255*(c<=.0031308?12.92*c:1.055*c**(1/2.4)-.055));}image.data[id*4+3]=255;}context.putImageData(image,0,0);}
function finish(value){receipt=value;$('readback').textContent=JSON.stringify(receipt);$('download').disabled=false;}
async function benchmark(){
 const samples=[],checks=[],readbacks=[];
 for(const interleaved of [false,true])for(const permuted of [false,true]){
  const mixedWorkgroups=upload(interleaved,permuted);
  for(const mode of ['scan','queue']){await sample(mode);const raw=await readback();checks.push({interleaved,permuted,mode,mixedWorkgroups,...verifyReadback(data,raw,mode)});readbacks.push({interleaved,permuted,mode,...raw});if(mode==='queue')display(raw.output);}
  for(let warmup=0;warmup<4;warmup++)for(const mode of ['scan','queue'])samples.push({interleaved,permuted,warmup,...await sample(mode)});
  const pairs=schedule();for(let pair=0;pair<pairs.length;pair++)for(let position=0;position<2;position++){samples.push({interleaved,permuted,pair,position,...await sample(pairs[pair][position])});$('status').textContent=`测量 grouped/interleaved=${Number(interleaved)}, permuted=${Number(permuted)}, ${pair+1}/30对`;
  }
  const raw=await readback();checks.push({interleaved,permuted,mode:'scan',afterTiming:true,...verifyReadback(data,raw,'scan')});readbacks.push({interleaved,permuted,mode:'scan',afterTiming:true,...raw});
 }
 finish({environment,negative:false,scope:'two ideal mirror reflections at most then directional environment, deterministic path transport; general compute, no hardware ray tracing; both modes launch 16384 lanes/stage',timingBoundary:'GPU timestamps cover two compute passes incl common instrumentation atomics; exclude queue reset/copies/upload/readback. CPU encode includes reset/copies/submission, wait is completion notification wall time. Four warmups/mode; 30 ABBA pairs/config. Readbacks outside timing. Layout changes can alter locality and branch grouping together; no pure divergence claim.',samples,checks,readbacks});
 $('log').textContent=JSON.stringify({environment,checks,measuredSamples:samples.filter(s=>s.pair!==undefined).length,warmups:samples.filter(s=>s.warmup!==undefined).length,scope:receipt.scope},null,2);$('status').textContent='PASS：4种布局 × 30对，所有像素与队列检查通过';
}
async function negatives(){
 const cases=[];
 for(const [name,capacity,mutation] of [['capacity',17,0],['stale',N,2],['tail',N,4]]){
  upload(false,false,capacity,mutation);const timing=await sample('queue'),raw=await readback();let rejected='';try{verifyReadback(data,raw,'queue');}catch(error){rejected=error.message;}
  if(!rejected)throw Error(`negative ${name} passed unexpectedly`);
  if(name==='capacity'&&(raw.counters[0]!==8192||raw.counters[1]!==8175||raw.counters[2]!==17))throw Error('capacity counters wrong');
  if(name==='stale'&&(raw.counters[0]!==8203||raw.counters[3]!==11))throw Error('stale counter injection missing');
  if(name==='tail'&&(raw.counters[4]!==3||raw.output.slice(N*4,N*4+12).some(v=>v!==9)))throw Error('tail injection missing');
  cases.push({name,capacity,mutation,rejected,timing,...raw});
 }
 upload(false,false);await sample('queue');const recovered=await readback();const recovery=verifyReadback(data,recovered,'queue');display(recovered.output);
 finish({environment,negative:true,cases,recovery,recovered});$('log').textContent=JSON.stringify({environment,cases:cases.map(c=>({name:c.name,rejected:c.rejected,counters:c.counters})),recovery},null,2);$('status').textContent='PASS：容量、陈旧计数、尾保护错误均被检出；恢复通过';
}
async function action(fn){if(busy)return;busy=true;invalidate();$('run').disabled=true;$('negative').disabled=true;$('log').textContent='';let scoped=false;try{await initialize();device.pushErrorScope('validation');scoped=true;await fn();const error=await device.popErrorScope();scoped=false;if(error)throw Error(error.message);ensureLive();}catch(error){invalidate(`FAIL：${error.message}`);}finally{if(scoped){const error=await device.popErrorScope();if(error)invalidate(`FAIL：${error.message}`);}busy=false;$('run').disabled=false;$('negative').disabled=false;}}
if(typeof document!=='undefined'){
 $('run').onclick=()=>action(benchmark);$('negative').onclick=()=>action(negatives);
 $('download').onclick=()=>{if(!receipt)return;const url=URL.createObjectURL(new Blob([JSON.stringify(receipt)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download=receipt.negative?'E04-gpu-negative.json':'E04-gpu-readback.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
}
