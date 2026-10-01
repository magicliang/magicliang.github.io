const $=id=>document.getElementById(id);
let data,device,context,pipeline,previewPipeline,uniform,bind,previewBind,vertex,depth,ready=false,lost=false,busy=false,playing=false,frameId=0,epoch=0,environment,receipt;
const code=`
struct Scene {vp:mat4x4f,light:vec4f,lighting:vec4f};
@group(0) @binding(0) var<uniform> scene:Scene;
struct Vertex {@location(0) p:vec3f,@location(1) n:vec3f,@location(2) rho:vec3f,@location(3) object:f32};
struct Interpolated {@builtin(position) clip:vec4f,@location(0) p:vec3f,@location(1) n:vec3f,@location(2) rho:vec3f,@location(3) @interpolate(flat) object:f32};
@vertex fn vs(v:Vertex)->Interpolated {var o:Interpolated;o.clip=scene.vp*vec4f(v.p,1);o.p=v.p;o.n=v.n;o.rho=v.rho;o.object=v.object;return o;}
fn shade(v:Interpolated)->vec3f {let toLight=scene.light.xyz-v.p;let r2=dot(toLight,toLight);let cosine=max(0.,dot(normalize(v.n),normalize(toLight)));return v.rho*(scene.lighting.y+scene.lighting.x*cosine/(3.141592653589793*r2));}
struct Result {@location(0) color:vec4f,@location(1) auxiliary:vec4f};
@fragment fn linear(v:Interpolated)->Result {var o:Result;o.color=vec4f(shade(v),v.object);o.auxiliary=vec4f(v.p,v.clip.z);return o;}
fn encode(c:vec3f)->vec3f {return select(12.92*c,1.055*pow(c,vec3f(1./2.4))-.055,c>vec3f(.0031308));}
@fragment fn display(v:Interpolated)->@location(0) vec4f {let c=shade(v);return vec4f(encode(c/(1.+c)),1);}`;
function checkData(d){
 const finite=(a,n)=>Array.isArray(a)&&a.length===n&&a.every(Number.isFinite),object=x=>Number.isInteger(x)&&x>=0&&x<=3;
 if(d.version!==1||d.width!==128||d.height!==128||!finite(d.camera?.vp_columns,16)||!Array.isArray(d.frames)||d.frames.length!==3)throw Error('场景版本或尺寸不符');
 if(!finite(d.rest_vbo,702)||!Array.isArray(d.vertex_object_ids)||d.vertex_object_ids.length!==78||!d.vertex_object_ids.every(x=>object(x)&&x>0))throw Error('顶点布局不符');
 if(d.boxes?.length!==2||!Array.isArray(d.motion?.samples)||d.motion.samples.length!==241||d.motion.moving_object!==2||!Number.isFinite(d.light?.intensity)||d.light.intensity<0||!Number.isFinite(d.light?.ambient)||d.light.ambient<0||!finite(d.light.position,3))throw Error('场景参数不符');
 for(let i=0;i<2;i++)if(d.boxes[i].object_id!==i+2||!finite(d.boxes[i].center,3))throw Error('对象布局不符');
 const pixels=d.width*d.height;
 for(let j=0;j<3;j++){const f=d.frames[j],r=f.reference;if(f.tick!==j*120||f.t_seconds!==f.tick/120||!finite(f.vbo,702)||!finite(r?.linear_rgb,3*pixels)||r.linear_rgb.some(x=>x<0)||!Array.isArray(r?.object)||r.object.length!==pixels||!r.object.every(object)||!finite(r?.world_position,3*pixels)||!finite(r?.depth,pixels)||r.depth.some(x=>x<0||x>1)||!Array.isArray(r?.boundary)||r.boundary.length!==pixels||!r.boundary.every(x=>typeof x==='boolean'))throw Error('冻结参考布局不符');}
 for(let i=0;i<241;i++){const s=d.motion.samples[i];if(s.tick!==i||s.t_seconds!==i/120||!Number.isFinite(s.offset_x))throw Error('运动表不符');}
}
async function initialize(){
 if(device){if(!ready||lost)throw Error('设备状态无效，请重新加载');return;}
 if(!navigator.gpu)throw Error('WebGPU不可用');
 const response=await fetch(new URLSearchParams(location.search).get('data')??'project33.json');if(!response.ok)throw Error(`场景请求${response.status}`);data=await response.json();checkData(data);
 const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('无可用adapter');device=await adapter.requestDevice();
 environment={date:new Date().toISOString(),vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,userAgent:navigator.userAgent};
 device.lost.then(()=>{lost=true;playing=false;$('status').textContent='设备丢失，请重新加载';});device.addEventListener('uncapturederror',e=>{lost=true;playing=false;$('status').textContent=e.error.message;});
 const module=device.createShaderModule({code});const errors=(await module.getCompilationInfo()).messages.filter(x=>x.type==='error');if(errors.length)throw Error(errors.map(x=>x.message).join('\n'));
 const layout={arrayStride:40,attributes:[{shaderLocation:0,format:'float32x3',offset:0},{shaderLocation:1,format:'float32x3',offset:12},{shaderLocation:2,format:'float32x3',offset:24},{shaderLocation:3,format:'float32',offset:36}]};
 const base={layout:'auto',vertex:{module,entryPoint:'vs',buffers:[layout]},primitive:{topology:'triangle-list',cullMode:'none'},depthStencil:{format:'depth32float',depthWriteEnabled:true,depthCompare:'less'}};
 pipeline=await device.createRenderPipelineAsync({...base,fragment:{module,entryPoint:'linear',targets:[{format:'rgba32float'},{format:'rgba32float'}]}});
 context=$('canvas').getContext('webgpu');const format=navigator.gpu.getPreferredCanvasFormat();context.configure({device,format,alphaMode:'opaque'});
 previewPipeline=await device.createRenderPipelineAsync({...base,fragment:{module,entryPoint:'display',targets:[{format}]}});
 uniform=device.createBuffer({size:96,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});vertex=device.createBuffer({size:data.vertex_object_ids.length*40,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
 const binding=p=>device.createBindGroup({layout:p.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}}]});bind=binding(pipeline);previewBind=binding(previewPipeline);
 depth=device.createTexture({size:[128,128],format:'depth32float',usage:GPUTextureUsage.RENDER_ATTACHMENT});ready=true;
}
function parameters(){return {scale:Number($('scale').value),albedo:Number($('albedo').value),light:Number($('light').value)};}
function geometry(tick,p=parameters()){
 const motion=data.motion.samples.find(s=>s.tick===tick);if(!motion)throw Error('tick无运动记录');const out=new Float32Array(data.vertex_object_ids.length*10),box=data.boxes.find(b=>b.object_id===data.motion.moving_object);if(!box)throw Error('移动对象引用缺失');
 for(let i=0;i<data.vertex_object_ids.length;i++){const id=data.vertex_object_ids[i],src=i*9,dst=i*10;for(let k=0;k<9;k++)out[dst+k]=data.rest_vbo[src+k];out[dst+9]=id;
  if(id===data.motion.moving_object){for(let k=0;k<3;k++)out[dst+k]=box.center[k]+p.scale*(data.rest_vbo[src+k]-box.center[k])+(k===0?motion.offset_x:0);for(let k=6;k<9;k++)out[dst+k]=data.rest_vbo[src+k]*p.albedo;}}
 return out;
}
function upload(tick,p){const values=new Float32Array(24);values.set(data.camera.vp_columns);values.set(data.light.position,16);values[20]=data.light.intensity*p.light;values[21]=data.light.ambient;device.queue.writeBuffer(uniform,0,values);device.queue.writeBuffer(vertex,0,geometry(tick,p));}
function pass(encoder,views,p,group){const render=encoder.beginRenderPass({colorAttachments:views.map((view,i)=>({view,clearValue:i?[0,0,0,1]:[0,0,0,0],loadOp:'clear',storeOp:'store'})),depthStencilAttachment:{view:depth.createView(),depthClearValue:1,depthLoadOp:'clear',depthStoreOp:'store'}});render.setPipeline(p);render.setBindGroup(0,group);render.setVertexBuffer(0,vertex);render.draw(data.vertex_object_ids.length);render.end();}
function render(){if(!ready||lost)return;const tick=Number($('tick').value);upload(tick,parameters());const encoder=device.createCommandEncoder();pass(encoder,[context.getCurrentTexture().createView()],previewPipeline,previewBind);device.queue.submit([encoder.finish()]);$('status').textContent=`tick=${tick}，t=${(tick/120).toFixed(3)}秒，参数${JSON.stringify(parameters())}`;}
async function readFrame(tick,p){
 upload(tick,p);const textures=[0,1].map(()=>device.createTexture({size:[128,128],format:'rgba32float',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC}));const buffers=[0,1].map(()=>device.createBuffer({size:128*2048,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}));
 try{const encoder=device.createCommandEncoder();pass(encoder,textures.map(t=>t.createView()),pipeline,bind);for(let i=0;i<2;i++)encoder.copyTextureToBuffer({texture:textures[i]},{buffer:buffers[i],bytesPerRow:2048},[128,128]);device.queue.submit([encoder.finish()]);await Promise.all(buffers.map(b=>b.mapAsync(GPUMapMode.READ)));const values=buffers.map(b=>Array.from(new Float32Array(b.getMappedRange())));if(values.some(a=>a.length!==128*128*4||!a.every(Number.isFinite)))throw Error('GPU回读包含非有限值或长度错误');return values;}finally{for(const b of buffers)b.destroy();for(const t of textures)t.destroy();}
}
function stop(){playing=false;cancelAnimationFrame(frameId);$('play').textContent='播放';}
function reset(){for(const id of ['scale','albedo','light'])$(id).value='1';}
async function check(negative=false){
 stop();receipt=undefined;$('download').disabled=true;$('readback').textContent='';$('log').textContent='';await initialize();reset();const results=[],readbacks=[];
 for(const f of data.frames){
  const v=geometry(f.tick,{scale:1,albedo:1,light:1});let geometryError=0;for(let i=0;i<data.vertex_object_ids.length;i++)for(let k=0;k<9;k++)geometryError=Math.max(geometryError,Math.abs(v[i*10+k]-f.vbo[i*9+k]));if(geometryError>1e-6)throw Error(`冻结几何误差${geometryError}`);
  const [color,aux]=await readFrame(f.tick,{scale:1,albedo:1,light:negative?1.25:1});let samples=0,boundary=0,mismatches=0,allObjectMismatches=0,coverageMismatches=0,maxColor=0,maxPosition=0,maxDepth=0,mse=0;
  for(let i=0;i<128*128;i++){const object=color[4*i+3],ref=f.reference.object[i];if(object!==ref)allObjectMismatches++;if((object!==0)!==(ref!==0))coverageMismatches++;if(f.reference.boundary[i]){boundary++;continue;}if(object!==ref){mismatches++;continue;}if(ref===0)continue;samples++;
   for(let k=0;k<3;k++){const diff=Math.abs(color[4*i+k]-f.reference.linear_rgb[3*i+k]);maxColor=Math.max(maxColor,diff);mse+=diff*diff;maxPosition=Math.max(maxPosition,Math.abs(aux[4*i+k]-f.reference.world_position[3*i+k]));}maxDepth=Math.max(maxDepth,Math.abs(aux[4*i+3]-f.reference.depth[i]));}
  if(![geometryError,maxColor,maxPosition,maxDepth,mse].every(Number.isFinite))throw Error('比较统计量非有限');
  if(samples<1000||mismatches)throw Error(`内部覆盖不符：samples${samples},mismatch${mismatches}`);
  if(negative){if(maxColor<.005)throw Error('光强负对照未检出');}else if(maxColor>2e-5||maxPosition>1e-3||maxDepth>2e-5)throw Error(`冻结数值差：color${maxColor},position${maxPosition},depth${maxDepth}`);
  results.push({tick:f.tick,seconds:f.t_seconds,geometryError,interiorSamples:samples,excludedBoundary:boundary,objectMismatches:mismatches,allObjectMismatches,coverageMismatches,maximumLinearError:maxColor,maximumWorldPositionError:maxPosition,maximumDepthError:maxDepth,linearMSE:mse/(3*samples)});readbacks.push({tick:f.tick,color_rgba:color,world_depth_rgba:aux});
 }
 const summary={environment,negative,lightMultiplier:negative?1.25:1,results,scope:'GPU triangle draw and CPU fixed-step table playback; no GPU dynamics or GPU ray tracing'};receipt={...summary,width:128,height:128,row_origin:'top_left',readbacks};$('readback').textContent=JSON.stringify(receipt);$('download').disabled=false;$('log').textContent=JSON.stringify(summary,null,2);$('tick').value='120';render();$('status').textContent=negative?'PASS：光强变化被默认参考检出':'PASS：三个冻结时刻的GPU绘制与CPU参考';
}
function action(fn){return async()=>{if(busy)return;busy=true;try{await fn();}catch(e){$('status').textContent=`失败：${e.message}`;}finally{busy=false;}};}
$('run').onclick=action(()=>check());$('negative').onclick=action(()=>check(true));$('reset').onclick=action(async()=>{stop();await initialize();reset();render();});
$('download').onclick=()=>{if(!receipt)return;const url=URL.createObjectURL(new Blob([JSON.stringify(receipt)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download=receipt.negative?'33-gpu-negative.json':'33-gpu-readback.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('play').onclick=action(async()=>{await initialize();playing=!playing;cancelAnimationFrame(frameId);epoch=performance.now()-Number($('tick').value)*1000/120;$('play').textContent=playing?'暂停':'播放';if(playing)frameId=requestAnimationFrame(frame);});
function frame(now){if(!playing||lost)return;$('tick').value=String(Math.floor((now-epoch)*120/1000)%241);render();frameId=requestAnimationFrame(frame);}
for(const id of ['tick','scale','albedo','light'])$(id).oninput=action(async()=>{stop();await initialize();render();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});for(const id of ['run','negative','play','reset','tick','scale','albedo','light'])$(id).disabled=false;$('status').textContent='点击核对按钮初始化GPU';
