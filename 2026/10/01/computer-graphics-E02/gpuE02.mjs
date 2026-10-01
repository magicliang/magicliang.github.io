export const width=64,height=64;
export function referencePixel(x,y,reverse=false) {
 if(!Number.isInteger(x)||!Number.isInteger(y)||x<0||y<0||x>=width||y>=height||typeof reverse!=='boolean')throw Error('invalid pixel or order');
 const red=x>=8&&x<44&&y>=8&&y<44,blue=x>=24&&x<56&&y>=24&&y<56;
 if(red&&blue)return reverse?[.5,0,.25,.75]:[.25,0,.5,.75];
 return red?[.5,0,0,.5]:blue?[0,0,.5,.5]:[0,0,0,0];
}
export function compareReadback(values,reverse=false) {
 if(typeof reverse!=='boolean'||!(values instanceof Float32Array)||values.length!==width*height*4||!values.every(Number.isFinite))throw Error('invalid float32 readback');
 let maximumError=0,correctOrderError=0,changedPixels=0;
 for(let y=0;y<height;y++)for(let x=0;x<width;x++) {
  const expected=referencePixel(x,y,reverse),correct=referencePixel(x,y);let changed=false;
  for(let k=0;k<4;k++) {
   const value=values[(y*width+x)*4+k];maximumError=Math.max(maximumError,Math.abs(value-expected[k]));
   correctOrderError=Math.max(correctOrderError,Math.abs(value-correct[k]));if(Math.abs(value-correct[k])>1e-6)changed=true;
  }
  if(changed)changedPixels++;
 }
 if(maximumError>1e-6)throw Error(`attachment mismatch ${maximumError}`);
 if(reverse&&(correctOrderError<.2||changedPixels!==400))throw Error('wrong-order control not detected');
 return {maximumError,correctOrderError,changedPixels,overlap:Array.from(values.slice((32*width+32)*4,(32*width+32)*4+4))};
}
const shader=`
struct Vertex {@location(0) position:vec2f,@location(1) color:vec4f};
struct Interpolated {@builtin(position) position:vec4f,@location(0) color:vec4f};
@vertex fn vs(v:Vertex)->Interpolated {var o:Interpolated;o.position=vec4f(v.position,0.,1.);o.color=v.color;return o;}
@fragment fn fs(v:Interpolated)->@location(0) vec4f {return v.color;}`;
let device,pipeline,vertices,environment,ready=false,lost=false,busy=false,receipt;
const $=id=>document.getElementById(id);
function invalidate(message) {receipt=undefined;$('download').disabled=true;$('readback').textContent='';if(message)$('status').textContent=message;}
async function sha256(bytes) {return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');}
async function initialize() {
 if(device){if(!ready||lost)throw Error('device unavailable; reload page');return;}
 if(!navigator.gpu)throw Error('WebGPU unavailable');
 const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw Error('adapter unavailable');
 if(!adapter.features.has('float32-blendable'))throw Error('float32-blendable required; no substituted format');
 device=await adapter.requestDevice({requiredFeatures:['float32-blendable']});
 device.lost.then(info=>{lost=true;invalidate(`device lost: ${info.message}`);});
 device.addEventListener('uncapturederror',event=>{lost=true;invalidate(event.error.message);});
 const response=await fetch(import.meta.url);if(!response.ok)throw Error('module hash fetch failed');
 environment={date:new Date().toISOString(),vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,userAgent:navigator.userAgent,module_sha256:await sha256(await response.arrayBuffer()),shader_sha256:await sha256(new TextEncoder().encode(shader)),feature:'float32-blendable'};
 const module=device.createShaderModule({code:shader});const errors=(await module.getCompilationInfo()).messages.filter(m=>m.type==='error');if(errors.length)throw Error(errors.map(e=>e.message).join('\n'));
 const component={operation:'add',srcFactor:'one',dstFactor:'one-minus-src-alpha'};
 pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:24,attributes:[{shaderLocation:0,offset:0,format:'float32x2'},{shaderLocation:1,offset:8,format:'float32x4'}]}]},fragment:{module,entryPoint:'fs',targets:[{format:'rgba32float',blend:{color:component,alpha:component}}]},primitive:{topology:'triangle-list',cullMode:'none'}});
 const data=[];
 for(const [left,top,right,bottom,color] of [[8,8,44,44,[.5,0,0,.5]],[24,24,56,56,[0,0,.5,.5]]]) {
  for(const [x,y] of [[left,top],[right,top],[left,bottom],[left,bottom],[right,top],[right,bottom]])data.push(2*x/width-1,1-2*y/height,...color);
 }
 vertices=device.createBuffer({size:data.length*4,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});device.queue.writeBuffer(vertices,0,new Float32Array(data));
 if(lost)throw Error('device lost during initialization');ready=true;
}
async function drawReadback(reverse) {
 const texture=device.createTexture({size:[width,height],format:'rgba32float',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
 const buffer=device.createBuffer({size:width*height*16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
 device.pushErrorScope('validation');
 try {
  const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:texture.createView(),clearValue:[0,0,0,0],loadOp:'clear',storeOp:'store'}]});
  pass.setPipeline(pipeline);pass.setVertexBuffer(0,vertices);pass.draw(6,1,reverse?6:0);pass.draw(6,1,reverse?0:6);pass.end();
  encoder.copyTextureToBuffer({texture},{buffer,bytesPerRow:width*16},[width,height]);device.queue.submit([encoder.finish()]);
  await buffer.mapAsync(GPUMapMode.READ);const values=new Float32Array(buffer.getMappedRange().slice(0));if(lost)throw Error('device lost during readback');return values;
 }finally{buffer.destroy();texture.destroy();const error=await device.popErrorScope();if(error)throw Error(error.message);}
}
function display(values) {
 const canvas=$('canvas'),context=canvas.getContext('2d'),image=context.createImageData(width,height);
 for(let i=0;i<width*height;i++) {
  for(let k=0;k<3;k++){const c=values[4*i+k],s=c<=.0031308?12.92*c:1.055*c**(1/2.4)-.055;image.data[4*i+k]=Math.round(255*s);}
  image.data[4*i+3]=255;
 }
 context.putImageData(image,0,0);
}
async function run(reverse) {
 if(busy)return;busy=true;invalidate();$('run').disabled=true;$('negative').disabled=true;$('log').textContent='';
 try {
  await initialize();const values=await drawReadback(reverse),result=compareReadback(values,reverse);display(values);
  receipt={environment,reverse,width,height,row_origin:'top_left',format:'rgba32float',linear_premultiplied:true,blend:{src:'one',dst:'one-minus-src-alpha'},result,rgba:Array.from(values),scope:'real GPU source-over; CPU display encodes readback over black; CPU TAA is separate'};
  $('log').textContent=JSON.stringify({...receipt,rgba:'full array in downloaded receipt'},null,2);$('readback').textContent=JSON.stringify(receipt);$('download').disabled=false;
  $('status').textContent=reverse?'PASS：反序改变400个交叠像素；正确排序检查检出错误':'PASS：4096像素真实GPU叠面匹配线性参考';
 }catch(error){invalidate(`FAIL：${error.message}`);}finally{busy=false;$('run').disabled=false;$('negative').disabled=false;}
}
if(typeof document!=='undefined') {
 $('run').onclick=()=>run(false);$('negative').onclick=()=>run(true);
 $('download').onclick=()=>{if(!receipt)return;const url=URL.createObjectURL(new Blob([JSON.stringify(receipt)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download=receipt.reverse?'E02-gpu-negative.json':'E02-gpu-readback.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
}
