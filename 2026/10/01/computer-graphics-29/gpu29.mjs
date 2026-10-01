const $=id=>document.getElementById(id);
const unit=q=>{const n=Math.hypot(...q);if(!(n>0)||!Number.isFinite(n))throw Error('非法四元数');return q.map(x=>x/n);};
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
function interpolate(a,b,u,mode='slerp',short=true){
  a=unit(a);b=unit(b);let d=dot(a,b);if(short&&d<0){b=b.map(x=>-x);d=-d;}
  d=Math.max(-1,Math.min(1,d));
  if(mode==='nlerp'||d>.9995)return unit(a.map((x,i)=>(1-u)*x+u*b[i]));
  const angle=Math.acos(d),s=Math.sin(angle);
  if(Math.abs(s)<1e-12)throw Error('未选择最短弧的反号端点退化');
  return unit(a.map((x,i)=>(Math.sin((1-u)*angle)*x+Math.sin(u*angle)*b[i])/s));
}
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
function rotate(q,p){const v=q.slice(0,3),t=cross(v,p).map(x=>2*x),c=cross(v,t);return p.map((x,i)=>x+q[3]*t[i]+c[i]);}
let data,device,context,pipeline,uniform,bind,environment,busy=false,lost=false,ready=false,playing=false,epoch=0,frameId=0;
const shader=`
@group(0) @binding(0) var<uniform> q:vec4f;
@vertex fn vs(@builtin(vertex_index) i:u32)->@builtin(position) vec4f {
 var points=array<vec2f,6>(vec2f(0,-.04),vec2f(.8,-.04),vec2f(.8,.04),vec2f(0,-.04),vec2f(.8,.04),vec2f(0,.04));
 let p=vec3f(points[i],0);let t=2*cross(q.xyz,p);let rotated=p+q.w*t+cross(q.xyz,t);return vec4f(rotated.xy,.5,1);
}
@fragment fn fs()->@location(0) vec4f {return vec4f(0,1,0,1);}`;
function pose(seconds,mode=$('mode').value,short=true){
 const u=Math.max(0,Math.min(1,seconds/2));
 if(mode==='euler'){const a=(170-340*u)*Math.PI/180;return [0,0,Math.sin(a/2),Math.cos(a/2)];}
 return interpolate(data.keys[0].quaternion_xyzw,data.keys[1].quaternion_xyzw,u,mode,short);
}
async function initialize(){
 if(device){if(lost||!ready)throw Error('设备丢失或初始化未完成，重新加载恢复');return;}
 if(!navigator.gpu)throw Error('WebGPU不可用');
 const response=await fetch(new URLSearchParams(location.search).get('data')??'animation29.json');if(!response.ok)throw Error(`数据请求${response.status}`);
 data=await response.json();
 if(data.keys?.length!==2||data.keys[0].t_seconds!==0||data.keys[1].t_seconds!==2||!Array.isArray(data.samples)||!data.samples.length)throw Error('错误时间布局');
 for(const key of data.keys){if(key.quaternion_xyzw?.length!==4||!key.quaternion_xyzw.every(Number.isFinite))throw Error('错误旋转布局');unit(key.quaternion_xyzw);}
 for(const s of data.samples){if(!Number.isFinite(s.t_seconds)||s.rotated_point?.length!==3||!s.rotated_point.every(Number.isFinite))throw Error('错误参考样本');}
 const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('无可用adapter');device=await adapter.requestDevice();
 environment={date:new Date().toISOString(),vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,userAgent:navigator.userAgent};
 device.lost.then(()=>{lost=true;playing=false;$('status').textContent='设备丢失，请重新加载';});device.addEventListener('uncapturederror',e=>{lost=true;playing=false;$('status').textContent=e.error.message;});
 context=$('canvas').getContext('webgpu');const format=navigator.gpu.getPreferredCanvasFormat();context.configure({device,format,alphaMode:'opaque'});
 const module=device.createShaderModule({code:shader});const errors=(await module.getCompilationInfo()).messages.filter(x=>x.type==='error');if(errors.length)throw Error(errors.map(x=>x.message).join('\n'));
 pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs'},fragment:{module,entryPoint:'fs',targets:[{format}]}});
 uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}}]});ready=true;
}
function draw(q,view,encoder){device.queue.writeBuffer(uniform,0,new Float32Array(q));const pass=encoder.beginRenderPass({colorAttachments:[{view,clearValue:[0,0,0,1],loadOp:'clear',storeOp:'store'}]});pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.draw(6);pass.end();}
function render(){if(!ready||lost)return;const seconds=Number($('time').value)/1000,q=pose(seconds);const encoder=device.createCommandEncoder();draw(q,context.getCurrentTexture().createView(),encoder);device.queue.submit([encoder.finish()]);$('status').textContent=`t=${seconds.toFixed(3)}秒，${$('mode').selectedOptions[0].textContent}`;}
async function check(negative=false){
 playing=false;cancelAnimationFrame(frameId);$('play').textContent='播放';await initialize();let maximum=0;
 for(const s of data.samples){const p=rotate(pose(s.t_seconds,'slerp',!negative),[1,0,0]);maximum=Math.max(maximum,Math.hypot(...p.map((x,i)=>x-s.rotated_point[i])));}
 if(negative){if(!(maximum>.1))throw Error('负对照未检出');$('status').textContent='负对照成功：错误符号造成不同轨迹';$('log').textContent=JSON.stringify({environment,negative:true,maximumPointError:maximum},null,2);return;}
 if(!(maximum<1e-12))throw Error(`CPU姿态误差${maximum}`);
 const format=navigator.gpu.getPreferredCanvasFormat(),target=device.createTexture({size:[256,256],format,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
 const read=device.createBuffer({size:256*1024,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
 try{const encoder=device.createCommandEncoder();draw(pose(1,'slerp'),target.createView(),encoder);encoder.copyTextureToBuffer({texture:target},{buffer:read,bytesPerRow:1024},[256,256]);device.queue.submit([encoder.finish()]);await read.mapAsync(GPUMapMode.READ);
  const bytes=new Uint8Array(read.getMappedRange()),pixel=(x,y)=>Array.from(bytes.slice(y*1024+x*4,y*1024+x*4+4));const tip=pixel(36,128),opposite=pixel(220,128);
  if(tip.join(',')!=='0,255,0,255'||opposite.join(',')!=='0,0,0,255')throw Error('GPU中点方向读回失败');
  $('log').textContent=JSON.stringify({environment,negative:false,maximumPointError:maximum,samples:data.samples.length,gpuMidpointTip:tip,gpuOpposite:opposite},null,2);
 }finally{read.destroy();target.destroy();}
 $('time').value='1000';$('mode').value='slerp';render();$('status').textContent='PASS：CPU同时间姿态与GPU中点方向';
}
function action(fn){return async()=>{if(busy)return;busy=true;try{await fn();}catch(e){$('status').textContent=`失败：${e.message}`;}finally{busy=false;}};}
$('run').onclick=action(()=>check());$('negative').onclick=action(()=>check(true));
$('play').onclick=action(async()=>{await initialize();playing=!playing;cancelAnimationFrame(frameId);epoch=performance.now()-Number($('time').value);$('play').textContent=playing?'暂停':'播放';if(playing)frameId=requestAnimationFrame(frame);});
function frame(now){if(!playing||lost)return;$('time').value=String((now-epoch)%2000);render();frameId=requestAnimationFrame(frame);}
$('time').oninput=()=>{if(busy)return;playing=false;cancelAnimationFrame(frameId);$('play').textContent='播放';render();};$('mode').onchange=()=>{if(!busy)render();};
document.addEventListener('visibilitychange',()=>{if(document.hidden){playing=false;cancelAnimationFrame(frameId);$('play').textContent='播放';}});
for(const id of ['run','negative','play','mode','time'])$(id).disabled=false;
$('status').textContent='模块已加载，点击核对按钮初始化';
