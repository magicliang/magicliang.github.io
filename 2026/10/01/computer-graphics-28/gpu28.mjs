const $ = id => document.getElementById(id);
let device, context, pipeline, displayPipeline, bind, uniform, target, data, format, environment;
let busy=false,lost=false;
const shader=`
struct Params { a:vec4f, bx:vec4f, by:vec4f, bz:vec4f, rho:vec4f, control:vec4u }
@group(0) @binding(0) var<uniform> p:Params;
@group(0) @binding(1) var<storage,read> reference:array<vec4f>;
@vertex fn vs(@builtin(vertex_index) i:u32)->@builtin(position) vec4f {
  var corners=array<vec2f,3>(vec2f(-1,-1),vec2f(3,-1),vec2f(-1,3));return vec4f(corners[i],.5,1);
}
fn approximate(pixel:vec2f)->vec3f {
  let xy=(pixel/64*2-1)*vec2f(1.2,-1.2);
  if(dot(xy,xy)>=1 || dot(xy-vec2f(.55,0),xy-vec2f(.55,0))<.35*.35){return vec3f(0);}
  let n=vec3f(xy,sqrt(1-dot(xy,xy)));
  let scale=select(2.0/3.0,1.0,p.control.y==1);
  return p.rho.rgb*(p.a.rgb+scale*(p.bx.rgb*n.x+p.by.rgb*n.y+p.bz.rgb*n.z));
}
@fragment fn linear(@builtin(position) position:vec4f)->@location(0) vec4f {return vec4f(approximate(position.xy),1);}
@fragment fn display(@builtin(position) position:vec4f)->@location(0) vec4f {
  let index=u32(position.y)*64+u32(position.x);
  let ibl=approximate(position.xy);var c=ibl;
  if(p.control.x==1){c=reference[index].rgb;}
  if(p.control.x==2){c=10*abs(ibl-reference[index].rgb);}
  c=c/(1+c);
  return vec4f(select(1.055*pow(c,vec3f(1.0/2.4))-.055,12.92*c,c<=vec3f(.0031308)),1);
}`;
async function initialize(){
  if(device){if(lost)throw Error('设备丢失，重新加载恢复');return;}
  if(!navigator.gpu)throw Error('WebGPU不可用');
  const response=await fetch(new URLSearchParams(location.search).get('data')??'ibl28.json');
  if(!response.ok)throw Error(`数据请求 ${response.status}`);data=await response.json();
  const validColor=c=>Array.isArray(c)&&c.length===3&&c.every(Number.isFinite);
  if(data.width!==64||data.height!==64||data.ibl?.length!==4096||data.reference?.length!==4096||
     !Array.isArray(data.coefficients)||data.coefficients.length!==4||!data.coefficients.every(validColor)||
     !validColor(data.rho)||!data.ibl.every(validColor)||!data.reference.every(validColor)||
     data.ibl.some(c=>c.some(v=>v<0))||data.reference.some(c=>c.some(v=>v<0))||data.exposure!==1)throw Error('数据布局或曝光错误');
  const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('无可用adapter');
  device=await adapter.requestDevice();device.lost.then(()=>{lost=true;$('status').textContent='设备丢失，重新加载恢复';});
  device.addEventListener('uncapturederror',e=>{lost=true;$('status').textContent=e.error.message;});
  environment={date:new Date().toISOString(),vendor:adapter.info.vendor,architecture:adapter.info.architecture,
    device:adapter.info.device,description:adapter.info.description,userAgent:navigator.userAgent,secureContext:isSecureContext};
  format=navigator.gpu.getPreferredCanvasFormat();context=$('canvas').getContext('webgpu');context.configure({device,format,alphaMode:'opaque'});
  const module=device.createShaderModule({code:shader});
  const errors=(await module.getCompilationInfo()).messages.filter(m=>m.type==='error');if(errors.length)throw Error(errors.map(e=>e.message).join('\n'));
  const layout=device.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.FRAGMENT,buffer:{type:'uniform'}},
    {binding:1,visibility:GPUShaderStage.FRAGMENT,buffer:{type:'read-only-storage'}}]});
  const pipelineLayout=device.createPipelineLayout({bindGroupLayouts:[layout]});
  const create=(entryPoint,format)=>device.createRenderPipelineAsync({layout:pipelineLayout,vertex:{module,entryPoint:'vs'},fragment:{module,entryPoint,targets:[{format}]},primitive:{topology:'triangle-list'}});
  pipeline=await create('linear','rgba32float');displayPipeline=await create('display',format);
  uniform=device.createBuffer({size:96,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const params=new Float32Array(24);[...data.coefficients,data.rho].forEach((c,i)=>params.set(c,i*4));device.queue.writeBuffer(uniform,0,params);
  const values=new Float32Array(4096*4);data.reference.forEach((c,i)=>values.set([...c,1],i*4));
  const reference=device.createBuffer({size:values.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});device.queue.writeBuffer(reference,0,values);
  bind=device.createBindGroup({layout,entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:{buffer:reference}}]});
  target=device.createTexture({size:[64,64],format:'rgba32float',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
}
function encode(encoder,view,selected){
  const pass=encoder.beginRenderPass({colorAttachments:[{view,clearValue:[0,0,0,1],loadOp:'clear',storeOp:'store'}]});
  pass.setPipeline(selected);pass.setBindGroup(0,bind);pass.draw(3);pass.end();
}
async function render(){
  device.queue.writeBuffer(uniform,80,new Uint32Array([Number($('view').value),0,0,0]));
  const encoder=device.createCommandEncoder();encode(encoder,context.getCurrentTexture().createView(),displayPipeline);
  device.queue.submit([encoder.finish()]);await device.queue.onSubmittedWorkDone();if(lost)throw Error('设备丢失');
}
async function check(negative=false){
  await initialize();device.queue.writeBuffer(uniform,80,new Uint32Array([0,Number(negative),0,0]));
  const read=device.createBuffer({size:4096*16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
  let maximum=0,mse=0,shaded=0;
  try{
    const encoder=device.createCommandEncoder();encode(encoder,target.createView(),pipeline);
    encoder.copyTextureToBuffer({texture:target},{buffer:read,bytesPerRow:64*16},[64,64]);device.queue.submit([encoder.finish()]);
    await read.mapAsync(GPUMapMode.READ);const values=new Float32Array(read.getMappedRange());
    for(let i=0;i<4096;++i){
      for(let c=0;c<3;++c){if(!Number.isFinite(values[i*4+c]))throw Error('非有限GPU颜色');maximum=Math.max(maximum,Math.abs(values[i*4+c]-data.ibl[i][c]));}
      if(data.ibl[i].some(v=>v>0)){++shaded;for(let c=0;c<3;++c)mse+=(values[i*4+c]-data.reference[i][c])**2/3;}
    }
  }finally{if(read.mapState==='mapped')read.unmap();read.destroy();}
  if(lost)throw Error('设备丢失');
  if(negative?maximum<.01:maximum>2e-5)throw Error(`颜色误差判据失败 ${maximum}`);
  $('log').textContent=JSON.stringify({environment,negative,maximumLinearError:maximum,linearMseVsPath:mse/shaded,shaded,
    tolerance:2e-5,width:64,height:64,referenceSeed:data.seed,referenceSpp:data.spp,
    model:'GPU unoccluded diffuse IBL; CPU convex receiver plus zero-reflectance blocker'},null,2);
  await render();$('status').textContent=negative?'负对照成功：漏掉2/3导致可检出的线性误差':'PASS：GPU IBL与CPU相同预计算结果一致；与路径参考的差异单列';
}
async function action(fn){if(busy)return;busy=true;for(const id of ['run','negative','view'])$(id).disabled=true;
  try{await fn();}catch(e){$('status').textContent=`FAIL：${e.message}`;}
  finally{busy=false;for(const id of ['run','negative','view'])$(id).disabled=false;}}
$('run').onclick=()=>action(()=>check());$('negative').onclick=()=>action(()=>check(true));
$('view').onchange=()=>action(async()=>{await initialize();await render();$('status').textContent=`已显示：${$('view').selectedOptions[0].textContent}`;});
for(const id of ['run','negative','view'])$(id).disabled=false;$('status').textContent='模块就绪，点击运行进行真实GPU检查。';
